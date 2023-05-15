import sys
from os.path import realpath
from pathlib import Path
import re
import csv

sys.path.append(realpath("src"))
import common
import helpers
import textprocess

CSV_FILES_MANUAL_NEWLINE = ("uma-profile-tagline.json", "tutorial-text.json", "support-bonus.json",
                            "special-transfer-thanks.json", "special-transfer-desc.json", "advice.json",
                            "conditions-desc.json", "item-acquisition-methods-shop.json", "load-screens.json",
                            "presents-desc.json", "item-desc.json")
CSV_FILES_PASSTHROUGH = ("uma-epithet-requirements.json", "special-transfer-requirements.json", "miscellaneous.json",
                         "mission-groups.json", "predictions.json")


def parseArgs():
    ap = common.Args("Transfers missing data from mdb patch files to Translation Files", defaultArgs=False)
    ap.add_argument("-src", type=Path, default=Path("../umamusume-db-translate/src/data").resolve(),
                    help="mdb patch data dir")
    ap.add_argument("-f", "--file", type=Path,
                    help="Specific file to transfer/convert. Otherwise all files in tl folder, or src in convert mode.")
    ap.add_argument("-convert", action="store_true", help="Convert mode (csv -> tlfile).")
    ap.add_argument("-R", "--reverse", action="store_true", help="Convert json to csv")
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
            if i == 0:  # skip header
                continue
            m = re.match(r"^\"(.+)(?<!\\)\", ?(?<!\\)\"(.+)\"\r?$", row)
            if m:
                data[m.group(1)] = re.sub(r'\\"', "\"", m.group(2))
    return data


def writeCsv(path, data):
    with open(path, "w", newline='', encoding="utf8") as file:
        file.write("\"text\", \"translation\"\n")
        w = csv.writer(file, quoting=csv.QUOTE_ALL, escapechar="\\", doublequote=False, lineterminator="\n")
        for k, v in data.items():
            # file.write(f"\"{k}\",\"{v}\"\n")
            w.writerow((k, v))


def main():
    args = parseArgs()
    if args.file:
        files = [args.file]
    elif args.convert:
        files = args.src.glob("*.csv")
    else:
        files = list(Path("translations/mdb").glob("**/*.json"))

    for file in files:
        if args.convert:
            csvPath = file
            tlFile = Path("translations/mdb", csvPath.with_suffix(".json").name)
            if not args.overwrite and tlFile.exists():
                print(f"Output exists, skipping: {tlFile}")
                continue
        else:
            csvPath = Path(args.src, file.relative_to("translations/mdb").with_suffix(".csv"))
            tlFile = common.TranslationFile(file)

        csvData = readCsv(csvPath)
        if args.convert:
            helpers.writeJson(tlFile, {'version': 101, 'type': "mdb", 'lineLength': 0, 'text': csvData})
        elif args.reverse:
            nativeJson = False
            if not isinstance(csvData, dict): # file no existo
                nativeJson = csvPath.with_suffix(".json").exists()
                if nativeJson:
                    csvPath = csvPath.with_suffix(".json")
                elif len(csvPath.parts) == 8: # allow to create new file if not in subdir
                    csvData = dict()
                    print(f"Creating {csvPath.name}")
                else: continue

            data = tlFile.textBlocks.toNative()
            ll = tlFile.data.get("lineLength")
            for k, v in data.items():
                if tlFile.name in CSV_FILES_MANUAL_NEWLINE:
                    if ll > 0:
                        data[k] = textprocess.adjustLength(tlFile, v, {"lineLength": int(ll * 0.8),
                                                                       "targetLines": 99,
                                                                       "forceResize": True})
                    # else don't process
                elif tlFile.name not in CSV_FILES_PASSTHROUGH:
                    v = textprocess.cleannewLines(v)
                    data[k] = textprocess.resizeText(tlFile, v, True)
            if nativeJson:
                helpers.writeJson(csvPath, data)
            else:
                writeCsv(csvPath, data)
        else:
            for block in tlFile.textBlocks:
                k, v = block.get("jpText"), block.get("enText")
                if v:
                    continue
                if k in csvData:
                    tlFile.textBlocks[k] = csvData[k]
            tlFile.save()


if __name__ == '__main__':
    main()
