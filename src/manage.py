import json
from pathlib import PurePath, Path
import shutil

import common
import helpers

ROOT = PurePath("src")
LOCAL_DUMP = ROOT / "data" / "static_dump.json"
LOCALIFY_DATA_DIR = Path("localify") / "localized_data"
HASH_FILE_STATIC = LOCALIFY_DATA_DIR / "static.json"
HASH_FILE_DYNAMIC = LOCALIFY_DATA_DIR / "dynamic.json"
CONFIG_FILE = Path("localify")  / "config.json"
TL_FILE = PurePath("translations") / "localify" / "ui.json"
STRING_BLACKLIST = ("現在の予約レース",)

def updateTlData(dumpData: dict, tlData: dict):
    for _, text in dumpData.items():
        if text not in tlData:
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

        inBlacklist = False
        if translatedText and not (inBlacklist := key in STRING_BLACKLIST):
            # special case for effectively removing text
            data[key] = "" if translatedText == "<empty>" else translatedText
        else:
            if inBlacklist: print(f"{key} causes issues with the game, skipping...")
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
            data = {**localDumpData, **data} if args.overwrite else {**data, **localDumpData}
            # now that we've already read the external file in path, we no longer need it
            # so we can swap it to local updating
            path = LOCAL_DUMP
        # copy to list so we don't run into issues deleting keys in our loop obj
        for key, val in list(data.items()):
            # remove non-japanese data (excluding static)
            if len(key) > 5 and helpers.isEnglish(val):
                del data[key]
            # remove animated text
            else:
                if len(animationCheck) == 0 or (val.startswith(animationCheck[-1][1])
                                                and len(val) - len(animationCheck[-1][1]) < 2):
                    animationCheck.append((key, val))
                else:
                    if len(animationCheck) > 4:
                        # and remove it
                        # print(f"Removing animated text: {animationCheck}")
                        for k, _ in animationCheck:
                            del data[k]
                    animationCheck.clear()

        if args.save:
            helpers.writeJson(path, data)
        return data
    else:
        # if it's not a json file then it's definitely external as we only use static_dump.json
        assert isExternal, "Dump file is not json and not external"

        with open(path, "r", encoding="utf8") as f:
            jsonDump = "{" + f.read()[:-2] +"}" # remove trailing newline and comma
            for key, val in json.loads(jsonDump).items():
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
        if k not in tlData:
            tlData[k] = ""


def clean(mode):
    """Clean ui.json and/or static_dump.json of empty translations. Keep the dump's static hashes regardless."""
    translations = {jp: en for jp, en in helpers.readJson(TL_FILE).items() if en}  # Remove empty translations
    if mode in ("both", "ui"):
        helpers.writeJson(file=TL_FILE, data=translations)

    if mode in ("both", "dump"):
        helpers.writeJson(file=DUMP_FILE,
                          data={ui_hash: jp for ui_hash, jp in helpers.readJson(DUMP_FILE).items()
                                if len(ui_hash) <= 5 or jp in translations})  # Keep static hashes even if untranslated
    
    if mode == "dyn":
        staticVals = helpers.readJson(HASH_FILE_STATIC).values()
        dynamicData = helpers.readJson(HASH_FILE_DYNAMIC)
        for hash, en in list(dynamicData.items()):
            if en != "" and en in staticVals:
                del dynamicData[hash]
        helpers.writeJson(HASH_FILE_DYNAMIC, dynamicData)


def order():
    for file in [LOCAL_DUMP, HASH_FILE_STATIC, HASH_FILE_DYNAMIC]:
        data = helpers.readJson(file)
        data = dict(sorted(data.items(), key=lambda x: int(x[0])))
        helpers.writeJson(file, data)


def convertMdb():
    """Writes any mdb files marked to do so in the index as TLG format dicts, returns the paths written."""
    converted = list()
    for entry in helpers.readJson("src/mdb/index.json"):
        files = entry['files'].items() if entry.get('files') else ((entry.get('file'), None),)
        for file, info in files:
            if not (isinstance(info, dict) and info.get('tlg')) and not entry.get('tlg'):
                continue
            subdir = entry['table'] if entry.get("subdir") else ""
            fn = f"{file}.json"
            tlData = helpers.readJson(Path("translations/mdb") / subdir / fn).get('text', dict())
            data = dict()
            for k,v in tlData.items():
                if not v: continue
                v = TextHasher.normalize(v)
                data[TextHasher.hash(k)] = v
                if entry.get('winBreaks') or (isinstance(info, dict) and info.get('winBreaks')):
                    data[TextHasher.hash(k, True)] = v
            if data:
                path = LOCALIFY_DATA_DIR / entry['table'] / fn
                helpers.writeJson(path, data)
                converted.append(path.relative_to(LOCALIFY_DATA_DIR.parent))
    print(f"Converted {len(converted)} files.")
    return converted

def convertTlFile(tlFile: common.TranslationFile, overwrite=False):
    converted = list()
    path = LOCALIFY_DATA_DIR / tlFile.type / (tlFile.getStoryId() + ".json")
    if not overwrite and path.exists() and path.stat().st_mtime >= tlFile.file.stat().st_mtime:
        return
    data = dict()
    for b in tlFile.genTextContainers():
        if text := b.get('enText'):
            data[TextHasher.hash(b['jpText'])] = TextHasher.normalize(text)
        if name := b.get('enName'):
            data[TextHasher.hash(b['jpName'])] = TextHasher.normalize(name)
    helpers.writeJson(path, data)
    converted.append(path)
    return converted


def updConfigDicts(cfgPath, dictPaths: list):
    """Update the dicts key in the cfgPath file with the given dictPaths."""
    try:
        data = helpers.readJson(cfgPath)
    except FileNotFoundError:
        print("Config file not found")
        return
    dicts = ["localized_data\\dynamic.json", *[str(x) for x in dictPaths]]
    data['dicts'] = dicts
    data['static_dict'] = "localized_data\\static.json"
    data['text_data_dict'] = ""
    data['character_system_text_dict'] = ""
    data['race_jikkyo_comment_dict'] = ""
    data['race_jikkyo_message_dict'] = ""
    data['stories_path'] = ""
    helpers.writeJson(cfgPath, data)

class TextHasher:
    mapA = {ord(c): None for c in ("\r", ",")}
    mapB = {ord(c): None for c in (",")}
    @classmethod
    def hash(cls, text:str, winBreak=False):
        '''Returns a 64bit C hash of text, with full or partial replacements'''
        # Cleaning done by texthashtool. There is a version that cleans \n too, seems unneeded.
        text = TextHasher.normalize(text.translate(cls.mapB if winBreak else cls.mapA), winBreak)
        # Implement vc++ std::hash (FNV1a)
         # mask = 2 ** 64 - 1 # Mask is used to emulate 64bit mult product
        o = 14695981039346656037 # FNV_offset_basis
        for c in text.encode("utf_16_le"):
            o ^= c
            o *= 1099511628211 # FNV_prime
            o &= 18446744073709551615 # Integer form of mask
        return o
    @staticmethod
    def normalize(txt:str, winBreak=False):
        '''Makes sure the text is correct for use in TLG. 
           Windows linebreaks are required for some game content.'''
        return txt.replace("\\n", "\r\n" if winBreak else "\n")


def parseArgs():
    ap = common.Args("Manages localify data files for UI translations", defaultArgs=False)
    ap.add_argument("-new", "--populate", action="store_true",
                    help="Add dump (local or target) entries to static_en.json for translating")
    # ? in hindsight I don't think it's useful to not import as we need both dump and tl file for the whole thing to
    # work right but ok. can't say there's no choice at least :^)
    ap.add_argument("-save", "-add", action="store_true", help="Save target dump entries to local dump on import")
    ap.add_argument("-upd", "--update", action="store_true",
                    help="Create/update the final static.json file used by the dll from static_dump.json and static_en.json")
    ap.add_argument("-clean", "--clean", choices=["dump", "ui", "both", "dyn"],  nargs='?', const="both", default=False,
                    help="Remove untranslated entries from tl file and local dump."
                         'Pass "ui" or "dump" to clean only one or the other file; default "both".')
    ap.add_argument("-sort", "-order", action="store_true", help="Sort keys in local dump and final file")
    ap.add_argument("-O", "--overwrite", action="store_true",
                    help="Overwrite/update local dump keys instead of only adding new ones")
    ap.add_argument("-I", "--import-only", action="store_true",
                    help="Purely import target dump to local and exit. Implies -save and -src (auto mode, can be overridden)")
    ap.add_argument("-M", "--move", action="store_true", help="Move final json files to game dir.")
    ap.add_argument("-src", default=LOCAL_DUMP, const=None, nargs="?", type=PurePath,
                    help="Target dump file for imports. Auto-detects in game dir if no path given", metavar="path")
    ap.add_argument("-tlg", default=None, const=PurePath(helpers.getUmaInstallDir(), "static_dump.json"), nargs="?", type=PurePath,
                    help="Import TLG's static dump too. Auto-detects in game dir if no path given", metavar="path")
    ap.add_argument("-mdb", "--convert-mdb", action="store_true", help="Import some mdb strings for TLG to improve formatting")
    ap.add_argument("-conv", "--convert-asset", nargs='?', const=True, default=False, help="Write TLG versions of [specified] asset files marked as such", metavar="path")
    args = ap.parse_args()

    if args.src is None or (args.import_only and args.src == LOCAL_DUMP):
        args.src = LOCAL_DUMP
        path = helpers.getUmaInstallDir()
        if path:
            path = path / "dump.txt"
            if path.exists():
                args.src = path
            else:
                print("Dump file not found.")
        else:
            print("Couldn't find game path.")

        print(f"Using dump: {args.src}")

    global DUMP_FILE
    DUMP_FILE = args.src

    return args


def main():
    args = parseArgs()

    if args.convert_mdb:
        mdbDicts = convertMdb()
        updConfigDicts(CONFIG_FILE, mdbDicts)
    elif args.convert_asset:
        if args.convert_asset is True:
            files = common.searchFiles(args.type, args.group, args.id, args.idx)
            for file in files:
                convertTlFile(common.TranslationFile(file), overwrite=args.overwrite)
        else: #str
            convertTlFile(common.TranslationFile(args.convert_asset), overwrite=args.overwrite)

    if args.clean:
        clean(args.clean)
        return
    elif args.sort:
        order()
        return

    if args.populate or args.update or args.import_only:
        dumpData = importDump(DUMP_FILE, args)
        if args.import_only:
            return
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
        print("Copying UI translations")
        installDir = helpers.getUmaInstallDir()
        if installDir:
            try:
                dst = installDir / LOCALIFY_DATA_DIR.name
                # dst.mkdir(exist_ok=True)  # Disabling this to check TLG status. First install must be manual.
                # Using rglob for future functionality
                dynFiles = list()
                for f in LOCALIFY_DATA_DIR.rglob("*.json"):
                    subPath = f.relative_to(LOCALIFY_DATA_DIR)
                    fn =  dst / subPath
                    fn.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(f, fn)
                    if len(subPath.parts) > 1:
                        dynFiles.append(LOCALIFY_DATA_DIR.name / subPath)
                updConfigDicts(installDir / "config.json", dynFiles)
            except PermissionError:
                print(f"No permission to write to {installDir}.\nUpdate perms, run as admin, or copy files yourself.")
            except FileNotFoundError as e:
                if not installDir.exists():
                    print(f"Obtained install dir doesn't exist: {str(installDir)}\n"
                           "Possibly corrupt or double game install. Copy UI files manually.")
                elif not dst.exists():
                    print("TLG not installed. See guide if you wish to translate UI elements.")
                else:
                    print(f"Error: {e}\n"
                          f"A patch file with/for UI translations is missing.\n"
                          f"Data may have been corrupted somehow, restore the files in {LOCALIFY_DATA_DIR}.")
        else:
            print("Couldn't find game install path, files not moved.")


if __name__ == '__main__':
    main()
