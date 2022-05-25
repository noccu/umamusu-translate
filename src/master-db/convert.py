import sys
from os.path import realpath
sys.path.append(realpath("src"))
import csv
import common
import helpers
from pathlib import Path

def parseArgs():
    ap = common.Args("Converts mdb patch files to uma-tl format", False)
    ap.add_argument("-src", default=Path("../umamusume-db-translate/src/data").resolve(), help="mdb patch data dir")
    return ap.parse_args()

def main():
    args = parseArgs()
    files = Path("translations/master_db").glob("*.json")

    for file in files:
        jsonData = helpers.readJson(file)
        csvData = dict()
        csvPath = Path(args.src, file.stem + ".csv")
        try:
            csvfile = open(csvPath, "r", newline='', encoding="utf8")
        except FileNotFoundError:
            print("Not found:", csvPath)
            continue
        with csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            for row in reader:
                csvData[row[0]] = row[1]
        for k, v in jsonData.items():
            if v: continue
            if k in csvData:
                jsonData[k] = csvData[k]
        helpers.writeJson(file, jsonData)

if __name__ == '__main__':
    main()