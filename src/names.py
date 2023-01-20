import common
import helpers

NAMES_DICT = None

def loadDict():
    global NAMES_DICT
    names = helpers.readJson("src/data/names.json")
    umas = helpers.readJson("translations/mdb/uma-name.json").get("text")
    misc = helpers.readJson("translations/mdb/miscellaneous.json").get("text")
    NAMES_DICT = misc.copy()
    NAMES_DICT.update(names)
    NAMES_DICT.update(umas)
    return names, umas, misc


def translate(file: common.TranslationFile, forceReload=False):
    if forceReload or not NAMES_DICT: 
        loadDict()
    for block in file.textBlocks:
        jpName = block.get('jpName')
        if jpName is None:
            continue
        if jpName in common.NAMES_BLACKLIST:
            # Force original names for game compat
            block['enName'] = ""
        elif tlName := NAMES_DICT.get(jpName):
            # Prevent overwriting names with empty strings in case a key is missing tl
            block['enName'] = tlName


def extract(files:list):
    curNames, *_ = loadDict()
    newNames = 0
    for file in files:
        file = common.TranslationFile(file)
        for block in file.textBlocks:
            name = block.get("jpName") 
            if name in common.NAMES_BLACKLIST:
                continue
            if name not in NAMES_DICT:
                curNames[name] = ""
                NAMES_DICT[name] = ""
                newNames += 1
    helpers.writeJson("src/data/names.json", curNames)
    return newNames


def main():
    ap = common.Args("Translate many enName fields in Translation Files by lookup")
    ap.add_argument("-src", nargs="*", help="Target Translation File(s), overwrites other file options")
    ap.add_argument("-e", "--extract", action="store_true", help="Target Translation File(s), overwrites other file options")
    args = ap.parse_args()

    if args.type in ("race", "lyrics"):
        print("No names in given type.")
        raise SystemExit

    files = args.src or common.searchFiles(args.type, args.group, args.id, args.idx, changed = args.changed)
    if args.extract:
        n = extract(files)
        print(f"Extracted {n} new names from {len(files)} files.")
    else:
        for file in files:
            file = common.TranslationFile(file)
            translate(file)
            file.save()
        print(f"Names translated in {len(files)} files.")


if __name__ == "__main__":
    main()
