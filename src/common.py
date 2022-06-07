import argparse
import os
from pathlib import Path, PurePath
import sys
from typing import Generator
import regex
from datetime import datetime, timezone
import helpers

GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
GAME_ASSET_ROOT = os.path.join(GAME_ROOT, "dat")
GAME_META_FILE = os.path.join(GAME_ROOT, "meta")
GAME_MASTER_FILE = os.path.join(GAME_ROOT, "master/master.mdb")
SUPPORTED_TYPES =  ["story", "home", "race", "lyrics", "preview", "mdb"] # update indexing on next line
TARGET_TYPES =  SUPPORTED_TYPES[:5]
NAMES_BLACKLIST = ["<username>", "", "モノローグ"] # special-use game names, don't touch


def searchFiles(targetType, targetGroup, targetId, targetIdx = False) -> list:
    found = list()
    isJson = lambda f: PurePath(f).suffix == ".json"
    searchDir = targetType if type(targetType) is os.PathLike else os.path.join("translations", targetType)
    for root, dirs, files in os.walk(searchDir):
        depth = len(dirs[0]) if dirs else -1
        if targetGroup and depth == 2:
            dirs[:] = [d for d in dirs if d == targetGroup]
        elif targetId:
            if targetType in ("lyrics", "preview"):
                found.extend(os.path.join(root, file) for file in files if PurePath(file).stem == targetId and isJson(file))
                continue
            elif depth == 4:
                dirs[:] = [d for d in dirs if d == targetId]
        if targetIdx and files:
            found.extend(os.path.join(root, file) for file in files if file.startswith(targetIdx) and isJson(file))
        else: found.extend(os.path.join(root, file) for file in files if isJson(file))
    return found

def parseStoryId(t, input, fromPath = True) -> tuple:
    if t == "home":
        if fromPath:
            input = input[-10:]
            return input[:2], input[3:7], input[7:]
        else:
            return input[:2], input[2:6], input[6:]
    elif t == "lyrics":
        if fromPath: input = input[-11:-7]
        return None, None, input
    elif t == "preview":
        if fromPath: input = input[-4:]
        return None, None, input
    else:
        # story and storyrace
        if fromPath: input = input[-9:]
        return  input[:2], input[2:6], input[6:9]

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
    def __init__(self, desc, defaultArgs = True, types = None, **kwargs) -> None:
        if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--version"):
            print(f"Patch version: {patchVersion()}")
            sys.exit()
        super().__init__(description=desc, conflict_handler='resolve', formatter_class=RawDefaultFormatter, **kwargs)
        if defaultArgs:
            self.add_argument("-v", "--version", action="store_true", default=argparse.SUPPRESS, help="Show version and exit")
            self.add_argument("-t", "--type", choices=types or TARGET_TYPES, default=types[0] if types else TARGET_TYPES[0], help="The type of assets to process.")
            self.add_argument("-g", "--group", help="The group to process")
            self.add_argument("-id", help="The id (subgroup) to process")
            self.add_argument("-idx", help="The specific asset index to process")
            self.add_argument("-src", default=GAME_ASSET_ROOT)
            self.add_argument("-dst", default=Path("dat/").resolve())
        elif types:
            self.add_argument("-t", "--type", choices=types, default=types[0], help="The type of assets to process.")

class TranslationFile:
    latestVersion = 5
    ver_offset_mdb = 100

    def __init__(self, file):
        self.file = file
        self.name = PurePath(file).name
        self.reload()

    class TextData:
        def __init__(self, root: 'TranslationFile', data = None) -> None:
            self.root = root
            self.map = None
            if not data: data = root.textBlocks
            self.data = self.toInterchange(data)
        def get(self, key, default = None):
            if isinstance(key, str) and self.map:
                return self.map.get(key, {}).get('enText', default)
            elif isinstance(key, int):
                try:
                    return self.data[key]
                except IndexError:
                    return default
            else:
                raise NotImplementedError
        def set(self, key, val, idx:int = None):
            if isinstance(key, int) and not idx or idx == key:
                self.data[key] = val
            if idx:
                self.data[idx][key] = val
            elif self.map:
                self.map[key]['enText'] = val
            else:
                raise LookupError(f"No index provided for list-format file {self.root.name}")
        def __getitem__ (self, itm):
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

        def toInterchange(self, data = None):
            data = data or self.data
            if isinstance(data, dict):
                self.map = dict()
                o = list()
                for i, (k, v) in enumerate(data.items(), start=1):
                    o.append({'jpText': k, 'enText': v, 'blockIdx': i, 'nextBlock': i + 1})
                    self.map[k] = o[-1]
                return o
            return data
        
        def toNative(self, data = None):
            data = data or self.data
            if self.root.version > self.root.ver_offset_mdb and isinstance(data, list):
                o = dict()
                for e in data:
                    o[e.get("jpText")] = e.get("enText", "")
                return o
            return data

    def _getVersion(self) -> int:
        if 'version' in self.data:
            return self.data['version']
        else:
            return 1

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

    def getStoryId(self):
        if self.version > 3:
            return self.data['storyId']
        elif self.version > 2 and self.data['storyId'] != "000000000":
            return self.data['storyId']
        else:
            isN = regex.compile(r"\d+")
            g, id, idx = PurePath(self.file).parts[-3:] # project structure provides at least 3 levels, luckily
            if not isN.match(g): g = ""
            if not isN.match(id): id = ""
            idx = isN.match(idx)[0]
            return f"{g}{id}{idx}"

    def reload(self):
        self.data = helpers.readJson(self.file)
        self.version = self._getVersion()
        self.data['text'] = self.TextData(self)

    def save(self):
        helpers.writeJson(self.file, self.data)
