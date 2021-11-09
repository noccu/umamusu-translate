import os
import UnityPy
import common
from common import GAME_ASSET_ROOT

# Globals & Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("[-g <group>] [-id <id>] [-src <game appdata root>] [-dst <asset save path>] [-O(verwrite)] [-S(ilently skip unchanged)]",
                 "Saves all files to <project root>/dat by default")

IMPORT_GROUP = args.getArg("-g", False)
IMPORT_ID = args.getArg("-id", os.path.realpath("translations/"))
GAME_ASSET_ROOT = args.getArg("-src", GAME_ASSET_ROOT)
SAVE_DIR = args.getArg("-dst", os.path.realpath("dat/"))
OVERWRITE_GAME_DATA = args.getArg("-O", False)
SILENT_SKIP = args.getArg("-S", False)


def get_meta(filePath: str) -> tuple[str, UnityPy.environment.files.ObjectReader]:
    env = UnityPy.load(filePath)
    return env, next(iter(env.container.values())).get_obj()

# Main import controller
def swapAssetData(jsonImport: dict):
    for assetFileName, jsonObjectList in jsonImport.items():
        env, metadata = get_meta(os.path.join(GAME_ASSET_ROOT, assetFileName[0:2], assetFileName))
        filesList = metadata.assets_file.files

        bundleChanged = True
        assetsSkipped = 0
        for jsonData in jsonObjectList:
            if not jsonData['enText']:
                assetsSkipped += 1
                continue

            try:
                file = filesList[jsonData['pathId']]
            except KeyError:
                print(f"Skipping block {jsonData['blockIdx']} in {assetFileName}: Can't find pathId in original asset")
                continue

            fileData = file.read_typetree()
            fileData['Text'] = jsonData['enText']
            fileData['Name'] = jsonData['enName'] or fileData['Name']

            if 'choices' in jsonData:
                jpChoices, enChoices = fileData['ChoiceDataList'], jsonData['choices']
                if len(jpChoices) != len(enChoices):
                    print(f"Choice lenghts do not match, skipping")
                else:
                    for idx, choice in enumerate(jsonData['choices']):
                        # ? Not sure if guaranteed same order. Maybe do a search on jpText instead?
                        if choice['enText']:
                            jpChoices[idx]['Text'] = choice['enText']

            file.save_typetree(fileData)
        if assetsSkipped == len(jsonObjectList):
            bundleChanged = False
        # There should only be one (assumption made)
        return env, bundleChanged


def saveAsset(env):
    b = env.file.save() #! packer="original" or any compression doesn't seem to work, the game will crash or get stuck loading forever
    fn = env.file.name
    fp = os.path.join(GAME_ASSET_ROOT if OVERWRITE_GAME_DATA else SAVE_DIR, fn[0:2], fn)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "wb") as f:
        f.write(b)

def main():
    print(f"Importing group {IMPORT_GROUP}, id {IMPORT_ID}\nfrom translations\ to {GAME_ASSET_ROOT if OVERWRITE_GAME_DATA else SAVE_DIR}")
    files = common.searchFiles(IMPORT_GROUP, IMPORT_ID)
    print(f"Importing {len(files)} files...")
    for file in files:
        data = common.readJson(file)
        modifiedBundle, changed = swapAssetData(data)
        if changed:
            saveAsset(modifiedBundle)
        elif not SILENT_SKIP:
            print(f"Bundle {modifiedBundle.file.name} not changed, skipping...")


main()
