import os
from pathlib import Path, PurePath
import UnityPy
import json
import sqlite3
import common
from common import GAME_META_FILE, GAME_ASSET_ROOT

# Globals & Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("[-g <group>] [-id <id>] [-l <limit files to process>] [-src <game asset root>] [-dst <extract to path>] [-O(verwrite existing)]",
                 "Any order. Defaults to extracting all text, skip existing")

EXTRACT_TYPE = args.getArg("-t", "story").lower()
if not EXTRACT_TYPE in ["story", "home"]: 
    print(f"Invalid type {EXTRACT_TYPE}")
    raise SystemExit
EXTRACT_GROUP = args.getArg("-g", "__")
EXTRACT_ID = args.getArg("-id", "____")
EXTRACT_LIMIT = args.getArg("-l", -1)
GAME_ASSET_ROOT = args.getArg("-src", GAME_ASSET_ROOT)
EXPORT_DIR = args.getArg("-dst", PurePath("translations").joinpath(EXTRACT_TYPE))
OVERWRITE_DST = args.getArg("-O", False)


def queryDB():
    if EXTRACT_TYPE == "story":
        pattern = f"{EXTRACT_TYPE}/data/{EXTRACT_GROUP}/{EXTRACT_ID}/{EXTRACT_TYPE}timeline%"
    elif EXTRACT_TYPE == "home":
        pattern = f"{EXTRACT_TYPE}/data/00000/{EXTRACT_GROUP}/{EXTRACT_TYPE}timeline_00000_{EXTRACT_GROUP}_{EXTRACT_ID}%"
    db = sqlite3.connect(GAME_META_FILE)
    cur = db.execute(
        f"select h, n from a where n like '{pattern}' limit {EXTRACT_LIMIT};")
    results = cur.fetchall()
    db.close()
    return results


def extractAsset(path, storyId):
    env = UnityPy.load(path)
    index = next(iter(env.container.values())).get_obj()

    if index.serialized_type.nodes:
        tree = index.read_typetree()
        export = {
            'version': 2,
            'bundle': env.file.name,
            'storyId': tree['StoryId'],
            'title' : tree['Title'],
            'text': list()
        }
        for block in tree['BlockList']:
            for clip in block['TextTrack']['ClipList']:
                pathId = clip['m_PathID']
                textData = extractText(index.assets_file.files[pathId])
                if not textData:
                    continue
                textData['pathId'] = pathId  # important for re-importing
                textData['blockIdx'] = block['BlockIndex'] # to help translators look for specific routes
                transferExisting(storyId, textData)
                export['text'].append(textData)
        return export


def extractText(obj):
    if obj.serialized_type.nodes:
        tree = obj.read_typetree()
        o = {
            'jpName': tree['Name'],
            'enName': "",  # todo: auto lookup
            'jpText': tree['Text'],
            'enText': "",
            'nextBlock': tree['NextBlock'] # maybe for adding blocks to split dialogue later
        }
        choices = tree['ChoiceDataList'] #always present
        if choices:
            o['choices'] = list()
            for c in choices:
                o['choices'].append({
                    'jpText': c['Text'],
                    'enText': "",
                    'nextBlock': c['NextBlock']
                })

        textColor = tree['ColorTextInfoList'] #always present
        if textColor:
            o['coloredText'] = list()
            for c in textColor:
                o['coloredText'].append({
                    'jpText': c['Text'],
                    'enText': ""
                })

        return o if o['jpText'] else None

def transferExisting(storyId, textData):
    if OVERWRITE_DST: return
    group, id, idx = storyId
    existing = None
    search = Path(EXPORT_DIR).joinpath(group, id).glob(f"{idx} *")
    for file in search:
        if file.is_file():
            existing = common.TranslationFile(file)
            break

    if existing:
        for block in existing.getTextBlocks():
            if block['blockIdx'] == textData['blockIdx']:
                textData['enText'] = block['enText']
                textData['enName'] = block['enName']
                if 'choices' in block:
                    for idx, choice in enumerate(textData['choices']):
                        choice['enText'] = block['choices'][idx]['enText']
                if 'coloredText' in block:
                    for idx, cText in enumerate(textData['coloredText']):
                        cText['enText'] = block['coloredText'][idx]['enText']
    return



def exportData(data, filepath: str):
    if OVERWRITE_DST == True or not os.path.exists(filepath):
        export = json.dumps(data, indent=4, ensure_ascii=False)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf8") as f:
            f.write(export)


def parseStoryId(path) -> tuple:
    if EXTRACT_TYPE == "story":
        storyId = path[-9:]
        return  storyId[:2], storyId[2:6], storyId[6:9]
    elif EXTRACT_TYPE == "home":
        # storyId = path[-16:]
        # return storyId[:5], storyId[6:8], storyId[9:13], storyId[13:]
        storyId = path[-10:]
        return storyId[:2], storyId[3:7], storyId[7:]
        


def exportAsset(bundle: str, path: str):
    group, id, idx = parseStoryId(path)
    exportDir =  Path(EXPORT_DIR).joinpath(group, id)

    # check existing files first
    if not OVERWRITE_DST:
        search = exportDir.glob(f"{idx} *.json")
        for file in search:
            if file.exists():
                print(f"Skipping existing: {file.name}")
                return

    importPath = os.path.join(GAME_ASSET_ROOT, bundle[0:2], bundle)
    data = extractAsset(importPath, (group, id, idx))

    #remove stray control chars
    title = "".join(c for c in data['title'] if ord(c) > 31)
    idxString = f"{idx} ({title})"

    exportPath = f"{os.path.join(exportDir, idxString)}.json"
    exportData(data, exportPath)


def main():
    print(f"Extracting group {EXTRACT_GROUP}, id {EXTRACT_ID} (limit {EXTRACT_LIMIT or 'ALL'}, overwrite: {OVERWRITE_DST})\nfrom {GAME_ASSET_ROOT} to {EXPORT_DIR}")
    q = queryDB()
    for bundle, path in q:
        exportAsset(bundle, path)

main()
