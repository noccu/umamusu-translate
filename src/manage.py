import common
import helpers
from pathlib import PurePath
import regex as re
import shutil

ROOT = PurePath("src")
LOCAL_DUMP = ROOT / "data" / "static_dump.json"
HASH_FILE_STATIC = PurePath("localify") / "localized_data" / "static.json"
HASH_FILE_DYNAMIC = PurePath("localify") / "localized_data" / "dynamic.json"
TL_FILE = PurePath("translations") / "localify" / "ui.json"


def updateTlData(dumpData: dict, tlData: dict):
    for _, text in dumpData.items():
        if not text in tlData:
            tlData[text] = ""

def updateHashData(dumpData: dict, tlData: dict, hashData: tuple[dict, dict]):
    for hash, text in dumpData.items():
        translatedText = tlData.get(text)
        if len(hash) > 5:
            data = hashData[1]
            key = hash
        else:
            data = hashData[0]
            key = text
        if translatedText:
            # special case for effectively removing text
            data[key] = "" if translatedText == "<empty>" else translatedText
        else:
            # Remove previously translated hashes that no longer are to prevent garbled text
            if key in data:
                # print(f"Missing {text} at {hash}. Removing existing: {hashData[hash]}")
                del data[key]

def importDump(path: PurePath, args):
    isExternal = path != LOCAL_DUMP
    # load local dump to update if using an external file
    localDumpData = helpers.readJson(LOCAL_DUMP) if isExternal else None

    if path.suffix == ".json":
        data = helpers.readJson(path)
        animationCheck = list()
        if isExternal:
            if args.overwrite: data = {**localDumpData, **data}
            else: data = {**data, **localDumpData}
            # now that we've already read the external file in path, we no longer need it so we can swap it to local for updating
            path = LOCAL_DUMP
        # copy to list so we don't run into issues deleting keys in our loop obj
        for key, val in list(data.items()):
            # remove non-japanese data (excluding static)
            if len(key) > 5 and helpers.isEnglish(val):
                del data[key]
            # remove animated text
            else:
                if len(animationCheck) == 0 or (val.startswith(animationCheck[-1][1]) and len(val) - len(animationCheck[-1][1]) < 2):
                    animationCheck.append( (key, val) )
                else:
                    if len(animationCheck) > 4:
                        # and remove it
                        # print (f"Removing animated text: {animationCheck}")
                        for key, val in animationCheck:
                            del data[key]
                    animationCheck.clear()

        if args.save:
            helpers.writeJson(path, data)
        return data
    else:
        # if it's not a json file then it's definitely external as we only use static_dump.json
        assert isExternal, "Dump file is not json and not external"

        extract = re.compile(r'"(\d+)": "(.+)",?')
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                match = extract.search(line)
                if match is None: continue
                key, val = map(lambda x: x.encode('latin1', 'backslashreplace').decode('unicode-escape'), match.group(1,2))
                if key and val:
                    # static range always seems to dump in japanese, which helps
                    # also assuming the problem this fixes only occurs/matters for static text
                    if (args.overwrite or key not in localDumpData) and (len(key) < 5 or not helpers.isEnglish(val)):
                        localDumpData[key] = val
        if args.save or args.import_only:
            helpers.writeJson(LOCAL_DUMP, localDumpData)
        return localDumpData

def importTlgStatic(dumpPath, tlData):
    data = helpers.readJson(dumpPath)
    for k in data.keys():
        if not k in tlData:
            tlData[k] = ""


def clean(mode):
    dump = helpers.readJson(DUMP_FILE)
    tlData = helpers.readJson(TL_FILE)
    targetData = dump if mode == "both" else tlData

    for key, value in list(targetData.items()):
        if mode == "both":
            if value in tlData:
                # ignore translated entries
                if tlData[value]: continue
                del tlData[value]
            # ignore static entries in dump
            if len(key) > 5:
                del dump[key]
        else:
            # remove untranslated
            if not value:
                del tlData[key]

    helpers.writeJson(TL_FILE, tlData)
    if mode == "both": helpers.writeJson(DUMP_FILE, dump)

def order():
    for file in [LOCAL_DUMP, HASH_FILE_STATIC, HASH_FILE_DYNAMIC]:
        data = helpers.readJson(file)
        data = dict(sorted(data.items(), key=lambda x: int(x[0])))
        helpers.writeJson(file, data)

def parseArgs():
    ap = common.Args("Manages localify data files for UI translations", defaultArgs=False)
    ap.add_argument("-new", "--populate", action="store_true", help="Add dump (local or target) entries to static_en.json for translating")
    #? in hindsight I don't think it's useful to not import as we need both dump and tl file for the whole thing to work right but ok. can't say there's no choice at least :^)
    ap.add_argument("-save", "-add", action="store_true", help="Save target dump entries to local dump")
    ap.add_argument("-upd", "--update", action="store_true", help="Create/update the final static.json file used by the dll from static_dump.json and static_en.json")
    ap.add_argument("-clean", default=False, const=True, nargs="?", help="Remove untranslated entries from tl file, or local dump and tl file")
    ap.add_argument("-sort", "-order", action="store_true", help="Sort keys in local dump and final file")
    ap.add_argument("-O", "--overwrite", action="store_true", help="Overwrite/update local dump keys instead of only adding new ones")
    ap.add_argument("-I", "--import-only", action="store_true", help="Purely import target dump to local and exit. Implies -save and -src (auto mode, can be overridden)")
    ap.add_argument("-M", "--move", action="store_true", help="Move final json files to game dir.")
    ap.add_argument("-src", default=LOCAL_DUMP, const=None, nargs="?", type=PurePath, help="Target dump file for imports. When given without value: auto-detect in game dir")
    ap.add_argument("-tlg", default=None, const=PurePath(common.GAME_ROOT, "static_dump.json"), nargs="?", type=PurePath, help="Import TLG-style static dump. Optionally pass a path to the dump, else auto-detects in game dir")
    args = ap.parse_args()

    if args.src is None or (args.import_only and args.src == LOCAL_DUMP):
        path = helpers.getUmaInstallPath()
        if path: path = path.joinpath("dump.txt")
        else: print("Couldn't find game path.")
        if path.exists():
            args.src = path
        else:
            print("Dump file not found.")
            args.src = LOCAL_DUMP
        print(f"Using dump: {args.src}")
    global DUMP_FILE
    DUMP_FILE = args.src
    return args

def main():
    args = parseArgs()
    if not any([args.populate, args.update, args.clean, args.import_only, args.sort, args.move]):
        raise SystemExit("1 required argument missing.")

    if args.clean:
        clean(args.clean)
        return
    elif args.sort:
        order()
        return

    if args.populate or args.update or args.import_only:
        dumpData = importDump(DUMP_FILE, args)
        if args.import_only: return
        tlData = helpers.readJson(TL_FILE)

    if args.populate:
        updateTlData(dumpData, tlData)
        if args.tlg:
            importTlgStatic(args.tlg, tlData)
        helpers.writeJson(TL_FILE, tlData)
    elif args.update:
        hashData = helpers.readJson(HASH_FILE_STATIC), helpers.readJson(HASH_FILE_DYNAMIC)
        updateHashData(dumpData, tlData, hashData)
        helpers.writeJson(HASH_FILE_STATIC, hashData[0])
        helpers.writeJson(HASH_FILE_DYNAMIC, hashData[1])

    if args.move:
        path = helpers.getUmaInstallPath()
        if path:
            shutil.copyfile(HASH_FILE_STATIC, path.joinpath(HASH_FILE_STATIC.relative_to(HASH_FILE_STATIC.parents[1])))
            shutil.copyfile(HASH_FILE_DYNAMIC, path.joinpath(HASH_FILE_DYNAMIC.relative_to(HASH_FILE_DYNAMIC.parents[1])))
        else:
            print("Couldn't find game path, files not moved.")

if __name__ == '__main__':
    main()