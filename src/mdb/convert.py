import sys
from os.path import realpath
sys.path.append(realpath("src"))
import csv
import common
import helpers
from pathlib import Path
import re

def parseArgs():
    ap = common.Args("Converts mdb patch files to uma-tl format", False)
    ap.add_argument("-src", default=Path("../umamusume-db-translate/src/data").resolve(), help="mdb patch data dir")
    ap.add_argument("-file", type=Path, help="Specific file to convert. Otherwise all files in tl folder.")
    return ap.parse_args()

def main():
    args = parseArgs()
    if args.file:
        files = [args.file]
    else:
        files = Path("translations/mdb").glob("*.json")

    for file in files:
        tlFile = common.TranslationFile(file)
        csvData = dict()
        csvPath = Path(args.src, file.stem + ".csv")
        try:
            csvfile = open(csvPath, "r", newline='', encoding="utf8")
        except FileNotFoundError:
            print("Not found:", csvPath)
            continue
        with csvfile:
            for row in csvfile:
                m = re.match(r"^\"(.+)(?<!\\)\", ?(?<!\\)\"(.+)\"$", row)
                if m:
                    csvData[m.group(1)] = re.sub(r'\\"', "\"", m.group(2))
        for k, v in tlFile.textBlocks.items():
            if v: continue
            if k in csvData:
                tlFile.textBlocks[k] = csvData[k]
        tlFile.save()

if __name__ == '__main__':
    main()