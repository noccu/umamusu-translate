# Script as module to use relative imports. py -m src.static.manage [args]
# TODO: Uhhh... do not do that? Somehow.
from .. import common
from pathlib import PurePath


args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-new|-upd",
                 "Add new strings to tl file, or update/write final file with translations.")

ADD_NEW_TEXT = args.getArg("-new", False)
TRANSLATE_HASHES = args.getArg("-upd", False)


def updateTlData(dumpData: dict, tlData: dict):
    for _, text in dumpData.items():
        if not text in tlData:
            tlData[text] = ""

def updateHashData(dumpData: dict, tlData: dict, hashData: dict):
    for hash, text in dumpData.items():
        if text in tlData and tlData[text]:
            hashData[hash] = tlData[text]

# Usage: use localify dll to dump entries to dump.json (edit the .txt or copy what you like)
# use -new to copy said entries to static_en.json (the tl file), translate the entries you want, use -upd to create the final .json to copy into your localify localized_data dir
def main():
    if not ADD_NEW_TEXT and not TRANSLATE_HASHES:
        raise SystemExit("1 required argument missing.")

    root = PurePath(__file__).parent
    dumpFile = root / "data" / "dump.json"
    hashFile = root / "release" / "localized_data" / "static.json"
    tlFile = root / "data" / "static_en.json"
    dumpData = common.readJson(dumpFile)
    hashData = common.readJson(hashFile)
    tlData = common.readJson(tlFile)

    if ADD_NEW_TEXT:
        updateTlData(dumpData, tlData)
        common.writeJsonFile(tlFile, tlData)
    elif TRANSLATE_HASHES:
        updateHashData(dumpData, tlData, hashData)
        common.writeJsonFile(hashFile, hashData)

main()