from common import utils, patch
from common.constants import NAMES_BLACKLIST
from common.types import TranslationFile

NAMES_DICT = None


def loadDict():
    global NAMES_DICT
    names = utils.readJson("src/data/names.json")
    umas = utils.readJson("translations/mdb/char-name.json").get("text")
    misc = utils.readJson("translations/mdb/miscellaneous.json").get("text")
    NAMES_DICT = misc.copy()
    NAMES_DICT.update(names)
    NAMES_DICT.update(umas)
    return names, umas, misc


def translate(file: TranslationFile, forceReload=False, onlyName=None):
    if forceReload or not NAMES_DICT:
        loadDict()
    for block in file.textBlocks:
        jpName = block.get("jpName")
        if jpName is None:
            continue
        if onlyName is not None and onlyName != jpName:
            continue
        if jpName in NAMES_BLACKLIST:
            # Force original names for game compat
            block["enName"] = ""
        elif tlName := NAMES_DICT.get(jpName):
            # Prevent overwriting names with empty strings in case a key is missing tl
            block["enName"] = tlName


def extract(files: list[utils.Path]):
    curNames, *_ = loadDict()
    newNames = 0
    for file in files:
        file = TranslationFile(file)
        for block in file.textBlocks:
            name = block.get("jpName")
            if name in NAMES_BLACKLIST:
                continue
            if name not in NAMES_DICT:
                curNames[name] = block.get("enName", "")
                NAMES_DICT[name] = block.get("enName", "")
                newNames += 1
    utils.writeJson("src/data/names.json", curNames)
    return newNames


def parseArgs(args=None):
    ap = patch.Args("Translate many enName fields in Translation Files by lookup")
    ap.add_argument(
        "-src", nargs="*", type=utils.Path, help="Target Translation File(s), overwrites other file options"
    )
    ap.add_argument(
        "-e",
        "--extract",
        action="store_true",
        help="Write new names from files to names file instead. Copies any existing EN names.",
    )
    ap.add_argument(
        "-l",
        "--limit",
        help="Update only the given name.",
    )
    args = ap.parse_args(args)

    if args.type in ("race", "lyrics"):
        print("No names in given type.")
        raise SystemExit
    return args


def main(args: patch.Args = None):
    args = args or parseArgs(args)
    files = (args.src,) if args.src else patch.searchFiles(
        args.type, args.group, args.id, args.idx, targetSet=args.set, changed=args.changed
    )
    if args.extract:
        n = extract(files)
        print(f"Extracted {n} new names from {len(files)} files.")
    else:
        for file in files:
            file = TranslationFile(file)
            translate(file, onlyName=args.limit)
            file.save()
        print(f"Names translated in {len(files)} files.")


if __name__ == "__main__":
    main()
