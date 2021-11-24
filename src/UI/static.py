from .. import common
from pathlib import PurePath


args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-new|-upd",
                 "Add new strings to tl file, or update new string file with translations.")

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

def main():
    if not ADD_NEW_TEXT and not TRANSLATE_HASHES:
        raise SystemExit("1 required argument missing.")

    root = PurePath(__file__).parent
    dumpFile = root / "dump.json"
    hashFile = root / "static.json"
    tlFile = root / "static_en.json"
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