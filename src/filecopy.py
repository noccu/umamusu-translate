import shutil
import sqlite3
from os import makedirs, path
import common
from common import GAME_META_FILE, GAME_ASSET_ROOT


def buildSqlStmt(args):
    stmt = "select h from a"
    firstExpr = True

    def add(expr: str):
        nonlocal firstExpr, stmt
        if firstExpr:
            stmt += f" where {expr}"
            firstExpr = False
        else:
            stmt += f" and {expr}"

    if args.type == "lyrics":
        args.type = "live"
    if not args.group:
        args.group = "__"
    if not args.id:
        args.id = "____"

    add(f"m = '{args.type}'") # always set
    if args.name:
        add(f"n like '%{args.name}%'")
    if args.hash:
        hashes = ",".join([f"'{h}'" for h in args.hash])
        add(f"h in ({hashes})")
    if args.type == "story":
        add(f"n like 'story/data/{args.group}/{args.id}/storytimeline%'")
    elif args.type == "home":
        add(f"n like 'home/data/00000/{args.group}/hometimeline_00000_{args.group}_{args.id}%'")
    elif args.type == "race":
        add(f"n like 'race/storyrace/text/storyrace_{args.group}{args.id}%'")
    elif args.type == "live":
        add(f"n like 'live/musicscores/m{args.id}/m{args.id}_lyrics'")
    elif args.type == "preview":
        add(f"n like 'outgame/announceevent/loguiasset/ast_announce_event_log_ui_asset_0{args.id}'")

    return None if firstExpr else stmt

def getFiles(args):
    with sqlite3.connect(GAME_META_FILE) as db:
        stmt = buildSqlStmt(args)
        if not stmt:
            raise SystemExit("Invalid statement. No args given? Pass -h for usage")
        cur = db.execute(stmt)
        return cur

def backup(args):
    print("Backing up extracted files...")
    for type in common.TARGET_TYPES:
        files = common.searchFiles(type, False, False)
        for file in files:
            file = common.TranslationFile(file)
            copy(file.bundle, args)

def copy(hash, args):
    dst = path.join(args.dst, hash)
    src = path.join(GAME_ASSET_ROOT, hash[:2], hash)
    if args.overwrite or not path.exists(dst):
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
    ap = common.Args("Copy files for backup or testing")
    ap.add_argument("-c", "--hash", "--checksum", nargs="+", help="Hash/asset filename")
    ap.add_argument("-n", "--name", help="Unity filepath wildcard")
    ap.add_argument("-dst", default="dump/")
    ap.add_argument("-O", dest="overwrite", action="store_true", help="Overwrite existing")
    ap.add_argument("-B", "--backup", action="store_true", help="Backup all assets for which Translation Files exist")
    args = ap.parse_args()

    if args.backup:
        backup(args)
    else:
        n = 0
        for hash, in getFiles(args):
            n += copy(hash, args)
        print(f"Copied {n} files.")


main()
