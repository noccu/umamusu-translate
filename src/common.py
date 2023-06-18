import argparse
import json
import os
from pathlib import Path, PurePath
import sys
from typing import Generator, Union
import regex
from datetime import datetime, timezone
from dataclasses import dataclass, astuple, asdict

import UnityPy
from UnityPy.files import ObjectReader

import helpers
from helpers import IS_WIN

if IS_WIN:
    GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
    GAME_ASSET_ROOT = os.path.join(GAME_ROOT, "dat")
    GAME_META_FILE = os.path.join(GAME_ROOT, "meta")
    GAME_MASTER_FILE = os.path.join(GAME_ROOT, "master", "master.mdb")
else:
    GAME_ROOT = GAME_ASSET_ROOT = GAME_META_FILE = GAME_MASTER_FILE = None
SUPPORTED_TYPES = ["story", "home", "race", "lyrics", "preview", "ruby", "mdb"]  # Update indexing on next line
TARGET_TYPES = SUPPORTED_TYPES[:-2]  # Classic asset types we want to read/write.
NAMES_BLACKLIST = ["<username>", "", "モノローグ"]  # Special-use game names, don't touch


def searchFiles(targetType, targetGroup, targetId, targetIdx=False, targetSet=False, changed=False, jsonOnly=True) -> list[str]:
    found = list()
    isJson = lambda f: PurePath(f).suffix == ".json" if jsonOnly else True
    if changed:
        from subprocess import run, PIPE
        cmd = ["git", "status", "--short", "--porcelain"] if changed is True else ["git", "show", "--pretty=", "--name-status", changed]
        # assumes git-config quotedPath = true, which is default I believe. :tmopera:
        for l in run(cmd, stdout=PIPE).stdout.decode('unicode-escape').encode("latin-1").decode().splitlines():
            m = regex.match(".?([^\s])\s*\"?([^\"]+)\"?", l)
            state, path = m[1], PurePath(m[2])
            if state in ("A", "M") and path.parts[0] == "translations" and path.parts[1] == targetType:
                if not isJson(path): continue
                if targetGroup and path.parts[2] != targetGroup: continue
                if targetId and path.parts[3] != targetId: continue
                found.append(str(path))
    else:
        searchDir = targetType if isinstance(targetType, os.PathLike) else os.path.join("translations", targetType)
        for root, dirs, files in os.walk(searchDir):
            depth = len(dirs[0]) if dirs else -1
            if targetSet and depth == 5:
                dirs[:] = [d for d in dirs if d == targetSet]
            elif targetGroup and depth == 2:
                dirs[:] = [d for d in dirs if d == targetGroup]
            elif targetId:
                if targetType in ("lyrics", "preview"):
                    found.extend(os.path.join(root, file) for file in files
                                 if PurePath(file).stem == targetId and isJson(file))
                    continue
                elif depth == 4:
                    dirs[:] = [d for d in dirs if d == targetId]
            if targetIdx and files:
                found.extend(os.path.join(root, file) for file in files if file.startswith(targetIdx) and isJson(file))
            else: found.extend(os.path.join(root, file) for file in files if isJson(file))
    return found


@dataclass
class StoryId:
    type:str = "story"
    set:str = None
    setLen = 5
    group:str = None
    groupLen = 2
    id:str = None
    idLen = 4
    idx:str = None
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
        '''Return the joined numeric parts, as written in tlFiles'''
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
        """Given a text type (story, lyrics, etc.) and a game data filepath, extract and return the group, id, and index."""
        if text_type == "home":
            path = path[-16:]
            return cls(type=text_type, set=path[:5], group=path[6:8], id=path[9:13], idx=path[13:])
        elif text_type == "lyrics":
            return cls(type=text_type, id=path[-11:-7])
        elif text_type == "preview":
            return cls(type=text_type, id=path[-4:])
        else:  # story and storyrace
            path = path[-9:]
            return cls(type=text_type, group=path[:2], id=path[2:6], idx=path[6:9])
    @classmethod
    def queryfy(cls, storyId:'StoryId'):
        '''Returns a new StoryId with attributes usable in SQL'''
        parts = asdict(storyId)
        for k,v in parts.items():
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
        return Path().joinpath(*self.asTuple(validOnly=True)[1:offset]) # ignore type for now
    def getFilenameIdx(self):
        if self.type in self.idOnlyGroup:
            return self.id
        elif self.idx:
            return self.idx
        else:
            raise AttributeError


def patchVersion():
    try:
        with open(".git/refs/heads/master", "r") as f:
            v = f.readline()
    except FileNotFoundError:
        v = os.path.getmtime("tl-progress.md")
        v = datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
    except:
        v = "unknown"
    finally:
        return v


class RawDefaultFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter): pass
class Args(argparse.ArgumentParser):
    def __init__(self, desc, defaultArgs=True, types=None, **kwargs) -> None:
        super().__init__(description=desc, conflict_handler='resolve', formatter_class=RawDefaultFormatter, **kwargs)
        self.add_argument("-v", "--version", action="store_true", help="Show version and exit")
        self.add_argument("--read-defaults", "--read-config", action="store_true", help="Overwrite args with data from umatl.json config")
        self.hasDefault = defaultArgs
        if defaultArgs:
            self.add_argument("-t", "--type", choices=types or TARGET_TYPES, default=types[0] if types else TARGET_TYPES[0],
                              help="The type of assets to process.")
            self.add_argument("-s", "--set", help="The set to process")
            self.add_argument("-g", "--group", help="The group to process")
            self.add_argument("-id", help="The id (subgroup) to process")
            self.add_argument("-idx", help="The specific asset index to process")
            self.add_argument("-sid", "-story", "--story", help="The storyid to process, can be partial")
            self.add_argument("--changed", nargs="?", default=False, const=True,
                              help="Limit to changed files (requires git)")
            self.add_argument("-src", default=GAME_ASSET_ROOT)
            self.add_argument("-dst", default=Path("dat/").resolve())
            self.add_argument("-vb", "--verbose", action="store_true", help="Print additional info")
        elif types:
            self.add_argument("-t", "--type", choices=types, default=types[0], help="The type of assets to process.")
    def parse_args(self, *args, **kwargs):
        a = super().parse_args(*args, **kwargs)
        if a.version:
            print(f"Patch version: {patchVersion()}")
            sys.exit()
        if a.read_defaults:
            try:
                cfg = helpers.readJson("umatl.json")
            except FileNotFoundError:
                cfg = createDefaultUmatlConfig()
            # Resolve to make sure it works on both abs and rel paths.
            ctx = str(Path(sys.argv[0]).resolve().relative_to(Path("src").resolve()).with_suffix("")).replace("\\","/")
            for k, v in cfg.get(ctx, {}).items():
                setattr(a, k, v)
        if self.hasDefault and a.story:
            a.story = StoryId.parse(a.type, a.story)
            a.set = a.set or a.story.set
            a.group = a.group or a.story.group
            a.id = a.id or a.story.id
            a.idx = a.idx or a.story.idx
        return a
    @classmethod
    def fake(cls, **kwargs):
        return argparse.Namespace(**kwargs)


class TranslationFile:
    latestVersion = 6
    ver_offset_mdb = 100
    textBlacklist = regex.compile(r"^タイトルコール$|イベントタイトルロゴ表示.*|※*ダミーテキスト|^欠番$")

    def __init__(self, file:Union[str, Path]=None, load=True, readOnly=False):
        self.readOnly = readOnly
        if load:
            if not file: raise RuntimeError("Attempting to load tlfile but no file provided.")
            self.setFile(file)
            self.reload()
        else:
            self.fileExists = False

    class TextData:
        def __init__(self, root: 'TranslationFile', data=None) -> None:
            self.root = root
            self.map = None
            if not data: data = root.textBlocks
            self.data = self.toInterchange(data)

        def get(self, key, default=None):
            if isinstance(key, str) and self.map:
                return self.map.get(key, {}).get('enText', default)
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
                self.map[key]['enText'] = val
            else:
                raise LookupError(f"No index provided for list-format file {self.root.name}")

        def items(self, key="jpText", val="enText"):
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
            self._nativeData = data #todo: change the whole system
            if isinstance(data, dict):
                self.map = dict()
                o = list()
                for i, (k, v) in enumerate(data.items(), start=1):
                    o.append({'jpText': k, 'enText': v, 'blockIdx': i, 'nextBlock': i + 1})
                    self.map[k] = o[-1]
                return o
            return data

        def toNative(self, data=None):
            data = data or self.data
            if (self.root.version == -2 or self.root.version > self.root.ver_offset_mdb) and isinstance(data, list):
                o = dict()
                for e in data:
                    o[e.get("jpText")] = e.get("enText", "")
                return o
            return data

    def _getVersion(self) -> int:
        ver = self.data.get('version', 1)
        if ver == 1 and not isinstance(next(iter(self.data.values())), list):
            ver = -2 
        return ver

    @property
    def textBlocks(self) -> TextData:
        if self.version > 1:
            return self.data['text']
        elif self.version == -2:
            return self.data
        else:
            return list(self.data.values())[0]
    @textBlocks.setter
    def textBlocks(self, val):
        if self.version > 1:
            self.data['text'] = self.TextData(self, val)
        elif self.version == -2:
            self.data = self.TextData(self, val)
        else:
            raise NotImplementedError

    def genTextContainers(self) -> Generator[dict, None, None]:
        for block in self.textBlocks:
            if block['jpText']:
                if self.textBlacklist.match(block['jpText']): continue
                yield block
            if 'coloredText' in block:
                for entry in block['coloredText']:
                    yield entry
            if 'choices' in block:
                for entry in block['choices']:
                    yield entry

    @property
    def bundle(self):
        if self.version > 1:
            return self.data['bundle']
        elif self.version == -2:
            return
        else:
            return list(self.data.keys())[0]

    @property
    def type(self):
        if self.version > 2:
            return self.data['type']
        elif self.version == -2:
            return "dict"
        else:
            return "story/home"

    def getStoryId(self) -> str:
        if self.version > 3:
            return self.data['storyId']
        elif self.version > 2 and self.data['storyId'] != "000000000":
            return self.data['storyId']
        elif self.version == -2:
            return
        else:
            isN = regex.compile(r"\d+")
            g, id, idx = self.file.parts[-3:]  # project structure provides at least 3 levels, luckily
            if not isN.match(g): g = ""
            if not isN.match(id): id = ""
            idx = isN.match(idx)[0]
            return f"{g}{id}{idx}"

    def reload(self):
        self.data = helpers.readJson(self.file)
        self.fileExists = True  # should error if it does not
        self.init()

    def save(self):
        if self.fileExists and self._snapshot == json.dumps(self.data, ensure_ascii=False, default=helpers._to_json): return
        assert self.file
        if 3 < self.version < self.ver_offset_mdb:
            self.data['modified'] = currentTimestamp()
        helpers.writeJson(self.file, self.data)

    def snapshot(self, copyFrom=None):
        if self.readOnly: return
        elif copyFrom:
            self._snapshot = copyFrom._snapshot
            self.fileExists = copyFrom.fileExists
            # Gets written correctly on save anyway but copyFrom means we're trying to "restore" a state (partially):
            mod = copyFrom.data.get('modified')
            if mod: self.data['modified'] = mod
        else:
            self._snapshot = json.dumps(self.data, ensure_ascii=False, default=helpers._to_json)

    def setFile(self, file:Union[str, Path]):
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
            self.data['text'] = self.TextData(self)
        if snapshot: self.snapshot()

    @classmethod
    def fromData(cls, data, snapshot=False):
        c = cls(load=False)
        c.data = {'version': cls.latestVersion, **data}
        c.init(snapshot)
        return c
    @classmethod
    def rename(cls, tlFile:'TranslationFile', newName:str=None):
        '''Renames the physical file in the same dir. Dev helper method.'''
        if not tlFile.fileExists:
            return
        if newName is None:
            idx = StoryId.parse(tlFile.type, tlFile.getStoryId()).idx
            title = tlFile.data.get('title')
            newName = f"{idx} ({title}).json" if title else f"{idx}.json"
        newName = tlFile.file.parent.joinpath(helpers.sanitizeFilename(newName))
        tlFile.file.rename(newName)
        tlFile.setFile(newName)


class GameBundle:
    editMark = b"\x08\x04"

    def __init__(self, path, load=True, bType="story") -> None:
        self.bundlePath = Path(path)
        self.bundleName = self.bundlePath.stem
        self.bundleType = bType
        self.exists = self.bundlePath.exists()
        self.data = None
        self.patchData:bytes = b""
        self._autoloaded = load
        self._patchedState = None

        if load:
            self.load()

    def markPatched(self, tlFile: TranslationFile):
        m = tlFile.data.get("modified", b"")
        if m:
            m = m.to_bytes(5, byteorder='big', signed=False)
            # Have a nice day and good training if you're reading this in the year 15xxx somewhere :spemini:
        self.patchData = m + self.editMark

    @property
    def isPatched(self):
        return self.readPatchState()
    @isPatched.setter
    def isPatched(self, v):
        self._patchedState = v

    def readPatchState(self, customPath=None):
        if not customPath and self._patchedState is not None: return self._patchedState
        try:
            with open(customPath or self.bundlePath, "rb") as f:
                f.seek(-7, os.SEEK_END)
                modified = f.read(5)
                mark = f.read(2)
                if mark == self.editMark:
                    self._patchedState = True
                    try:
                        modified = int.from_bytes(modified, byteorder='big')
                        self.patchedTime = modified
                    except:
                        self.patchedTime = None
                else:
                    self._patchedState = False
        except:
            self._patchedState = False
        return self._patchedState

    def getAssetData(self, pathId: int):
        if a := self.assets.get(pathId):
            return a.read_typetree()
        else: return None

    def load(self):
        # UnityPy does not error and loads empty files
        if not self.exists:
            raise FileNotFoundError

        self.data = UnityPy.load(str(self.bundlePath))
        if self._autoloaded: self.readPatchState()
        self.rootAsset: ObjectReader = next(iter(self.data.container.values())).get_obj()
        self.assets: dict[str, ObjectReader] = self.rootAsset.assets_file.files
        return self

    def save(self, dstFolder:Path=None, dstName:str=None):
        if not self.data: return

        b = self.data.file.save() + self.patchData
        fn = dstName or self.data.file.name
        fp = ((dstFolder / fn[0:2]) if dstFolder else self.bundlePath.parent) / fn
        fp.parent.mkdir(parents=True, exist_ok=True)
        with open(fp, "wb") as f:
            f.write(b)
        self.isPatched = True


    @classmethod
    def fromName(cls, name, **kwargs):
        '''Create a bundle by hash/name from the default game dir. kwargs passed to constructor'''
        bundlePath = PurePath(GAME_ASSET_ROOT, name[0:2], name)
        return cls(bundlePath, **kwargs)

    @staticmethod
    def createPath(dstFolder, dstName):
        return PurePath(dstFolder, dstName[0:2], dstName)


def currentTimestamp():
    return int(datetime.now(timezone.utc).timestamp())

def createDefaultUmatlConfig():
    data = {
        "import": {
            "update": True,
            "skip_mtl": False
        },
        "mdb/import": {
            "skill_data": False
        }
    }
    try:
        helpers.writeJson("umatl.json", data, 2)
    except PermissionError:
        print("Error: Lacking permissions to create the config file in this location. \nEdit the patch folder's permissions or move it to a different location.")
        sys.exit()
    print("Uma-tl uses the umatl.json config file for user preferences when requested.\n"
        "This seems to be your first time running uma-tl this way so a new file was created.\n"
        "Uma-tl has quit without doing anything this first time so you can edit the config before running it again. Defaults are:")
    print(json.dumps(data, indent=2))
    sys.exit()
