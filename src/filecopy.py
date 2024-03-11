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
        add(f"n like '{args.path if args.custom else f'%{args.path}%'}' escape '\\'")
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
            add(
                f"n like 'outgame/announceevent/loguiasset/ast_announce_event_log_ui_asset_0{args.id}'"
            )
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
        files = common.searchFiles(type, args.group, args.id, args.idx, changed=args.changed)
        for file in files:
            file = common.TranslationFile(file)
            copy((file.type, file.bundle, None), args)


def removeOldFiles(args):
    cfg = common.UmaTlConfig()
    ts = common.currentTimestamp()
    lastrun = cfg.core.get("lastBackupPrune", 0)
    # Run every ~6 months
    if not args.overwrite and lastrun + 15778476 > ts:
        print(f"Skipping backup pruning as it was last done on {common.timestampToDate(lastrun)}.")
        return 0, 0
    from pathlib import PurePath, Path

    n = 0
    isHash = args.remove_old == "hash"
    files = [Path(p) for p in common.searchFiles(PurePath(args.dst), None, None, jsonOnly=False)]
    print(f"Found {len(files)} files in {args.dst}")
    with sqlite3.connect(GAME_META_FILE) as db:
        for fPath in files:
            q = f"h = '{fPath.name}'" if isHash else f"n like '%{fPath.name}'"
            if not db.execute(f"select h from a where {q}").fetchone():
                Path(fPath).unlink()
                if args.verbose:
                    print(f"Removed {fPath}")
                n += 1
    cfg.core["lastBackupPrune"] = ts
    cfg.save()
    return n, len(files)


def copy(data, args):
    if isinstance(data, common.GameBundle):
        if args.use_pathname:
            raise NotImplementedError
        asset = data
        fileHash = data.bundleName
    else:
        fileType, fileHash, filePath = data
        asset = common.GameBundle.fromName(fileHash, load=False)
        asset.bundleType = fileType  # only used for restoring

    if asset.exists:
        if asset.isPatched:
            if args.verbose:
                print(f"Skipping patched bundle: {asset.bundleName}")
            return 0
    else:
        if args.restore_missing and restore.save(asset, args.restore_args) == 1:
            return copy(data, args)  # retry
        elif args.verbose:
            print(f"Couldn't find {asset.bundlePath}, skipping...")
        return 0

    if args.use_pathname:
        fn = filePath if args.full_path else filePath[max(filePath.rfind("/") + 1, 0) :]
    else:
        fn = fileHash
    dst = path.join(args.dst, fn)
    if args.overwrite or not path.exists(dst):
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


def parseArgs(src=None):
    ap = common.Args("Copy files for backup or testing", types=[*common.TARGET_TYPES, "ruby"])
    ap.add_argument("-c", "--hash", "--checksum", nargs="+", help="Hash/asset filename")
    ap.add_argument("-p", "--path", help="Unity filepath wildcard")
    ap.add_argument(
        "--custom",
        action="store_true",
        help="Ignore additional argument processing.\n\
        Pure SQL queries based on --hash and/or --path",
    )
    ap.add_argument(
        "-miss", "--restore-missing", action="store_true", help="Download missing files."
    )
    ap.add_argument(
        "-name",
        "--use-pathname",
        action="store_true",
        help="Name file in -dst by path name stem instead of hash, for exports.",
    )
    ap.add_argument(
        "--full-path",
        action="store_true",
        help="Use full unity path in save dest, creating folders. Needs -name",
    )
    ap.add_argument("-dst", default="dump/")
    ap.add_argument("-O", dest="overwrite", action="store_true", help="Overwrite existing")
    ap.add_argument(
        "-B",
        "--backup",
        nargs="?",
        default=False,
        const=True,
        help="Backup all assets for which Translation Files exist",
    )
    ap.add_argument(
        "--remove-old",
        nargs="?",
        default=False,
        const="hash",
        choices=["hash", "name"],
        help="Remove backups for old assets that are no longer used",
    )
    return ap.parse_args(src)


def main():
    args = parseArgs()
    if args.backup:
        backup(args)
    elif args.remove_old:
        rem, total = removeOldFiles(args)
        print(f"Removed {rem} old files out of {total} total files from {args.dst}")
    else:
        if args.restore_missing:
            global restore
            import restore

            args.restore_args = restore.parseArgs([])
        n = 0
        for data in getFiles(args):
            n += copy(data, args)
        print(f"Copied {n} files.")


if __name__ == "__main__":
    main()
