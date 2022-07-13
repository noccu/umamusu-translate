import common
import helpers


NAMES_DICT = helpers.readJson("translations/mdb/uma-name.json").get("text")
NAMES_DICT.update(helpers.readJson("translations/mdb/miscellaneous.json"))
NAMES_DICT.update(helpers.readJson("src/data/names.json"))


def translate(file: common.TranslationFile):
    for block in file.textBlocks:
        name = block.get('jpName')
        if name is not None:
            if name in common.NAMES_BLACKLIST:
                block['enName'] = ""
            elif name in NAMES_DICT:
                block['enName'] = NAMES_DICT[name]


def main():
    ap = common.Args("Translate many enName fields in Translation Files by lookup")
    ap.add_argument("-src", nargs="*", help="Target Translation File(s), overwrites other file options")
    args = ap.parse_args()

    if args.type in ("race", "lyrics"):
        print("No names in given type.")
        raise SystemExit

    files = args.src or common.searchFiles(args.type, args.group, args.id, args.idx, changed = args.changed)
    for file in files:
        file = common.TranslationFile(file)
        translate(file)
        file.save()
    print(f"Names translated in {len(files)} files.")


if __name__ == "__main__":
    main()
