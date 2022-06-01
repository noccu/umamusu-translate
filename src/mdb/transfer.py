import sys
from os.path import realpath
sys.path.append(realpath("src"))
import csv
import common
import helpers
from pathlib import Path
import re

def parseArgs():
    ap = common.Args("Transfers missing data from mdb patch files to Translation Files", False)
    ap.add_argument("-src", type=Path, default=Path("../umamusume-db-translate/src/data").resolve(), help="mdb patch data dir")
    ap.add_argument("-f", "--file", type=Path, help="Specific file to transfer/convert. Otherwise all files in tl folder, or src in convert mode.")
    ap.add_argument("-convert", action="store_true", help="Convert mode (csv -> tlfile).")
    ap.add_argument("-O", "--overwrite", action="store_true", help="Overwrite destinations.")
    return ap.parse_args()

def readCsv(path: Path):
    data = dict()
    try:
        file = open(path, "r", newline='', encoding="utf8")
    except FileNotFoundError:
        print("Not found:", path)
        return
    with file:
        for i, row in enumerate(file):
            if i == 0: continue # skip header
            m = re.match(r"^\"(.+)(?<!\\)\", ?(?<!\\)\"(.+)\"\r?$", row)
            if m:
                data[m.group(1)] = re.sub(r'\\"', "\"", m.group(2))
    return data

def main():
    args = parseArgs()
    if args.file:
        files = [args.file]
    elif args.convert:
        files = args.src.glob("*.csv")
    else:
        files = Path("translations/mdb").glob("*.json")

    for file in files:
        if args.convert:
            csvPath = file 
            tlFile = Path("translations/mdb", csvPath.with_suffix(".json").name)
            if not args.overwrite and tlFile.exists():
                print(f"Output exists, skipping: {tlFile}")
                continue
        else:
            csvPath = Path(args.src, file.stem + ".csv")
            tlFile = common.TranslationFile(file)

        csvData = readCsv(csvPath)
        if args.convert:
            helpers.writeJson(tlFile, {'version': 101, 'type': "mdb", 'lineLength': 0, 'text': csvData})
        else:
            for k, v in tlFile.textBlocks.items():
                if v: continue
                if k in csvData:
                    tlFile.textBlocks[k] = csvData[k]
            tlFile.save()

if __name__ == '__main__':
    main()