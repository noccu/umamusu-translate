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
        oldData = common.TranslationFile(savePath)
    except FileNotFoundError:
        oldData = None
    newData = dict()
    cur = db.execute(stmt)
    for row in cur:
        val = row[0]
        newData[val] = oldData.textBlocks.get(val, "") if oldData else ""
    if oldData:
        oldData.textBlocks = newData
        oldData.save()
    else:
        o = {'version': 101, 'type': "mdb", 'lineLength': 0, 'text': newData}
        helpers.writeJson(savePath.with_suffix(".json"), o)

def parseArgs():
    ap = common.Args("Extracts master.mdb data for translation", False)
    ap.add_argument("-src", default=common.GAME_MASTER_FILE, help="Path to master.mdb file")
    ap.add_argument("-dst", default="translations/mdb", help="Extraction path")
    ap.add_argument("-sd", "--skill-data", action="store_true", help="Extract skill data too (requires nodeJS)")
    return ap.parse_args()

def main():
    args = parseArgs()
    index = helpers.readJson("src/mdb/index.json")
    with sqlite3.connect(args.src) as db:
        for entry in index:
            stmt = f"SELECT DISTINCT {entry['field']} FROM {entry['table']}"
            if entry.get("specifier"):
                for filename, specval in entry['files'].items():
                    if isinstance(specval, list):
                        specval = ",".join([str(x) for x in specval])
                        specStmt = f"{stmt} WHERE {entry['specifier']} IN ({specval});"
                    else:
                        specStmt = f"{stmt} WHERE {entry['specifier']} = {specval};"
                    extract(db, specStmt, Path(args.dst, filename))
            else:
                extract(db, stmt, Path(args.dst, entry['file']))
    db.close()
    if args.skill_data:
        print("Extracting skill data...")
        from subprocess import run
        run(["node", "src/mdb/extract-skill-data.js"], check=True)

if __name__ == '__main__':
    main()
