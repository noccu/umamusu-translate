from ntpath import join
import os
import sys
import json


GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
GAME_ASSET_ROOT = os.path.join(GAME_ROOT, "dat")
GAME_META_FILE = os.path.join(GAME_ROOT, "meta")
GAME_MASTER_FILE = os.path.join(GAME_ROOT, "master/master.mdb")


def searchFiles(IMPORT_GROUP, IMPORT_ID):
    found = list()
    for root, dirs, files in os.walk("translations/"):
        depth = len(dirs[0]) if dirs else 3
        if IMPORT_GROUP and depth == 2:
            dirs[:] = [d for d in dirs if d == IMPORT_GROUP]
        elif IMPORT_ID and depth == 4:
            dirs[:] = [d for d in dirs if d == IMPORT_ID]
        found.extend(os.path.join(root, file) for file in files)
    return found

def readJson(file):
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)

class Args:
    parsed = dict()

    def getArg(self, name, default=None):
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
                    self.setArg(name, val)
                    idx += 2  # get next opt
                else:
                    self.setArg(name, True)
                    idx += 1
            else: raise SystemExit("Invalid arguments")
        return self


def usage(args: str, *msg: str):
    joinedMsg = '\n'.join(msg)
    print(f"Usage: {sys.argv[0]} {args}\n{joinedMsg}")
    raise SystemExit
