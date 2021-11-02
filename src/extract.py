import os
import sys
import UnityPy
import json
import re
import sqlite3

GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
EXPORT_DIR = os.path.realpath("translations/")
EXTRACT_GROUP = "__"
EXTRACT_ID = "____"
EXTRACT_LIMIT = -1
OVERWRITE_DST = False

opts = sys.argv[1:]
idx = 0
while idx < len(opts):
    opt = opts[idx]
    idx += 1  # get arg
    if opt == "-g":
        EXTRACT_GROUP = opts[idx]
    elif opt == "-id":
        EXTRACT_ID = opts[idx]
    elif opt == "-l":
        EXTRACT_LIMIT = opts[idx]
    elif opt == "-src":
        GAME_ROOT = opts[idx]
    elif opt == "-O":
        OVERWRITE_DST = True
        continue  # no arg
    else:
        quit()
    idx += 1  # get next opt


def quit():
    raise SystemExit(
        f"Usage: {sys.argv[0]} [-g <group>] [-id <id>] [-src <game appdata root>] [-O]\nAny order. Defaults to extracting all text")


def queryDB():
    db = sqlite3.connect(os.path.join(GAME_ROOT, "meta"))
    cur = db.execute(
        f"select h from a where n like 'story/data/{EXTRACT_GROUP}/{EXTRACT_ID}/storytimeline%' limit {EXTRACT_LIMIT};")
    results = cur.fetchall()
    db.close()
    return results


def get_meta(filePath: str) -> tuple[str, UnityPy.environment.files.ObjectReader]:
    env = UnityPy.load(filePath)
    return env.file.name, next(iter(env.container.values())).get_obj()

def extractFiles(obj, assetName: str) -> tuple[str, str, dict[str, list[dict]]]:
    if obj.serialized_type.nodes:
        data = {
            assetName: list()
        }
        metadata = obj.read_typetree()
        title = metadata['Title']
        for block in metadata['BlockList']:
            for clip in block['TextTrack']['ClipList']:
                pathId = clip['m_PathID']
                o = extractText(obj.assets_file.files[pathId])
                if not o:
                    continue
                o['pathId'] = pathId  # important for re-importing
                # to help translators look for specific routes
                o['blockIdx'] = block['BlockIndex']
                data[assetName].append(o)
        return (metadata["StoryId"], title, data)


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
        export = json.dumps(data, indent=4, ensure_ascii=False).encode("utf8")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
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
    groupString = f"{id} ({groupName})" if groupName else group
    idName = lookupId(id)
    idString = f"{id} ({idName})" if idName else id
    idxString = f"{idx} ({title})"
    path = f"{os.path.join(EXPORT_DIR, groupString, idString, idxString)}.json"

    exportData(data, path)


def main():
    q = queryDB()
    for file, in q:
        exportAsset(os.path.join(GAME_ROOT, "dat", file[0:2], file))

main()
