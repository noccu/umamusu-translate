import os
from pathlib import Path, PurePath
import UnityPy
import sqlite3
import csv
import common
from common import GAME_META_FILE, GAME_ASSET_ROOT

# Globals & Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("[-g <group>] [-id <id>] [-l <limit files to process>] [-src <game asset root>] [-dst <extract to path>] [-O(verwrite existing)]",
                 "Any order. Defaults to extracting all text, skip existing")

EXTRACT_TYPE = args.getArg("-t", "story").lower()
common.checkTypeValid(EXTRACT_TYPE)
EXTRACT_GROUP = args.getArg("-g", "__")
EXTRACT_ID = args.getArg("-id", "____")
EXTRACT_IDX = args.getArg("-idx", "___")
EXTRACT_LIMIT = args.getArg("-l", -1)
GAME_ASSET_ROOT = args.getArg("-src", GAME_ASSET_ROOT)
EXPORT_DIR = args.getArg("-dst", PurePath("translations").joinpath(EXTRACT_TYPE))
OVERWRITE_DST = args.getArg("-O", False)


def queryDB():
    if EXTRACT_TYPE == "story":
        pattern = f"{EXTRACT_TYPE}/data/{EXTRACT_GROUP}/{EXTRACT_ID}/{EXTRACT_TYPE}timeline%{EXTRACT_IDX}"
    elif EXTRACT_TYPE == "home":
        pattern = f"{EXTRACT_TYPE}/data/00000/{EXTRACT_GROUP}/{EXTRACT_TYPE}timeline_00000_{EXTRACT_GROUP}_{EXTRACT_ID}%"
    elif EXTRACT_TYPE == "race":
        pattern = f"race/storyrace/text/storyrace_{EXTRACT_GROUP}{EXTRACT_ID}%"
    elif EXTRACT_TYPE == "lyrics":
        pattern = f"live/musicscores/m{EXTRACT_ID}/m{EXTRACT_ID}_lyrics"
    elif EXTRACT_TYPE == "preview":
        pattern = f"outgame/announceevent/loguiasset/ast_announce_event_log_ui_asset_0{EXTRACT_ID}"
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
            'version': 3,
            'bundle': env.file.name,
            'type': EXTRACT_TYPE,
            'storyId': "",
            'title' : "",
            'text': list()
        }

        if EXTRACT_TYPE == "race":
            export['storyId'] = tree['m_Name'][-9:]

            for block in tree['textData']:
                textData = extractText("race", block)
                export['text'].append(textData)
        elif EXTRACT_TYPE == "lyrics":
            # data = index.read()
            # export['storyId'] = data.name[1:5]
            # export['text'] = extractText("lyrics", data.text)
            export['storyId'] = tree['m_Name'][1:5]
            export['text'] = extractText("lyrics", tree['m_Script'])
        elif EXTRACT_TYPE == "preview":
            export['storyId'] = tree['m_Name'][-4:]
            for block in tree['DataArray']:
                textData = extractText("preview", block)
                export['text'].append(textData)
        else:
            export['storyId'] = tree['StoryId']
            export['title'] = tree['Title']

            fileCache = None
            for block in tree['BlockList']:
                for clip in block['TextTrack']['ClipList']:
                    pathId = clip['m_PathID']
                    textData = extractText(EXTRACT_TYPE, index.assets_file.files[pathId])
                    if not textData:
                        continue
                    textData['pathId'] = pathId  # important for re-importing
                    textData['blockIdx'] = block['BlockIndex'] # to help translators look for specific routes
                    fileCache = transferExisting(storyId, textData, fileCache)
                    export['text'].append(textData)
        return export


def extractText(assetType, obj):
    if assetType == "race":
        # obj is already read
        o = {
            'jpText': obj['text'],
            'enText': "",
            'blockIdx': obj['key']
        }
    elif assetType == "lyrics":
        o = list()
        r = csv.reader(obj.splitlines(), skipinitialspace=True)
        header = True
        # intern-kun can't help goof up even csv
        for time, text, *_ in r:
            if header: header = False; continue
            o.append({
                'jpText': text,
                'enText': "",
                'time': time
            })
        return o
    elif assetType == "preview":
        o = {
                'jpName': obj['Name'],
                'enName': "",
                'jpText': obj['Text'],
                'enText': "",
            }
    elif obj.serialized_type.nodes:
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

def transferExisting(storyId, textData, file):
    # Existing files are skipped before reaching here so there's no point in checking when we know the result already.
    # Only continue when forced to.
    if not OVERWRITE_DST: return
    group, id, idx = storyId

    if file is None:
        file = common.findExisting(PurePath(EXPORT_DIR).joinpath(group, id), f"{idx}*.json")
        if file is not None: # Check we actually found a file above
            file = common.TranslationFile(file)

    for block in file.getTextBlocks():
        if block['blockIdx'] == textData['blockIdx']:
            textData['enText'] = block['enText']
            textData['enName'] = block['enName']
            if 'choices' in block:
                for idx, choice in enumerate(textData['choices']):
                    try:
                        choice['enText'] = block['choices'][idx]['enText']
                    except IndexError:
                        print(f"New choice in {file.name} at {idx}. Requires translation.")
            if 'coloredText' in block:
                for idx, cText in enumerate(textData['coloredText']):
                    cText['enText'] = block['coloredText'][idx]['enText']
            if 'skip' in block:
                textData['skip'] = block['skip']
    return file


def exportData(data, filepath: str):
    if OVERWRITE_DST == True or not os.path.exists(filepath):
        common.writeJsonFile(filepath, data)


def parseStoryId(path) -> tuple:
    if EXTRACT_TYPE == "home":
        # storyId = path[-16:]
        # return storyId[:5], storyId[6:8], storyId[9:13], storyId[13:]
        storyId = path[-10:]
        return storyId[:2], storyId[3:7], storyId[7:]
    elif EXTRACT_TYPE == "lyrics":
        return None, path[-11:-7], path[-11:-7]
    elif EXTRACT_TYPE == "preview":
        return None, None, path[-4:]
    else:
        # story and storyrace
        storyId = path[-9:]
        return  storyId[:2], storyId[2:6], storyId[6:9]
        


def exportAsset(bundle: str, path: str):
    group, id, idx = parseStoryId(path)
    if EXTRACT_TYPE in ("lyrics", "preview"):
        exportDir = Path(EXPORT_DIR)
    else:
        exportDir =  Path(EXPORT_DIR).joinpath(group, id)

    # check existing files first
    if not OVERWRITE_DST:
        file = common.findExisting(exportDir, f"{idx}*.json")
        if file is not None:
            print(f"Skipping existing: {file.name}")
            return

    importPath = os.path.join(GAME_ASSET_ROOT, bundle[0:2], bundle)
    data = extractAsset(importPath, (group, id, idx))

    #remove invalid path chars (win)
    delList = [34,42,47,58,60,62,63,92,124]
    title = ""
    for c in data['title']:
        cp = ord(c)
        if cp > 31 and cp not in delList:
            title += c
    idxString = f"{idx} ({title})" if title else idx

    exportPath = f"{os.path.join(exportDir, idxString)}.json"
    exportData(data, exportPath)


def main():
    print(f"Extracting group {EXTRACT_GROUP}, id {EXTRACT_ID} (limit {EXTRACT_LIMIT or 'ALL'}, overwrite: {OVERWRITE_DST})\nfrom {GAME_ASSET_ROOT} to {EXPORT_DIR}")
    q = queryDB()
    print(f"Found {len(q)} files.")
    for bundle, path in q:
        exportAsset(bundle, path)
    print("Processing finished successfully.")
main()
