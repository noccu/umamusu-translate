import sys
from os.path import realpath
sys.path.append(realpath("src"))
import common
import helpers
import sqlite3
from pathlib import Path

def extract(db: sqlite3.Connection, stmt: str, savePath: Path):
    # In the spirit of the original db patch, we don't modify old files to keep the db order
    try:
        oldData = helpers.readJson(savePath)
    except FileNotFoundError:
        oldData = dict()
    newData = dict()
    cur = db.execute(stmt)
    for row in cur:
        val = row[0]
        newData[val] = oldData.get(val, "")
    helpers.writeJson(savePath, newData)

def parseArgs():
    ap = common.Args("Extracts master.mdb data for translation", False)
    ap.add_argument("-src", default=common.GAME_MASTER_FILE, help="Path to master.mdb file")
    ap.add_argument("-dst", default="translations/master_db", help="Extraction path")
    return ap.parse_args()

def main():
    args = parseArgs()
    index = helpers.readJson("src/master-db/index.json")
    with sqlite3.connect(args.src) as db:
        for entry in index:
            stmt = f"SELECT DISTINCT {entry['field']} FROM {entry['table']}"
            if entry.get("specifier"):
                for specval, filename in entry['files'].items():
                    specStmt = f"{stmt} WHERE {entry['specifier']} = {specval};"
                    extract(db, specStmt, Path(args.dst, filename + ".json"))
            else:
                extract(db, stmt, Path(args.dst, entry['file'] + ".json"))
    db.close()

if __name__ == '__main__':
    main()
