import shutil
import sqlite3
from os import path
import common
from common import GAME_META_FILE, GAME_ASSET_ROOT

# Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("[-t <type>] [-n <unity filepath wildcard>] [-c <specific hash/asset filename>] [-g <story group>] [-id <story id>] [-O(verwrite)]",
                 "All args are combined with AND")
TARGET_TYPE = args.getArg("-t", "")
TARGET_HASHES = args.getArg("-c", False)
TARGET_NAME = args.getArg("-n", "")
# story shortcuts
TARGET_GROUP = args.getArg("-g", False)
TARGET_ID = args.getArg("-id", False)
DESTINATION = args.getArg("-dst", "dump/")
OVERWRITE_DST = args.getArg("-O", False)


def buildSqlStmt():
    stmt = "select n, h from a"
    firstExpr = True

    def add(expr: str):
        nonlocal firstExpr, stmt
        if firstExpr:
            stmt += f" where {expr}"
            firstExpr = False
        else:
            stmt += f" and {expr}"

    if TARGET_TYPE:
        add(f"m = {TARGET_TYPE}")
    if TARGET_NAME:
        add(f"n like '%{TARGET_NAME}%'")
    if TARGET_HASHES:
        add(f"h in ('{TARGET_HASHES}')")
    if TARGET_GROUP:
        add(f"n like 'story/data/{TARGET_GROUP}/____/storytimeline%'")
    if TARGET_ID:
        add(f"n like 'story/data/__/{TARGET_ID}/storytimeline%'")

    return None if firstExpr else stmt


def getFiles():
    with sqlite3.connect(GAME_META_FILE) as db:
        stmt = buildSqlStmt()
        if not stmt:
            raise SystemExit("Invalid statement. No args given? Pass -h for usage")
        cur = db.execute(stmt)
        return cur


def main():
    for filepath, hash in getFiles():
        dst = path.join(DESTINATION, hash)
        if OVERWRITE_DST or not path.exists(dst):
            src = path.join(GAME_ASSET_ROOT, hash[:2], hash)
            print(f"Copying {src} to {dst}")
            shutil.copyfile(src, dst)


main()
