import sys
from os.path import realpath
import sqlite3
from pathlib import Path
import shutil

sys.path.append(realpath("src"))
import common
import helpers


def checkPatched(file: Path):
    with open(file, "rb") as f:
        f.seek(60)
        user_ver = f.read(4)
    return user_ver == b'\x00\x00\x04\x08'

def markPatched(db: sqlite3.Connection):
    db.execute("PRAGMA user_version = 1032;")


def translator(args, entry: dict):
    files = entry['files'].items() if entry.get("specifier") else ((entry.get('file'), None),)
    ovrList = entry.get("overrides")
    if entry.get('tlg') and helpers.isUsingTLG():
        print(f"TLG used: skipping {entry.get('table')}")
        return
    for file, info in files:
        if (isinstance(info, dict) and info.get('tlg')) and helpers.isUsingTLG():
            print(f"TLG used: skipping {file}")
            continue

        # could just make alt/same-name.json a standard and remove the list from index.json
        if ovrList:
            for argName, data in ovrList.items():
                if getattr(args, argName) and file == data[0]:
                    file = data[1]
                    break

        print(f"Importing {file}...")
        try:
            data = common.TranslationFile(args.src / (entry['table'] if entry.get("subdir") else "") / (file + ".json"))
        except FileNotFoundError:
            return

        for e in data.textBlocks:
            if e.get('enText'):
                yield e


def parseArgs():
    ap = common.Args("Imports translations to master.mdb", defaultArgs=False)
    ap.add_argument("-src", default="translations/mdb", type=Path, help="Import path")
    ap.add_argument("-dst", default=common.GAME_MASTER_FILE, help="Path to master.mdb file")
    ap.add_argument("-B", "--backup", action="store_true", help="Backup the master.mdb file")
    ap.add_argument("-R", "--restore", action="store_true", help="Restore the master.mdb file from backup")
    ap.add_argument("-sd", "--skill-data", action="store_true",
                    help="Replace skill descriptions with skill data (effect, conditions, etc)")
    return ap.parse_args()


def main():
    args = parseArgs()
    if args.backup:
        if checkPatched(args.dst):
            print("master.mdb already patched, backup cancelled.")
            return
        shutil.copyfile(args.dst, args.dst + ".bak")
        print("master.mdb backed up.")
        return
    elif args.restore:
        try:
            shutil.copyfile(args.dst + ".bak", args.dst)
        except FileNotFoundError:
            print("No backup found.")
        else:
            print("master.mdb restored.")
        return

    try:
        with sqlite3.connect(args.dst, isolation_level=None) as db:
            index = helpers.readJson("src/mdb/index.json")
            db.execute("PRAGMA journal_mode = MEMORY;")
            db.execute("BEGIN;")
            for entry in index:
                stmt = f"UPDATE {entry['table']} SET {entry['field']}=:enText WHERE {entry['field']}=:jpText;"
                inputGen = translator(args, entry)
                db.executemany(stmt, inputGen)
            markPatched(db)
            # COMMIT; handled by with:
    except sqlite3.OperationalError:
        if not Path(args.dst).exists():
            print(f"The master.mdb file does not exist at {args.dst}.\n\
                    Start the game and login first to download it. Or direct to nonstandard location with -dst")
        else:
            raise
    finally:
        # todo? :tmo:
        if "db" in locals():
            db.close()


if __name__ == '__main__':
    main()
