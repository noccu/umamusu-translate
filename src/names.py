from os import path
import csv

import common
import helpers


def createDict(namesFile):
    names = dict()
    with open(namesFile, "r", newline='', encoding="utf8") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in reader:
            names[row[0]] = row[1]
    names.update(helpers.readJson("src/data/names.json"))
    return names


def translate(namesDict, args):
    files = args.src or common.searchFiles(args.type, args.group, args.id, args.idx)

    for file in files:
        file = common.TranslationFile(file)
        for block in file.textBlocks:
            name = block.get('jpName')
            if name is not None:
                if name in common.NAMES_BLACKLIST:
                    block['enName'] = ""
                elif name in namesDict:
                    block['enName'] = namesDict[name]
        file.save()
    return len(files)


def main():
    ap = common.Args("Translate many enName fields in Translation Files by lookup")
    ap.add_argument("-n", dest="namesFile", default="../umamusume-db-translate/src/data/uma-name.csv",
                    help="Path to (external) db-translate's uma-name.csv")
    ap.add_argument("-src", nargs="*", help="Target Translation File(s), overwrites other file options")
    args = ap.parse_args()

    if args.type in ("race", "lyrics"):
        print("No names in given type.")
        raise SystemExit
    if not path.exists(args.namesFile):
        raise FileNotFoundError("You must specify the uma-name.csv file.")

    dict = createDict(args.namesFile)
    n = translate(dict, args)
    print(f"Names translated in {n} files.")


main()
