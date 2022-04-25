# Script as module to use relative imports. py -m src.static.manage [args]
# TODO: Uhhh... do not do that? Somehow.
from .. import common
from pathlib import PurePath
import regex as re
import shutil
import winreg


args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-new|-upd [-add] [-src <dumpfile path>] [-clean [both]] [-order] [-O(verwrite duplicate keys in dump with imported)] [-I(mport only the dump from external)] [-M(ove static.json to game dir)]",
                 "Add new strings to tl file, or update/write final file with translations.",
                 "-add imports text files (dumps) given by -src to local dump.json",
                 "-new adds all new entries from dump.json or src file to static_en.json for translating",
                 "-upd creates the final static.json file used by the dll from dump.json and static_en.json",
                 "-clean removes untranslated entries from tl file, or dump and tl file",
                 "-O overwrites local values with external ones, else vice versa")

ADD_NEW_TEXT = args.getArg("-new", False)
TRANSLATE_HASHES = args.getArg("-upd", False)

DO_IMPORT = args.getArg("-add", False) #? in hindsight I don't think it's useful to not import as we need both dump and tl file for the whole thing to work right but ok. can't say there's no choice at least :^)
DO_CLEAN = args.getArg("-clean", False)
DO_ORDER = args.getArg("-order", False)
OVERWRITE_LOCAL_DUMP = args.getArg("-O", False)
IMPORT_DUMP_ONLY = args.getArg("-I", False)
AUTO_MOVE = args.getArg("-M", False)

ROOT = PurePath(__file__).parent
LOCAL_DUMP = ROOT / "data" / "dump.json"
DUMP_FILE: PurePath = args.getArg("-src", LOCAL_DUMP)
if type(DUMP_FILE) is not PurePath: DUMP_FILE = PurePath(DUMP_FILE)
HASH_FILE = PurePath("localify") / "localized_data" / "static.json"
TL_FILE = ROOT / "data" / "static_en.json"


def updateTlData(dumpData: dict, tlData: dict):
    for _, text in dumpData.items():
        if not text in tlData:
            tlData[text] = ""

def updateHashData(dumpData: dict, tlData: dict, hashData: dict):
    for hash, text in dumpData.items():
        try:
            translatedText = tlData[text]
        except:
            translatedText = None

        if translatedText:
            # special case for effectively removing text
            hashData[hash] = "" if translatedText == "<empty>" else translatedText
        else:
            # Remove missing data on update to prevent garbled translations
            if hash in hashData:
                # print(f"Missing {text} at {hash}. Removing existing: {hashData[hash]}")
                del hashData[hash]


def importDump(path: PurePath):
    isExternal = path != LOCAL_DUMP
    # load local dump to update if using an external file
    localDumpData = common.readJson(LOCAL_DUMP) if isExternal else None

    if path.suffix == ".json":
        data = common.readJson(path)
        animationCheck = list()
        if isExternal:
            if OVERWRITE_LOCAL_DUMP: data = {**localDumpData, **data}
            else: data = {**data, **localDumpData}
            # now that we've already read the external file in path, we no longer need it so we can swap it to local for updating
            path = LOCAL_DUMP
        # copy to list so we don't run into issues deleting keys in our loop obj
        for key, val in list(data.items()):
            if len(key) > 5 and common.isEnglish(val):
                # remove non-japanese data (excluding static)
                del data[key]
            else:
                # keep track of animated text
                if len(animationCheck) == 0 or (val.startswith(animationCheck[-1][1]) and len(val) - len(animationCheck[-1][1]) < 2):
                    animationCheck.append( (key, val) )
                else:
                    if len(animationCheck) > 4:
                        # and remove it
                        # print (f"Removing animated text: {animationCheck}")
                        for key, val in animationCheck:
                            del data[key]
                    animationCheck.clear()

        if DO_IMPORT:
            common.writeJson(path, data)
        return data
    else:
        # if it's not a json file then it's definitely external as we only use dump.json
        if not isExternal: raise AssertionError("Dump file is not json and not external. This is a bug and you should never see this message.") # but just in case

        extract = re.compile(r'"(\d+)": "(.+)",?')
        with open(path, "r", encoding="utf8") as f:
            for line in f:
                match = extract.search(line)
                if match is None: continue
                key, val = map(lambda x: x.encode('latin1', 'backslashreplace').decode('unicode-escape'), match.group(1,2))
                if key and val:
                    # static range always seems to dump in japanese, which helps
                    # also assuming the problem this fixes only occurs/matters for static text
                    if (OVERWRITE_LOCAL_DUMP or key not in localDumpData) and (len(key) < 5 or not common.isEnglish(val)):
                        localDumpData[key] = val
        if DO_IMPORT or IMPORT_DUMP_ONLY:
            common.writeJson(LOCAL_DUMP, localDumpData)
        return localDumpData

def clean():
    dump = common.readJson(DUMP_FILE)
    tlData = common.readJson(TL_FILE)
    targetData = dump if DO_CLEAN == "both" else tlData

    for key, value in list(targetData.items()):
        if DO_CLEAN == "both":
            # ignore translated entries
            if (value in tlData and tlData[value]): continue
            try:
                del tlData[value]
            except KeyError:
                pass
            # ignore static entries in dump
            if len(key) > 5:
                del dump[key]
        else:
            # remove untranslated
            if not value:
                del tlData[key]

    common.writeJson(TL_FILE, tlData)
    if DO_CLEAN == "both": common.writeJson(DUMP_FILE, dump)

def order():
    for file in [LOCAL_DUMP, HASH_FILE]:
        data = common.readJson(file)
        data = dict(sorted(data.items(), key=lambda x: int(x[0])))
        common.writeJson(file, data)

# Usage: use localify dll to dump entries
# use -new to copy said entries to static_en.json (the tl file), translate the entries you want, use -upd to create the final static.json to copy into your game's localized_data dir
def main():
    if not ADD_NEW_TEXT and not TRANSLATE_HASHES and not DO_CLEAN and not IMPORT_DUMP_ONLY and not DO_ORDER and not AUTO_MOVE:
        raise SystemExit("1 required argument missing.")

    if DO_CLEAN:
        clean()
        return
    elif DO_ORDER:
        order()
        return

    if ADD_NEW_TEXT or TRANSLATE_HASHES or IMPORT_DUMP_ONLY:
        dumpData = importDump(DUMP_FILE)
        if IMPORT_DUMP_ONLY: return
        tlData = common.readJson(TL_FILE)

    if ADD_NEW_TEXT:
        updateTlData(dumpData, tlData)
        common.writeJson(TL_FILE, tlData)
    elif TRANSLATE_HASHES:
        hashData = common.readJson(HASH_FILE)
        updateHashData(dumpData, tlData, hashData)
        common.writeJson(HASH_FILE, hashData)

    if AUTO_MOVE:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\DMM GAMES\Launcher\Content\umamusume") as k:
                path = PurePath(winreg.QueryValueEx(k, "Path")[0]) / "localized_data" / "static.json"
                shutil.copyfile(HASH_FILE, path)
                print("static.json moved to game dir")
        except:
            print("Error reading registry. static.json not moved.")

main()