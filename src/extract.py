import os
import sys
import UnityPy
import json
import re
import sqlite3

GAME_ROOT = os.path.realpath(os.path.join(os.environ['LOCALAPPDATA'], "../LocalLow/Cygames/umamusume/"))
EXPORT_DIR = os.path.realpath("translations/")
EXTRACT_GROUP = "__"
EXTRACT_ID = "__"

opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

if len(opts) != len(args): quit()
for idx, opt in enumerate(opts):
    if opt == "-g":
        EXTRACT_GROUP = args[idx]
    elif opt == "-id":
        EXTRACT_ID = args[idx]
    elif opt == "-src":
        GAME_ROOT = args[idx]

def quit():
    raise SystemExit(f"Usage: {sys.argv[0]} [-g <group>] [-id <id>] [-src <game appdata root>]\nDefaults to extracting all text")

# CONTAINER = None
# FILENAME = None

def queryDB():
    db = sqlite3.connect(os.path.join(GAME_ROOT, "meta"))
    cur = db.execute(f"select h from a where n like 'story/data/{EXTRACT_GROUP}/{EXTRACT_ID}/storytimeline%' limit 5;")
    results = cur.fetchall()
    db.close()
    return results

def get_meta(filePath: str) -> tuple[str, UnityPy.environment.files.ObjectReader]:
    env = UnityPy.load(filePath)
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            # storytimeline metadata (also typeof container == string !!)
            # obj.type_id == 16 does NOT work!
            if obj.serialized_type.script_type_index == 0:
                return (env.file.name, obj)

def extractFiles(obj, assetName: str) -> tuple[str, str, dict[str, list]]:
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
                o['pathId'] = pathId
                data[assetName].append(o)
        return (metadata["StoryId"], title, data)


def extractText(obj):
    if obj.serialized_type.nodes:
        tree = obj.read_typetree()
        o = {
            'jpText': tree['Text'],
            'enText': "",
            'name': tree['Name'],
            'enName': "", # todo: auto lookup
        }
        c = tree['ChoiceDataList']
        if c:
            o['choices'] = c

        return o


def exportData(data, filepath):
    if not os.path.exists(filepath):
        export = json.dumps(data, indent=4, ensure_ascii=False).encode("utf8")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(export)
            f.close()

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
