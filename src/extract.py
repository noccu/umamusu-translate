import os
from pathlib import Path
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

EXTRACT_GROUP = args.getArg("-g", "__")
EXTRACT_ID = args.getArg("-id", "____")
EXTRACT_LIMIT = args.getArg("-l", -1)
GAME_ASSET_ROOT = args.getArg("-src", GAME_ASSET_ROOT)
EXPORT_DIR = args.getArg("-dst", "translations/")
OVERWRITE_DST = args.getArg("-O", False)

def queryDB():
    db = sqlite3.connect(GAME_META_FILE)
    cur = db.execute(
        f"select h,n from a where n like 'story/data/{EXTRACT_GROUP}/{EXTRACT_ID}/storytimeline%' limit {EXTRACT_LIMIT};")
    results = cur.fetchall()
    db.close()
    return results


def extractAssets(path):
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
                transferExisting(tree['StoryId'], textData)
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
    group, id, idx = parseStoryId(storyId)
    existing = None
    search = Path(EXPORT_DIR).joinpath(group, id).glob(f"{idx}*")
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


def parseStoryId(storyId):
    if len(storyId) == 9:
       return storyId[:2], storyId[2:6], storyId[6:9]
    else:
        raise ValueError("Invalid Story ID format.")


def exportAssets(bundle: str, path: str):
    # check existing files first
    if not OVERWRITE_DST:
        group, id, idx = parseStoryId(path[-9:])
        search = Path(EXPORT_DIR).joinpath(group, id).glob(f"{idx} *.json")
        for file in search:
            if file.exists():
                print(f"Skipping existing: {file.name}")
                return

    importPath = os.path.join(GAME_ASSET_ROOT, bundle[0:2], bundle)
    data = extractAssets(importPath)

    group, id, idx = parseStoryId(data['storyId'])

    #remove stray control chars
    title = "".join(c for c in data['title'] if ord(c) > 31)
    idxString = f"{idx} ({title})"

    exportPath = f"{os.path.join(EXPORT_DIR, group, id, idxString)}.json"
    exportData(data, exportPath)


def main():
    print(f"Extracting group {EXTRACT_GROUP}, id {EXTRACT_ID} (limit {EXTRACT_LIMIT or 'ALL'}, overwrite: {OVERWRITE_DST})\nfrom {GAME_ASSET_ROOT} to {EXPORT_DIR}")
    q = queryDB()
    for bundle, path in q:
        exportAssets(bundle, path)

main()
