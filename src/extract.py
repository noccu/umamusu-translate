import os
import UnityPy
import json
import re
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
EXPORT_DIR = args.getArg("-dst", os.path.realpath("translations/"))
OVERWRITE_DST = args.getArg("-O", False)

def queryDB():
    db = sqlite3.connect(GAME_META_FILE)
    cur = db.execute(
        f"select h from a where n like 'story/data/{EXTRACT_GROUP}/{EXTRACT_ID}/storytimeline%' limit {EXTRACT_LIMIT};")
    results = cur.fetchall()
    db.close()
    return results


def get_meta(filePath: str) -> tuple[str, UnityPy.environment.files.ObjectReader]:
    env = UnityPy.load(filePath)
    return env.file.name, next(iter(env.container.values())).get_obj()

def extractFiles(obj, bundleName: str):
    if obj.serialized_type.nodes:
        export = {
            bundleName: list()
        }
        tree = obj.read_typetree()
        title = tree['Title']
        for block in tree['BlockList']:
            for clip in block['TextTrack']['ClipList']:
                pathId = clip['m_PathID']
                o = extractText(obj.assets_file.files[pathId])
                if not o:
                    continue
                o['pathId'] = pathId  # important for re-importing           
                o['blockIdx'] = block['BlockIndex'] # to help translators look for specific routes
                export[bundleName].append(o)
        return (tree["StoryId"], title, export)


def extractText(obj):
    if obj.serialized_type.nodes:
        tree = obj.read_typetree()
        o = {
            'jpText': tree['Text'],
            'enText': "",
            'name': tree['Name'],
            'enName': "",  # todo: auto lookup
        }
        choices = tree['ChoiceDataList']
        if choices:
            o['choices'] = []
            for c in choices:
                o['choices'].append({
                    'jpText': c['Text'],
                    'enText': "",
                    'nextBlockIdx': c['NextBlock']
                })

        # return if text isn't empty
        return o if o['jpText'] else None


def exportData(data, filepath):
    if OVERWRITE_DST == True or not os.path.exists(filepath):
        export = json.dumps(data, indent=4, ensure_ascii=False)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf8") as f:
            f.write(export)


def lookupId(id):
    # todo: implement
    return False
def lookupGroup(id):
    # todo: implement
    return False


def exportAsset(file):
    assetName, obj = get_meta(file)
    storyId, title, data = extractFiles(obj, assetName)
    m = re.match(r"(\d\d)(\d{4,4})(\d+)", storyId)
    if m:
        group, id, idx = m.groups()
    else:
        print(f"ID error in {assetName}, matching {storyId}")
        return

    groupName = lookupGroup(id)
    groupString = f"{group} ({groupName})" if groupName else group
    idName = lookupId(id)
    idString = f"{id} ({idName})" if idName else id
    idxString = f"{idx} ({title})"
    path = f"{os.path.join(EXPORT_DIR, groupString, idString, idxString)}.json"

    exportData(data, path)


def main():
    print(f"Extracting group {EXTRACT_GROUP}, id {EXTRACT_ID} (limit {EXTRACT_LIMIT or 'ALL'}, overwrite: {OVERWRITE_DST})\nfrom {GAME_ASSET_ROOT} to {EXPORT_DIR}")
    q = queryDB()
    for file, in q:
        exportAsset(os.path.join(GAME_ASSET_ROOT, file[0:2], file))

main()
