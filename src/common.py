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
TARGET_TYPES =  ["story", "home", "race", "lyrics", "preview"]
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
    def __init__(self, desc, defaultArgs = True, **kwargs) -> None:
        if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--version"):
            print(f"Patch version: {patchVersion()}")
            sys.exit()
        super().__init__(description=desc, conflict_handler='resolve', formatter_class=RawDefaultFormatter, **kwargs)
        if defaultArgs:
            self.add_argument("-v", "--version", action="store_true", default=argparse.SUPPRESS, help="Show version and exit")
            self.add_argument("-t", "--type", choices=TARGET_TYPES, default=TARGET_TYPES[0], help="The type of assets to process.")
            self.add_argument("-g", "--group", help="The group to process")
            self.add_argument("-id", help="The id (subgroup) to process")
            self.add_argument("-idx", help="The specific asset index to process")
            self.add_argument("-src", default=GAME_ASSET_ROOT)
            self.add_argument("-dst", default=Path("dat/").resolve())

class TranslationFile:
    latestVersion = 5
    def __init__(self, file):
        self.file = file
        self.name = PurePath(file).name
        self.reload()
        self.version = self._getVersion()

    def _getVersion(self) -> int:
        if 'version' in self.data:
            return self.data['version']
        else:
            return 1

    @property
    def textBlocks(self) -> list[dict]:
        if self.version > 1:
            return self.data['text']
        else:
            return list(self.data.values())[0]

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
    def save(self):
        helpers.writeJson(self.file, self.data)
