import os
from pathlib import Path, PurePath
import sys
import json


GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
GAME_ASSET_ROOT = os.path.join(GAME_ROOT, "dat")
GAME_META_FILE = os.path.join(GAME_ROOT, "meta")
GAME_MASTER_FILE = os.path.join(GAME_ROOT, "master/master.mdb")


def searchFiles(targetType, targetGroup, targetId) -> list:
    found = list()
    searchDir = targetType if type(targetType) is os.PathLike else os.path.join("translations", targetType)
    for root, dirs, files in os.walk(searchDir):
        depth = len(dirs[0]) if dirs else 3
        if targetGroup and depth == 2:
            dirs[:] = [d for d in dirs if d == targetGroup]
        elif targetId and depth == 4:
            dirs[:] = [d for d in dirs if d == targetId]
        found.extend(os.path.join(root, file) for file in files)
    return found

def readJson(file) -> dict:
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)

def writeJsonFile(file, data):
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w", encoding="utf8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def findExisting(searchPath: os.PathLike, filePattern: str):
    searchPath = Path(searchPath)
    search = searchPath.glob(filePattern)
    for file in search:
        if file.is_file():
            return file
    return None

class Args:
    parsed = dict()

    def getArg(self, name, default=None) -> str:
        try:
            return self.parsed[name]
        except KeyError:
            return default

    def setArg(self, name, val):
        self.parsed[name] = val

    def parse(self):
        args = sys.argv[1:]
        idx = 0
        while idx < len(args):
            name = args[idx]
            if name.startswith("-"):
                try:
                    val = args[idx+1]
                except IndexError:
                    val = ""
                if val and not val.startswith("-"):
                    if val.startswith('"'):
                        while not val.endswith('"'):
                            idx += 1
                            val += args[idx + 1]
                    self.setArg(name, val)
                    idx += 2  # get next opt
                else:
                    self.setArg(name, True)
                    idx += 1
            else: raise SystemExit("Invalid arguments")
        return self

class TranslationFile:
    def __init__(self, file):
        self.file = file
        self.name = PurePath(file).name
        self.data = readJson(file)
        self.version = self._getVersion()

    def _getVersion(self) -> int:
        if 'version' in self.data:
            return self.data['version']
        else:
            return 1

    def getTextBlocks(self) -> list:
        if self.version > 1:
            return self.data['text']
        else:
            return list(self.data.values())[0]

    def getBundle(self):
        if self.version > 1:
            return self.data['bundle']
        else:
            return list(self.data.keys())[0]

    def getType(self):
        if self.version > 2:
            return self.data['type']
        else:
            return "story/home"

    def save(self):
        writeJsonFile(self.file, self.data)

def usage(args: str, *msg: str):
    joinedMsg = '\n'.join(msg)
    print(f"Usage: {sys.argv[0]} {args}\n{joinedMsg}")
    raise SystemExit
