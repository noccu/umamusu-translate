import shutil
import sqlite3
from os import makedirs, path
import common
from common import GAME_META_FILE


def buildSqlStmt(args):
    stmt = "select m, h, n from a"
    firstExpr = True

    def add(expr: str):
        nonlocal firstExpr, stmt
        if firstExpr:
            stmt += f" where {expr}"
            firstExpr = False
        else:
            stmt += f" and {expr}"

    sType = args.type
    if args.type == "lyrics":
        args.type = sType = "live"
    elif args.type == "ruby":
        sType = "story"
    if not args.group:
        args.group = "__"
    if not args.id:
        args.id = "____"
    if not args.idx:
        args.idx = "___"

    if args.path:
        add(f"n like '%{args.path}%' escape '\\'")
    if args.hash:
        hashes = ",".join([f"'{h}'" for h in args.hash])
        add(f"h in ({hashes})")
    if not args.custom:
        add(f"m = '{sType}'") 
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
        elif args.type == "ruby":
            storyid = f"{args.group}{args.id}{args.idx}"
            add(f"n like 'story/data/__/____/ast_ruby_{storyid}'")

    return None if firstExpr else stmt


def getFiles(args):
    with sqlite3.connect(GAME_META_FILE) as db:
        stmt = buildSqlStmt(args)
        if not stmt:
            raise SystemExit("Invalid statement. No args given? Pass -h for usage")
        cur = db.execute(stmt)
        return cur


def backup(args):
    print("Backing up non-patched & extracted files...")
    for type in common.TARGET_TYPES if args.backup is True else [args.backup]:
        files = common.searchFiles(type, args.group, args.id, args.idx, changed = args.changed)
        for file in files:
            file = common.TranslationFile(file)
            copy(file.bundle, args)


def copy(data, args):
    fileType, fileHash, filePath = data
    asset = common.GameBundle.fromName(fileHash, load=False)
    asset.bundleType = fileType
    if args.use_pathname:
        fn = filePath if args.full_path else filePath[max(filePath.rfind("/"), 0):] 
    else: fn = fileHash
    dst = path.join(args.dst, fn)
    if not asset.exists:
        if args.restore_missing and restore.save(asset, args.restore_args) == 1:
            return copy(data, args) # retry
        elif args.verbose:
            print(f"Couldn't find {asset.bundlePath}, skipping...")
        return 0
    elif args.overwrite or not path.exists(dst):
        asset.readPatchState()
        if not asset.isPatched:
            try:
                makedirs(path.dirname(dst), exist_ok=True)
                shutil.copyfile(asset.bundlePath, dst)
                print(f"Copied {asset.bundlePath} to {dst}")
                return 1
            except Exception as e:
                print(f"Unknown error: {repr(e)}, skipping...")
                return 0
    else:
        if args.verbose:
            print(f"Skipping existing: {asset.bundleName}")
        return 0


def main():
    ap = common.Args("Copy files for backup or testing")
    ap.add_argument("-c", "--hash", "--checksum", nargs="+", help="Hash/asset filename")
    ap.add_argument("-p", "--path", help="Unity filepath wildcard")
    ap.add_argument("--custom", action="store_true", help="Ignore additional argument processing.\n\
        Pure SQL queries based on --hash and/or --path")
    ap.add_argument("-miss", "--restore-missing", action="store_true", help="Download missing files.")
    ap.add_argument("-name", "--use-pathname", action="store_true", help="Name file in -dst by path name stem instead of hash, for exports.")
    ap.add_argument("--full-path", action="store_true", help="Use full unity path in save dest, creating folders. Needs -name")
    ap.add_argument("-dst", default="dump/")
    ap.add_argument("-O", dest="overwrite", action="store_true", help="Overwrite existing")
    ap.add_argument("-B", "--backup", nargs="?", default=False, const=True, help="Backup all assets for which Translation Files exist")
    args = ap.parse_args()

    if args.backup:
        backup(args)
    else:
        if args.restore_missing:
            global restore
            import restore
            args.restore_args = restore.parseArgs([])
        n = 0
        for data in getFiles(args):
            n += copy(data, args)
        print(f"Copied {n} files.")


main()
