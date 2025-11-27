import json
import os
from dataclasses import asdict, astuple, dataclass
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Generator, Optional

import regex
import UnityPy

from . import utils
from .constants import GAME_ASSET_ROOT, BUNDLE_BASE_KEY

if TYPE_CHECKING:
    from UnityPy.files import ObjectReader


@dataclass
class StoryId:
    type: str = "story"
    set: str = None
    setLen = 5
    group: str = None
    groupLen = 2
    id: str = None
    idLen = 4
    idx: str = None
    idxLen = 3
    idOnlyGroup = ("lyrics", "preview")

    def __post_init__(self):
        if self.type in self.idOnlyGroup:
            if not self.id and self.idx:
                self.id = self.idx
            self.idx = None
            self.group = None
            self.set = None

    def __str__(self) -> str:
        """Return the joined numeric parts, as written in tlFiles"""
        return "".join(x for x in astuple(self)[1:] if x is not None)

    @classmethod
    def parse(cls, text_type, s):
        if text_type in cls.idOnlyGroup:
            return cls(type=text_type, id=s)
        elif len(s) > 9 and text_type == "home":
            return cls(type=text_type, set=s[:5], group=s[5:7], id=s[7:11], idx=s[11:])
        else:
            return cls(type=text_type, group=s[:2], id=s[2:6], idx=s[6:])

    @classmethod
    def parseFromPath(cls, text_type: str, path: str):
        """Given a text type (story, lyrics, etc.) and a game data filepath,
        extract and return the group, id, and index."""
        if text_type == "home":
            path = path[-16:]
            return cls(
                type=text_type,
                set=path[:5],
                group=path[6:8],
                id=path[9:13],
                idx=path[13:],
            )
        elif text_type == "lyrics":
            return cls(type=text_type, id=path[-11:-7])
        elif text_type == "preview":
            return cls(type=text_type, id=path[-4:])
        else:  # story and storyrace
            path = path[-9:]
            return cls(type=text_type, group=path[:2], id=path[2:6], idx=path[6:9])

    @classmethod
    def queryfy(cls, storyId: "StoryId"):
        """Returns a new StoryId with attributes usable in SQL"""
        parts = asdict(storyId)
        for k, v in parts.items():
            if v is None:
                parts[k] = "_" * getattr(storyId, f"{k}Len", 0)
        return cls(*parts.values())

    @classmethod
    def fromLegacy(cls, group, id, idx):
        return cls(group=group, id=id, idx=idx)

    def asLegacy(self):
        return self.group, self.id, self.idx

    def asTuple(self, validOnly=False):
        if validOnly:
            # Faster with the list comp for some extra mem cost, apparently
            return tuple([x for x in astuple(self) if x is not None])
        else:
            return astuple(self)

    def asPath(self, includeIdx=False):
        offset = None if includeIdx else -1
        return Path().joinpath(*self.asTuple(validOnly=True)[1:offset])  # ignore type for now

    def getFilenameIdx(self):
        if self.type in self.idOnlyGroup:
            return self.id
        elif self.idx:
            return self.idx
        else:
            raise AttributeError


class TranslationFile:
    latestVersion = 6
    ver_offset_mdb = 100
    textBlacklist = regex.compile(r"^タイトルコール$|イベントタイトルロゴ表示.*|※*ダミーテキスト|^欠番$")

    def __init__(self, file: Path = None, load=True, readOnly=False):
        self.readOnly = readOnly
        if load:
            if not file:
                raise RuntimeError("Attempting to load tlfile but no file provided.")
            self.setFile(file)
            self.reload()
        else:
            if file:
                self.setFile(file)
            self.fileExists = False

    class TextData:
        def __init__(self, root: "TranslationFile", data=None) -> None:
            self.root = root
            self.map = None
            if data is None:
                data = root.textBlocks
            self.data = self.toInterchange(data)

        def get(self, key, default=None):
            if isinstance(key, str) and self.map:
                return self.map.get(key, {}).get("enText", default)
            elif isinstance(key, int):
                try:
                    return self.data[key]
                except IndexError:
                    return default
            else:
                raise NotImplementedError

        def set(self, key, val, idx: int = None):
            if isinstance(key, int) and idx in (None, key):
                self.data[key] = val
            elif idx:
                self.data[idx][key] = val
            elif self.map is not None:
                if key not in self.map:
                    self.data.append({"jpText": key, "enText":val})
                    self.map[key] = self.data[-1]
                else:
                    self.map[key]["jpText"] = key
                    self.map[key]["enText"] = val
            elif key is None:
                self.data.append(val)
            else:
                raise LookupError(f"No index provided for list-format file {self.root.name}")

        def items(self, key="jpText", val="enText") -> dict[str, str]:
            for entry in self.data:
                yield (entry.get(key), entry.get(val))

        def __getitem__(self, itm):
            return self.get(itm)

        def __setitem__(self, itm, val):
            self.set(itm, val)

        def __iter__(self):
            return self.data.__iter__()

        def __len__(self):
            return len(self.data)

        def __json__(self):
            return self.toNative()

        def find(self, key, val) -> dict:
            return next((x for x in self.data if x.get(key) == val), None)

        def toInterchange(self, data=None) -> list[dict]:
            data = self.data if data is None else data
            self._nativeData = data  # todo: change the whole system
            if isinstance(data, dict):
                self.map = dict()
                o = list()
                for i, (k, v) in enumerate(data.items(), start=1):
                    o.append({"jpText": k, "enText": v, "blockIdx": i, "nextBlock": i + 1})
                    self.map[k] = o[-1]
                return o
            return data

        def toNative(self, data=None):
            data = self.data if data is None else data
            if (
                self.root.version == -2 or self.root.version > self.root.ver_offset_mdb
            ) and isinstance(data, list):
                o = dict()
                for e in data:
                    o[e.get("jpText")] = e.get("enText", "")
                return o
            return data

    def _getVersion(self) -> int:
        ver = self.data.get("version", 1)
        if ver == 1 and not isinstance(next(iter(self.data.values())), list):
            ver = -2
        return ver

    @property
    def textBlocks(self) -> TextData:
        if self.version > 1:
            return self.data["text"]
        elif self.version == -2:
            return self.data
        else:
            return list(self.data.values())[0]

    @textBlocks.setter
    def textBlocks(self, val):
        if self.version > 1:
            self.data["text"] = self.TextData(self, val)
        elif self.version == -2:
            self.data = self.TextData(self, val)
        else:
            raise NotImplementedError

    def genTextContainers(self) -> Generator[dict, None, None]:
        for block in self.textBlocks:
            if block["jpText"]:
                if self.textBlacklist.match(block["jpText"]):
                    continue
                yield block
            if "coloredText" in block:
                for entry in block["coloredText"]:
                    yield entry
            if "choices" in block:
                for entry in block["choices"]:
                    yield entry

    @property
    def bundle(self) -> Optional[str]:
        if self.version > 1:
            return self.data["bundle"]
        elif self.version == -2:
            return
        else:
            return list(self.data.keys())[0]

    @property
    def type(self):
        if self.version > 2:
            return self.data["type"]
        elif self.version == -2:
            return "dict"
        else:
            return "story/home"

    def getStoryId(self) -> str:
        if self.version > 3:
            return self.data["storyId"]
        elif self.version > 2 and self.data["storyId"] != "000000000":
            return self.data["storyId"]
        elif self.version == -2:
            return
        else:
            isN = regex.compile(r"\d+")
            g, id, idx = self.file.parts[
                -3:
            ]  # project structure provides at least 3 levels, luckily
            if not isN.match(g):
                g = ""
            if not isN.match(id):
                id = ""
            idx = isN.match(idx)[0]
            return f"{g}{id}{idx}"

    def reload(self):
        self.data = utils.readJson(self.file)
        self.fileExists = True  # should error if it does not
        self.init()

    def save(self, update=True):
        if self.fileExists and self._snapshot == json.dumps(
            self.data, ensure_ascii=False, default=utils._to_json
        ):
            return
        assert self.file
        if update and 3 < self.version < self.ver_offset_mdb:
            self.data["modified"] = utils.currentTimestamp()
        utils.writeJson(self.file, self.data)

    def snapshot(self, copyFrom=None):
        if self.readOnly:
            return
        elif copyFrom:
            self._snapshot = copyFrom._snapshot
            self.fileExists = copyFrom.fileExists
            # Gets written correctly on save anyway but copyFrom means
            # we're trying to "restore" a state (partially):
            mod = copyFrom.data.get("modified")
            if mod:
                self.data["modified"] = mod
        else:
            self._snapshot = json.dumps(self.data, ensure_ascii=False, default=utils._to_json)

    def setFile(self, file: Path):
        self.file = file
        self.name = self.file.name

    def init(self, snapshot=True):
        self.version = self._getVersion()
        self.escapeNewline = self.type in ("race", "preview", "mdb", "lyrics")
        if self.type == "mdb" and self.file.parent.name == "character_system_text":
            self.escapeNewline = False
        if self.type == "dict":
            self.data = self.TextData(self)
        else:
            self.data["text"] = self.TextData(self)
        if snapshot:
            self.snapshot()

    @classmethod
    def fromData(cls, data, file_path:Path|None = None, snapshot=False):
        c = cls(load=False)
        c.data = {"version": cls.latestVersion, **data}
        c.file = file_path or Path("tl_file_dump.json")
        c.init(snapshot)
        return c

    @classmethod
    def rename(cls, tlFile: "TranslationFile", newName: str = None):
        """Renames the physical file in the same dir. Dev helper method."""
        if not tlFile.fileExists:
            return
        if newName is None:
            idx = StoryId.parse(tlFile.type, tlFile.getStoryId()).idx
            title = tlFile.data.get("title")
            newName = f"{idx} ({title}).json" if title else f"{idx}.json"
        newName = tlFile.file.parent.joinpath(utils.sanitizeFilename(newName))
        tlFile.file.rename(newName)
        tlFile.setFile(newName)


class GameBundle:
    # Decryption based on code and work by croakfang
    editMark = b"\x08\x04"

    def __init__(self, path, load=True, bType="story", bundle_key:int=0) -> None:
        self.bundlePath = Path(path)
        self.bundleName = self.bundlePath.stem
        self.bundleType = bType
        self.data = None
        self.patchData: bytes = b""
        self._autoloaded = load
        self._patchedState = None
        self.patchedTime = None
        self.bundle_key = bundle_key # encryption key from meta

        if load:
            self.load()

    def markPatched(self, tlFile: "TranslationFile"):
        m = tlFile.data.get("modified", b"")
        if m:
            m = m.to_bytes(5, byteorder="big", signed=False)
            # Have a nice day and good training if you're reading this in the year 15xxx somewhere :spemini:
        self.patchData = m + self.editMark

    @property
    def isPatched(self):
        return self.readPatchState()

    @isPatched.setter
    def isPatched(self, v):
        self._patchedState = v

    def readPatchState(self, customPath=None):
        if not customPath and self._patchedState is not None:
            return self._patchedState
        try:
            with open(customPath or self.bundlePath, "rb") as f:
                f.seek(-7, os.SEEK_END)
                modified = f.read(5)
                mark = f.read(2)
                if mark == self.editMark:
                    self._patchedState = True
                    # Exception handling removed as I don't see how it would except
                    # The actual issue is it could not be a timestamp... todo?
                    modified = int.from_bytes(modified, byteorder="big")
                    self.patchedTime = modified
                else:
                    self._patchedState = False
        except Exception:
            self._patchedState = False
        return self._patchedState

    def getAssetData(self, pathId: int):
        if a := self.assets.get(pathId):
            return a.read_typetree()
        else:
            return None

    def load(self):
        # UnityPy does not error and loads empty files
        if not self.exists:
            raise FileNotFoundError
        # We'll just assume nobody will use this to read massive files. Hehe.
        if self.bundle_key == 0:
            self.data = UnityPy.load(str(self.bundlePath))
        else:
            file_data = self.bundlePath.read_bytes()
            if len(file_data) > 256:
                file_data = self._decrypt(file_data)
            self.data = UnityPy.load(file_data)
        if self._autoloaded:
            self.readPatchState()
        self.rootAsset: "ObjectReader" = next(iter(self.data.container.values())).get_obj()
        self.assets: dict[str, "ObjectReader"] = self.rootAsset.assets_file.files
        return self

    def _decrypt(self, data:bytes):
        final_key = self._create_final_key()
        decrypted_data = bytearray(data)
        for i in range(256, len(decrypted_data)):
            decrypted_data[i] ^= final_key[i % len(final_key)]
        return bytes(decrypted_data)

    def _create_final_key(self):
        base_key = bytes.fromhex(BUNDLE_BASE_KEY)
        bundle_key = self.bundle_key.to_bytes(8, byteorder="little", signed=True)
        base_len = len(base_key)
        final_key = bytearray(base_len * 8)
        for i, b in enumerate(base_key):
            baseOffset = i << 3 # i * 8
            for j, k in enumerate(bundle_key):
                final_key[baseOffset + j] = b ^ k
        return final_key

    def save(self, dstFolder: Path = None, dstName: str = None):
        if not self.data:
            return

        b = self.data.file.save(packer="lz4")
        if self.bundle_key != 0:
            b = self._decrypt(b) # XOR-based, so works both ways
        b += self.patchData
        fn = dstName or self.bundleName
        fp = ((dstFolder / fn[0:2]) if dstFolder else self.bundlePath.parent) / fn
        fp.parent.mkdir(parents=True, exist_ok=True)
        with open(fp, "wb") as f:
            f.write(b)
        self.isPatched = True

    @property
    def exists(self):
        return self.bundlePath.exists()

    @classmethod
    def fromName(cls, name, **kwargs):
        """Create a bundle by hash/name from the default game dir. kwargs passed to constructor"""
        bundlePath = GameBundle.createPath(GAME_ASSET_ROOT, name)
        return cls(bundlePath, **kwargs)

    @staticmethod
    def createPath(dstFolder, dstName):
        return PurePath(dstFolder, dstName[0:2], dstName)
