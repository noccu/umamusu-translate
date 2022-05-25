import sys
from os.path import realpath
sys.path.append(realpath("src"))
import common
import helpers
import sqlite3
from pathlib import Path

def translator(srcdir, files):
    for file in files:
        print(f"Importing {file}...")
        try:
            data = helpers.readJson(Path(srcdir, file + ".json"))
        except FileNotFoundError:
            raise StopIteration
        for k, v in data.items():
            if not v: continue
            yield {'jpText': k, 'enText': v}

def parseArgs():
    ap = common.Args("Imports translations to master.mdb", False)
    ap.add_argument("-src", default="translations/master_db", help="Import path")
    ap.add_argument("-dst", default=common.GAME_MASTER_FILE, help="Path to master.mdb file")
    return ap.parse_args()

def main():
    args = parseArgs()
    with sqlite3.connect(args.dst, isolation_level=None) as db:
        index = helpers.readJson("src/master-db/index.json")
        db.execute("PRAGMA journal_mode = MEMORY;")
        db.execute("BEGIN;")
        for entry in index:
            stmt = f"UPDATE {entry['table']} SET {entry['field']}=:enText WHERE {entry['field']}=:jpText;"
            inputGen = translator(args.src, entry['files'].values() if entry.get("specifier") else [entry['file']])
            db.executemany(stmt, inputGen)
    db.close()

if __name__ == '__main__':
    main()
