import shutil
import sqlite3
from os import makedirs, path
import common
from common import GAME_META_FILE, GAME_ASSET_ROOT
from re import sub as resub

# Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("[-t <type>] [-n <unity filepath wildcard>] [-c <specific hash/asset filename>] [-g <story group>] [-id <story id>] [-O(verwrite)]",
                 "All args are combined with AND")
TARGET_TYPE = args.getArg("-t", "story")
if TARGET_TYPE == "lyrics": TARGET_TYPE = "live" # consistency with other scripts
TARGET_HASHES = args.getArg("-c", False)
TARGET_NAME = args.getArg("-n", "")
# story shortcuts
TARGET_GROUP = args.getArg("-g", False)
TARGET_ID = args.getArg("-id", False)
DESTINATION = args.getArg("-dst", "dump/")
OVERWRITE_DST = args.getArg("-O", False)
BACKUP = args.getArg("-B", False)


def buildSqlStmt():
    global TARGET_ID
    stmt = "select h from a"
    firstExpr = True

    def add(expr: str):
        nonlocal firstExpr, stmt
        if firstExpr:
            stmt += f" where {expr}"
            firstExpr = False
        else:
            stmt += f" and {expr}"

    if TARGET_TYPE:
        add(f"m = '{TARGET_TYPE}'")
        if TARGET_TYPE == "live" and not TARGET_ID:
            TARGET_ID = "____"
    if TARGET_NAME:
        add(f"n like '%{TARGET_NAME}%'")
    if TARGET_HASHES:
        hashes = resub("(\"?[A-Z0-9]+\"?) ?(?=,|$)", r"'\1'", TARGET_HASHES)
        add(f"h in ({hashes})")
    if TARGET_GROUP:
        if TARGET_TYPE == "story":
            add(f"n like 'story/data/{TARGET_GROUP}/____/storytimeline%'")
        elif TARGET_TYPE == "home":
            add(f"n like 'home/data/00000/{TARGET_GROUP}/hometimeline%'")
        elif TARGET_TYPE == "race":
            add(f"n like 'race/storyrace/text/storyrace_{TARGET_GROUP}____%'")
    if TARGET_ID:
        if TARGET_TYPE == "story":
            add(f"n like 'story/data/__/{TARGET_ID}/storytimeline%'")
        elif TARGET_TYPE == "home":
            add(f"n like 'home/data/00000/__/hometimeline_00000____{TARGET_ID}%'")
        elif TARGET_TYPE == "race":
            add(f"n like 'race/storyrace/text/storyrace___{TARGET_ID}%'")
        elif TARGET_TYPE == "live":
            add(f"n like 'live/musicscores/m{TARGET_ID}/m{TARGET_ID}_lyrics'")

    return None if firstExpr else stmt

def getFiles():
    with sqlite3.connect(GAME_META_FILE) as db:
        stmt = buildSqlStmt()
        if not stmt:
            raise SystemExit("Invalid statement. No args given? Pass -h for usage")
        cur = db.execute(stmt)
        return cur

def backup():
    print("Backing up extracted files...")
    for type in common.TARGET_TYPES:
        files = common.searchFiles(type, False, False)
        for file in files:
            file = common.TranslationFile(file)
            copy(file.bundle)

def copy(hash):
    dst = path.join(DESTINATION, hash)
    src = path.join(GAME_ASSET_ROOT, hash[:2], hash)
    if OVERWRITE_DST or not path.exists(dst):
        try:
            makedirs(path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            print(f"Copied {src} to {dst}")
            return 1
        except FileNotFoundError:
            print(f"Couldn't find {src}, skipping...")
            return 0
    else:
        print(f"Skipping existing: {src}")
        return 0

def main():
    if BACKUP:
        backup()
    else:
        n = 0
        for hash, in getFiles():
            n += copy(hash)
        print(f"Copied {n} files.")


main()
