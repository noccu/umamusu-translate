import sys
from os.path import realpath
import sqlite3
from pathlib import Path
import shutil

sys.path.append(realpath("src"))
import common
import helpers


def translator(args, entry: dict):
    files = entry['files'].keys() if entry.get("specifier") else [entry['file']]
    ovrList = entry.get("overrides")
    for file in files:
        # could just make alt/same-name.json a standard and remove the list from index.json
        if ovrList:
            for argName, data in ovrList.items():
                if getattr(args, argName) and file == data[0]:
                    file = data[1]
                    break

        print(f"Importing {file}...")
        try:
            data = common.TranslationFile(args.src / entry['table'] if entry.get("subdir") else "" / file + ".json")
        except FileNotFoundError:
            raise StopIteration

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
            # COMMIT; handled by with:
    finally:
        db.close()


if __name__ == '__main__':
    main()
