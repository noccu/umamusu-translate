import sys
from os.path import realpath
import sqlite3
from pathlib import Path
from importlib import import_module

sys.path.append(realpath("src"))
import common
import helpers
checkPatched = import_module("import").checkPatched


def extract(db: sqlite3.Connection, stmt: str, savePath: Path):
    # In the spirit of the original db patch, we don't modify old files to keep the db order
    savePath = savePath.with_suffix(".json")
    try:
        oldData = common.TranslationFile(savePath)
    except FileNotFoundError:
        print(f"File not found, creating new: {savePath}")
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
        helpers.writeJson(savePath, o)


def parseArgs():
    ap = common.Args("Extracts master.mdb data for translation", defaultArgs=False)
    ap.add_argument("-src", default=common.GAME_MASTER_FILE, help="Path to master.mdb file")
    ap.add_argument("-dst", default="translations/mdb", type=Path, help="Extraction path")
    ap.add_argument("--no-skill-data", action="store_true", help="Skip extracting skill data (requires nodeJS)")
    ap.add_argument("--no-text", action="store_true", help="Skip extracting standard text data")
    ap.add_argument("-f", "--file", help="Extract specific file name (as found in index.json)")
    ap.add_argument("--forced", action="store_true", help="Ignore mdb patch state")
    return ap.parse_args()


def main():
    args = parseArgs()
    if not args.forced and checkPatched(args.src):
        print("master.mdb is patched, aborting extract.")
        return
    index = helpers.readJson("src/mdb/index.json")
    if not args.no_text:
        print("Extracting standard text...")
        with sqlite3.connect(args.src) as db:
            for entry in index:
                stmt = f"SELECT DISTINCT {entry['field']} FROM {entry['table']}"
                if entry.get("specifier"):
                    for filename, specval in entry['files'].items():
                        if not specval or args.file and filename != args.file: continue
                        if isinstance(specval, list):
                            specval = ",".join([str(x) for x in specval])
                            specStmt = f"{stmt} WHERE {entry['specifier']} IN ({specval});"
                        elif isinstance(specval, dict):
                            specStmt = f"{stmt} WHERE {entry['specifier']} = {specval['spec']} AND {specval.get('sql', 'true')};"
                        else:
                            specStmt = f"{stmt} WHERE {entry['specifier']} = {specval};"
                        extract(db, specStmt, args.dst / (entry['table'] if entry.get("subdir") else "") / filename)
                else:
                    if args.file and entry['file'] != args.file: continue
                    extract(db, stmt, args.dst / entry['file'])
        db.close()
    if not args.no_skill_data:
        print("Extracting skill data...")
        # This is just a QoL thing
        from subprocess import run
        run(["node", "src/mdb/scripts/extract-skill-data.js", args.src], check=True)
        run(["py", "src/textprocess.py", "-fsize", "-tl", "6", "-src", "translations/mdb/alt/skill-desc.json"]) # :tmo:


if __name__ == '__main__':
    main()
