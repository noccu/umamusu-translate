import json
from pathlib import Path
from typing import Generator, Union

import regex

from common import utils
from common.files import fileops
from ..StoryId import StoryId


class TranslationFile:
    latestVersion = 6
    ver_offset_mdb = 100
    textBlacklist = regex.compile(r"^タイトルコール$|イベントタイトルロゴ表示.*|※*ダミーテキスト|^欠番$")

    def __init__(self, file: Union[str, Path] = None, load=True, readOnly=False):
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
            if not data:
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
            if isinstance(key, int) and not idx or idx == key:
                self.data[key] = val
            if idx:
                self.data[idx][key] = val
            elif self.map:
                self.map[key]["enText"] = val
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
            data = data or self.data
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
            data = data or self.data
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
    def bundle(self):
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
        self.data = fileops.readJson(self.file)
        self.fileExists = True  # should error if it does not
        self.init()

    def save(self):
        if self.fileExists and self._snapshot == json.dumps(
            self.data, ensure_ascii=False, default=fileops._to_json
        ):
            return
        assert self.file
        if 3 < self.version < self.ver_offset_mdb:
            self.data["modified"] = utils.currentTimestamp()
        fileops.writeJson(self.file, self.data)

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
            self._snapshot = json.dumps(self.data, ensure_ascii=False, default=fileops._to_json)

    def setFile(self, file: Union[str, Path]):
        self.file = Path(file)
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
    def fromData(cls, data, snapshot=False):
        c = cls(load=False)
        c.data = {"version": cls.latestVersion, **data}
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
