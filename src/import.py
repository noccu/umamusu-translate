import os
import sys
import UnityPy
import json
import re

# Globals
GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
IMPORT_DIR = os.path.realpath("translations/")
SAVE_DIR = os.path.realpath("dat/")
IMPORT_GROUP = False
IMPORT_ID = False
OVERWRITE_GAME_DATA = False
GAME_DATA_DIR = os.path.join(GAME_ROOT, "dat")

# Parameter parsing
opts = sys.argv[1:]
idx = 0
while idx < len(opts):
    opt = opts[idx]
    idx += 1  # get arg
    if opt == "-g":
        IMPORT_GROUP = opts[idx]
    elif opt == "-id":
        IMPORT_ID = opts[idx]
    elif opt == "-src":
        GAME_ROOT = opts[idx]
    elif opt == "-dst":
        SAVE_DIR = opts[idx]
    elif opt == "-O":
        OVERWRITE_GAME_DATA = True
        continue  # no arg
    else:
        quit()
    idx += 1  # get next opt


def quit():
    raise SystemExit(
        f"Usage: {sys.argv[0]} [-g <group>] [-id <id>] [-src <game appdata root>] [-dst <asset save path>] [-O]\nSaves all files to <project root>/dat by default")

def get_meta(filePath: str) -> tuple[str, UnityPy.environment.files.ObjectReader]:
    env = UnityPy.load(filePath)
    return env, next(iter(env.container.values())).get_obj()

# Main import controller
def swapAssetData(jsonImport: dict):
    for assetFileName, jsonObjectList in jsonImport.items():
        env, metadata = get_meta(os.path.join(GAME_ROOT, "dat", assetFileName[0:2], assetFileName))
        filesList = metadata.assets_file.files

        for jsonData in jsonObjectList:
            if not jsonData['enText']: continue
            
            try:
                file = filesList[jsonData['pathId']]
            except KeyError:
                print (f"Skipping block {jsonData['blockIdx']} in {assetFileName}: pathId/file error")
                continue
            fileData = file.read_typetree()

            fileData['Text'] = jsonData['enText']
            fileData['Name'] = jsonData['enName'] or fileData['Name']

            if 'choices' in jsonData:
                choices, enChoices = fileData['ChoiceDataList'], jsonData['choices']
                if len(choices) != len(enChoices):
                    print(f"Choice lenghts do not match, skipping")
                else:
                    for idx, choice in enumerate(jsonData['choices']):
                        #? Not sure if guaranteed same order. Maybe do a search on jpText instead?
                        if choice['enText']:
                            choices[idx]['Text'] = choice['enText']

            file.save_typetree(fileData)
        # There should only be one (assumption made)
        return env

def saveAsset(env):
    b = env.file.save(packer="original")
    fn = env.file.name
    fp = os.path.join(GAME_DATA_DIR if OVERWRITE_GAME_DATA else SAVE_DIR, fn[0:2], fn)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "wb") as f:
        f.write(b)

def readJson(file):
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)

def searchFiles():
    found = list()
    for root, dirs, files in os.walk("translations/"):
        depth = len(dirs[0]) if dirs else 3
        if IMPORT_GROUP and depth == 2:
            dirs[:] = [d for d in dirs if d == IMPORT_GROUP]
        elif IMPORT_ID and depth == 4:
            dirs[:] = [d for d in dirs if d == IMPORT_ID]
        found.extend(files)
    return found

def main():
    print(searchFiles())
    return

    dbgTestPath = r"translations\50\1017\100 (シンボリルドルフ登場！).json"
    d = readJson(dbgTestPath)
    enAsset = swapAssetData(d)
    saveAsset(enAsset)

    return

    importFiles = readFiles()
    gameAssets = readGameFiles()
    for file in importFiles:
        with file:
            content = readJson(file)
        swapAssetData(content);


main()
