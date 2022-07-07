from os import path
import csv

import common
import helpers


def createDict():
    names = helpers.readJson("translations/mdb/uma-name.json")
    names.update(helpers.readJson("translations/mdb/miscellaneous.json"))
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
    ap.add_argument("-src", nargs="*", help="Target Translation File(s), overwrites other file options")
    args = ap.parse_args()

    if args.type in ("race", "lyrics"):
        print("No names in given type.")
        raise SystemExit

    dict = createDict()
    n = translate(dict, args)
    print(f"Names translated in {n} files.")


main()
