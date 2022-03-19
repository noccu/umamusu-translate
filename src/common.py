import os
from pathlib import Path, PurePath
import sys
import json
from typing import Generator
import regex


GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
GAME_ASSET_ROOT = os.path.join(GAME_ROOT, "dat")
GAME_META_FILE = os.path.join(GAME_ROOT, "meta")
GAME_MASTER_FILE = os.path.join(GAME_ROOT, "master/master.mdb")
TARGET_TYPES =  ["story", "home", "race", "lyrics", "preview"]

def checkTypeValid(t):
    if t in TARGET_TYPES: 
        return True
    print(f"Invalid type: {t}. Expecting one of: {', '.join(TARGET_TYPES)}")
    raise SystemExit


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

def isParseableInt(x):
    try:
        int(x)
        return True
    except ValueError:
        return False
        
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
                if val and (not val.startswith("-") or isParseableInt(val)):
                        # if val.startswith('"'):
                        #     while not val.endswith('"'):
                        #         idx += 1
                        #         val += args[idx + 1]
                        #     val = val[1:-1]
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

    def genTextContainers(self) -> Generator[dict, None, None]:
        for block in self.getTextBlocks():
            if block['jpText']:
                yield block
            if 'coloredText' in block:
                for entry in block['coloredText']:
                    yield entry
            if 'choices' in block:
                for entry in block['choices']:
                    yield entry

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

    def getStoryId(self):
        if self.version > 3:
            return self.data['storyId']
        elif self.version > 2 and self.getType() != "000000000":
            return self.data['storyId']
        else:
            isN = regex.compile(r"\d+")
            g, id, idx = PurePath(self.file).parts[-3:] # project structure provides at least 3 levels, luckily
            if not isN.match(g): g = ""
            if not isN.match(id): id = ""
            idx = isN.match(idx)[0]
            return f"{g}{id}{idx}"

    def save(self):
        writeJsonFile(self.file, self.data)

def isJapanese(text):
    # Should be cached according to docs
    return regex.search(r"[\p{scx=Katakana}\p{scx=Hiragana}\p{Han}\p{InHalfwidth_and_Fullwidth_Forms}\p{General_Punctuation}]{3,}", text)

def usage(args: str, *msg: str):
    joinedMsg = '\n'.join(msg)
    print(f"Usage: {sys.argv[0]} {args}\n{joinedMsg}")
    raise SystemExit
