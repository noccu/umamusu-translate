# Script as module to use relative imports. py -m src.static.manage [args]
# TODO: Uhhh... do not do that? Somehow.
from .. import common
from pathlib import PurePath
import regex as re


args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-new|-upd [-add] [-src <dumpfile path>] [-clean [both]] [-O(verwrite duplicate keys in dump with imported)]",
                 "Add new strings to tl file, or update/write final file with translations.",
                 "-add imports text files given by -src to local dump.json",
                 "-clean removes untranslated entries from tl file, or dump and tl file")

ADD_NEW_TEXT = args.getArg("-new", False)
TRANSLATE_HASHES = args.getArg("-upd", False)

DO_IMPORT = args.getArg("-add", False) #? in hindsight I don't think it's useful to not import as we need both dump and tl file for the whole thing to work right but ok. can't say there's no choice at least :^)
DO_CLEAN = args.getArg("-clean", False)
OVERWRITE_LOCAL_DUMP = args.getArg("-O", False)

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
        except KeyError:
            continue

        # special case for effectively removing text
        if translatedText == "<empty>": translatedText = ""
        hashData[hash] = translatedText

def importDump(path: PurePath):
    isExternal = path != LOCAL_DUMP
    # load local dump to update if using an external file
    localDumpData = common.readJson(LOCAL_DUMP) if isExternal else None
    filter = re.compile(r'[^\p{Katakana}\p{Hiragana}\p{Han}]+')

    if path.suffix == ".json":
        data = common.readJson(path)
        if isExternal:
            if OVERWRITE_LOCAL_DUMP: data = {**localDumpData, **data}
            else: data = {**data, **localDumpData}
            # now that we've already read the external file in path, we no longer need it so we can swap it to local for updating
            path = LOCAL_DUMP
        # copy to list so we don't run into issues deleting keys in our loop obj
        for key, val in list(data.items()):
            if filter.fullmatch(val):
                del data[key]
        if DO_IMPORT:
            common.writeJsonFile(path, data)
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
                if key and val and not filter.fullmatch(val):
                    localDumpData[key] = val
        if DO_IMPORT:
            common.writeJsonFile(LOCAL_DUMP, localDumpData)
        return localDumpData

def clean():
    dump = common.readJson(DUMP_FILE)
    tlData = common.readJson(TL_FILE)
    targetData = dump if DO_CLEAN == "both" else tlData

    for key, value in list(targetData.items()):
        if DO_CLEAN == "both":
            # ignore static and translated entries
            if len(key) < 5 or (value in tlData and tlData[value]): continue

            # remove the rest
            try:
                del dump[key]
                del tlData[value]
            except KeyError:
                pass
        else:
            # remove untranslated
            if not value:
                del tlData[key]

    common.writeJsonFile(TL_FILE, tlData)
    if DO_CLEAN == "both": common.writeJsonFile(DUMP_FILE, dump)

# Usage: use localify dll to dump entries
# use -new to copy said entries to static_en.json (the tl file), translate the entries you want, use -upd to create the final static.json to copy into your game's localized_data dir
def main():
    if not ADD_NEW_TEXT and not TRANSLATE_HASHES and not DO_CLEAN:
        raise SystemExit("1 required argument missing.")

    if DO_CLEAN:
        clean()
        return

    dumpData = importDump(DUMP_FILE)
    tlData = common.readJson(TL_FILE)

    if ADD_NEW_TEXT:
        updateTlData(dumpData, tlData)
        common.writeJsonFile(TL_FILE, tlData)
    elif TRANSLATE_HASHES:
        hashData = common.readJson(HASH_FILE)
        updateHashData(dumpData, tlData, hashData)
        common.writeJsonFile(HASH_FILE, hashData)

main()