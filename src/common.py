import argparse
import json
import os
from pathlib import Path, PurePath
import sys
from typing import Generator
import regex
from datetime import datetime, timezone

import UnityPy
from UnityPy.files import ObjectReader

import helpers
from helpers import IS_WIN

GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
GAME_ASSET_ROOT = os.path.join(GAME_ROOT, "dat")
GAME_META_FILE = os.path.join(GAME_ROOT, "meta")
GAME_MASTER_FILE = os.path.join(GAME_ROOT, "master", "master.mdb")
SUPPORTED_TYPES = ["story", "home", "race", "lyrics", "preview", "ruby", "mdb"]  # Update indexing on next line
TARGET_TYPES = SUPPORTED_TYPES[:-1]  # Omit mdb
NAMES_BLACKLIST = ["<username>", "", "モノローグ"]  # Special-use game names, don't touch


def searchFiles(targetType, targetGroup, targetId, targetIdx=False, changed=False) -> list[str]:
    found = list()
    isJson = lambda f: PurePath(f).suffix == ".json"
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
        searchDir = targetType if type(targetType) is os.PathLike else os.path.join("translations", targetType)
        for root, dirs, files in os.walk(searchDir):
            depth = len(dirs[0]) if dirs else -1
            if targetGroup and depth == 2:
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


# TODO: This is unpacking a string we packed ourselves, refactoring should eliminate this fn entirely.
def parseStoryId(text_type, s) -> tuple:
    if text_type in ("lyrics", "preview"):
        return None, s, s
    else:
        return s[:2], s[2:6], s[6:]


def parseStoryIdFromPath(text_type: str, path: str):
    """Given a text type (story, lyrics, etc.) and a game data filepath, extract and return the group, id, and index."""
    if text_type == "home":
        path = path[-10:]
        return path[:2], path[3:7], path[7:]
    elif text_type == "lyrics":
        return None, None, path[-11:-7]
    elif text_type == "preview":
        return None, None, path[-4:]
    else:  # story and storyrace
        path = path[-9:]
        return path[:2], path[2:6], path[6:9]


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
        if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--version"):
            print(f"Patch version: {patchVersion()}")
            sys.exit()
        super().__init__(description=desc, conflict_handler='resolve', formatter_class=RawDefaultFormatter, **kwargs)
        if defaultArgs:
            self.add_argument("-v", "--version", action="store_true", default=argparse.SUPPRESS,
                              help="Show version and exit")
            self.add_argument("-t", "--type", choices=types or TARGET_TYPES, default=types[0] if types else TARGET_TYPES[0],
                              help="The type of assets to process.")
            self.add_argument("-g", "--group", help="The group to process")
            self.add_argument("-id", help="The id (subgroup) to process")
            self.add_argument("-idx", help="The specific asset index to process")
            self.add_argument("--changed", nargs="?", default=False, const=True,
                              help="Limit to changed files (requires git)")
            self.add_argument("-src", default=GAME_ASSET_ROOT)
            self.add_argument("-dst", default=Path("dat/").resolve())
            self.add_argument("-vb", "--verbose", action="store_true", help="Print additional info")
        elif types:
            self.add_argument("-t", "--type", choices=types, default=types[0], help="The type of assets to process.")
    @classmethod
    def fake(cls, **kwargs):
        return argparse.Namespace(**kwargs)


class TranslationFile:
    latestVersion = 6
    ver_offset_mdb = 100

    def __init__(self, file=None, load=True, readOnly=False):
        self.readOnly = readOnly
        if load:
            if not file: raise RuntimeError("Attempting to load tlfile but no file provided.")
            self.setFile(file)
            self.fileExists = True  # should error if it does not
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
            if self.root.version > self.root.ver_offset_mdb and isinstance(data, list):
                o = dict()
                for e in data:
                    o[e.get("jpText")] = e.get("enText", "")
                return o
            return data

    def _getVersion(self) -> int:
        return self.data['version'] if 'version' in self.data else 1

    @property
    def textBlocks(self) -> TextData:
        if self.version > 1:
            return self.data['text']
        else:
            return list(self.data.values())[0]
    @textBlocks.setter
    def textBlocks(self, val):
        if self.version > 1:
            self.data['text'] = self.TextData(self, val)
        else:
            raise NotImplementedError

    def genTextContainers(self) -> Generator[dict, None, None]:
        for block in self.textBlocks:
            if block['jpText']:
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
        else:
            return list(self.data.keys())[0]

    @property
    def type(self):
        if self.version > 2:
            return self.data['type']
        else:
            return "story/home"

    def getStoryId(self) -> str:
        if self.version > 3:
            return self.data['storyId']
        elif self.version > 2 and self.data['storyId'] != "000000000":
            return self.data['storyId']
        else:
            isN = regex.compile(r"\d+")
            g, id, idx = PurePath(self.file).parts[-3:]  # project structure provides at least 3 levels, luckily
            if not isN.match(g): g = ""
            if not isN.match(id): id = ""
            idx = isN.match(idx)[0]
            return f"{g}{id}{idx}"

    def reload(self):
        self.data = helpers.readJson(self.file)
        self.init()

    def save(self):
        if self.fileExists and self._snapshot == json.dumps(self.data, ensure_ascii=False, default=helpers._to_json): return
        assert self.file
        if self.version < self.ver_offset_mdb:
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

    def setFile(self, file):
        self.file = file
        self.name = PurePath(file).name

    def init(self, snapshot=True):
        self.version = self._getVersion()
        self.escapeNewline = self.type in ("race", "preview", "mdb")
        self.data['text'] = self.TextData(self)
        if snapshot: self.snapshot()

    @classmethod
    def fromData(cls, data, snapshot=False):
        c = cls(load=False)
        c.data = {'version': cls.latestVersion, **data}
        c.init(snapshot)
        return c


class GameBundle:
    editMark = b"\x08\x04"

    def __init__(self, path, load=True) -> None:
        self.bundlePath = Path(path)
        self.bundleName = self.bundlePath.stem
        self.bundleType = "story"
        self.exists = self.bundlePath.exists()
        self.isPatched = False
        self.data = None
        self.patchData:bytes = b""
        self._autoloaded = load

        if load:
            self.load()

    def setPatchState(self, tlFile: TranslationFile):
        m = tlFile.data.get("modified", b"")
        if m:
            m = m.to_bytes(5, byteorder='big', signed=False)
            # Have a nice day and good training if you're reading this in the year 15xxx somewhere :spemini:
        self.patchData = m + self.editMark

    def readPatchState(self, customPath=None):
        try:
            with open(customPath or self.bundlePath, "rb") as f:
                f.seek(-7, os.SEEK_END)
                modified = f.read(5)
                mark = f.read(2)
                if mark == self.editMark:
                    self.isPatched = True
                    try:
                        modified = int.from_bytes(modified, byteorder='big')
                        self.patchedTime = modified
                    except:
                        self.patchedTime = None
        except:
            pass # defer to defaults

    def load(self):
        # UnityPy does not error and loads empty files
        if not self.exists:
            raise FileNotFoundError

        self.data = UnityPy.load(str(self.bundlePath))
        if self._autoloaded: self.readPatchState()
        self.rootAsset: ObjectReader = next(iter(self.data.container.values())).get_obj()
        self.assets: list[ObjectReader] = self.rootAsset.assets_file.files
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
    def fromName(cls, name, load=True):
        bundlePath = PurePath(GAME_ASSET_ROOT, name[0:2], name)
        return cls(bundlePath, load)

    @staticmethod
    def createPath(dstFolder, dstName):
        return PurePath(dstFolder, dstName[0:2], dstName)


def currentTimestamp():
    return int(datetime.now(timezone.utc).timestamp())
