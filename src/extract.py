import os
from pathlib import Path, PurePath
import UnityPy
import sqlite3
import csv
from Levenshtein import ratio as similarity
import common
from common import GAME_META_FILE, GAME_ASSET_ROOT

# Globals & Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("[-g <group>] [-id <id>] [-l <limit files to process>] [-src <game asset root>] [-dst <extract to path>] [-O(verwrite existing)] [-upd]",
                 "Any order. Defaults to extracting all text, skip existing",
                 "-upd Re-extracts existing files. Implies -O, ignores -dst")

EXTRACT_TYPE = args.getArg("-t", "story").lower()
common.checkTypeValid(EXTRACT_TYPE)
EXTRACT_GROUP = args.getArg("-g", None)
EXTRACT_ID = args.getArg("-id", None)
EXTRACT_IDX = args.getArg("-idx", None)
EXTRACT_LIMIT = args.getArg("-l", -1)
GAME_ASSET_ROOT = args.getArg("-src", GAME_ASSET_ROOT)
EXPORT_DIR = args.getArg("-dst", PurePath("translations").joinpath(EXTRACT_TYPE))
OVERWRITE_DST = args.getArg("-O", False)
UPDATE = args.getArg("-upd", False)


def queryDB(db = None, storyId = None):
    externalDb = bool(db)
    if storyId:
        group, id, idx = common.parseStoryId(EXTRACT_TYPE, storyId, False)
    else:
        group = EXTRACT_GROUP or "__"
        id = EXTRACT_ID or "____"
        idx = EXTRACT_IDX or "___"
    if EXTRACT_TYPE == "story":
        pattern = f"{EXTRACT_TYPE}/data/{group}/{id}/{EXTRACT_TYPE}timeline%{idx}"
    elif EXTRACT_TYPE == "home":
        pattern = f"{EXTRACT_TYPE}/data/00000/{group}/{EXTRACT_TYPE}timeline_00000_{group}_{id}{idx}%"
    elif EXTRACT_TYPE == "race":
        pattern = f"race/storyrace/text/storyrace_{group}{id}{idx}%"
    elif EXTRACT_TYPE == "lyrics":
        if EXTRACT_ID and not EXTRACT_IDX: idx = EXTRACT_ID
        pattern = f"live/musicscores/m{idx}/m{idx}_lyrics"
    elif EXTRACT_TYPE == "preview":
        if EXTRACT_ID and not EXTRACT_IDX: idx = EXTRACT_ID
        pattern = f"outgame/announceevent/loguiasset/ast_announce_event_log_ui_asset_0{idx}"
    if not externalDb:
        db = sqlite3.connect(GAME_META_FILE)
    cur = db.execute(
        f"select h, n from a where n like '{pattern}' limit {EXTRACT_LIMIT};")
    results = cur.fetchall()
    if not externalDb: 
        db.close()
    return results

class CheckPatched():
    def __init__(self, asset):
        self.n = 0
        self.asset = asset
    
    def __call__(self, textData):
        if len(textData['jpText']) < 3: return False
        if not common.isJapanese(textData['jpText']): self.n += 1
        if (self.n > 5):
            print(f"Asset {self.asset} looks patched, skipping...")
            return True
        else:
            return False

def extractAsset(path, storyId, tlFile = None):
    env = UnityPy.load(path)
    index = next(iter(env.container.values())).get_obj()

    if index.serialized_type.nodes:
        tree = index.read_typetree()
        export = {
            'version': 4,
            'bundle': env.file.name,
            'type': EXTRACT_TYPE,
            'storyId': "",
            'title' : "",
            'text': list()
        }
        isPatched = CheckPatched(env.file.name)
        transferExisting = DataTransfer(tlFile)

        if EXTRACT_TYPE == "race":
            export['storyId'] = tree['m_Name'][-9:]

            for block in tree['textData']:
                textData = extractText("race", block)
                if isPatched(textData): return
                transferExisting(storyId, textData)
                export['text'].append(textData)
        elif EXTRACT_TYPE == "lyrics":
            # data = index.read()
            # export['storyId'] = data.name[1:5]
            # export['text'] = extractText("lyrics", data.text)
            export['storyId'] = tree['m_Name'][1:5]

            r = csv.reader(tree['m_Script'].splitlines(), skipinitialspace=True)
            header = True
            # intern-kun can't help goof up even csv
            for row in r:
                if header: header = False; continue
                textData = extractText("lyrics", row)
                if isPatched(textData): return
                transferExisting(storyId, textData)
                export['text'].append(textData)
                
        elif EXTRACT_TYPE == "preview":
            export['storyId'] = tree['m_Name'][-4:]
            for block in tree['DataArray']:
                textData = extractText("preview", block)
                if isPatched(textData): return
                transferExisting(storyId, textData)
                export['text'].append(textData)
        else:
            export['storyId'] = "".join(storyId) if EXTRACT_TYPE == "home" else  tree['StoryId']
            export['title'] = tree['Title']

            for block in tree['BlockList']:
                for clip in block['TextTrack']['ClipList']:
                    pathId = clip['m_PathID']
                    textData = extractText(EXTRACT_TYPE, index.assets_file.files[pathId])
                    if not textData:
                        continue
                    if isPatched(textData): return
                    textData['pathId'] = pathId  # important for re-importing
                    textData['blockIdx'] = block['BlockIndex'] # to help translators look for specific routes
                    transferExisting(storyId, textData)
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
        time, text, *_ = obj
        o = {
            'jpText': text,
            'enText': "",
            'time': time
        }
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
    
class DataTransfer():
    def __init__(self, file: common.TranslationFile = None):
        self.file = file
        self.offset = 0
        self.simRatio = 0.9 if UPDATE and EXTRACT_TYPE != "lyrics" else 0.99
        self.printed = False

    def filePrint(self, text):
        if not self.printed:
            print(f"\nIn {self.file.name}:")
            self.printed = True
        print(text)

    def __call__(self, storyId, textData):
        # Existing files are skipped before reaching here so there's no point in checking when we know the result already.
        # Only continue when forced to.
        if not OVERWRITE_DST: return
        group, id, idx = storyId

        if self.file is None:
            file = common.findExisting(PurePath(EXPORT_DIR).joinpath(group, id), f"{idx}*.json")
            if file is None: # Check we actually found a file above
                return
            else: 
                self.file = common.TranslationFile(file)

        textSearch = False
        targetBlock = None
        textBlocks = self.file.textBlocks
        if 'blockIdx' in textData:
            txtIdx = max(textData["blockIdx"] - 1 - self.offset, 0)
            if txtIdx < len(textBlocks):
                targetBlock = textBlocks[txtIdx]
                if similarity(targetBlock['jpText'], textData['jpText']) < self.simRatio:
                    self.filePrint(f"jpText does not match at bIdx {textData['blockIdx']}")
                    targetBlock = None
                    textSearch = True
            else: textSearch = True
        else: 
            self.filePrint(f"No block idx at {txtIdx}")
            txtIdx = int(txtIdx)
            textSearch = True

        if textSearch:
            self.filePrint("Searching by text")
            for i, block in enumerate(textBlocks):
                if similarity(block['jpText'], textData['jpText']) > self.simRatio:
                    self.filePrint(f"Found text at block {i}")
                    self.offset = txtIdx - i
                    targetBlock = block
                    break
            if not targetBlock:
                self.filePrint("Text not found")

        if targetBlock:
            textData['enText'] = targetBlock['enText']
            if 'enName' in targetBlock:
                textData['enName'] = targetBlock['enName']
            if 'choices' in targetBlock:
                for txtIdx, choice in enumerate(textData['choices']):
                    try:
                        choice['enText'] = targetBlock['choices'][txtIdx]['enText']
                    except IndexError:
                        self.filePrint(f"New choice at bIdx {targetBlock['blockIdx']}.")
                    except KeyError:
                        self.filePrint(f"Choice mismatch when attempting data transfer at {txtIdx}")
            if 'coloredText' in targetBlock:
                for txtIdx, cText in enumerate(textData['coloredText']):
                    cText['enText'] = targetBlock['coloredText'][txtIdx]['enText']
            if 'skip' in targetBlock:
                textData['skip'] = targetBlock['skip']


def exportData(data, filepath: str):
    if OVERWRITE_DST == True or not os.path.exists(filepath):
        common.writeJsonFile(filepath, data)
        
def exportAsset(bundle: str, path: str, db = None):
    if bundle is None:
        tlFile = common.TranslationFile(path)
        storyId = tlFile.getStoryId()
        bundle, _ = queryDB(db, storyId)[0]
    else: # make sure tlFile is set for the call later
        tlFile = None
    group, id, idx = common.parseStoryId(EXTRACT_TYPE, storyId if UPDATE else path, not UPDATE)
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
    if not os.path.exists(importPath):
        print(f"AssetBundle {bundle} does not exist in your game data, skipping...")
        return
    try:
        data = extractAsset(importPath, (group, id, idx), tlFile)
        if not data: return
    except:
        print(f"Failed extracting bundle {bundle}, g {group}, id {id} idx {idx} to {exportDir}")
        raise

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
    if UPDATE:
        global EXTRACT_TYPE
        global OVERWRITE_DST
        global EXPORT_DIR
        OVERWRITE_DST = True
        print(f"Updating exports, this could take a while...")
        # check if a type was specifically given and use that if so, otherwise use all
        db = sqlite3.connect(GAME_META_FILE)
        try:
            for type in [EXTRACT_TYPE] if args.getArg("-t") else common.TARGET_TYPES:
                EXTRACT_TYPE = type
                EXPORT_DIR = PurePath("translations").joinpath(EXTRACT_TYPE)
                files = common.searchFiles(type, EXTRACT_GROUP, EXTRACT_ID, EXTRACT_IDX)
                print(f"Found {len(files)} files for {type}.")
                for i, file in enumerate(files):
                    try:
                        exportAsset(None, file, db)
                    except:
                        print(f"Failed in file {i} of {type}: {file}")
                        raise #todo consider continuing
        finally:
            db.close()
    else:
        print(f"Extracting group {EXTRACT_GROUP}, id {EXTRACT_ID}, idx {EXTRACT_IDX} (limit {EXTRACT_LIMIT or 'ALL'}, overwrite: {OVERWRITE_DST})\nfrom {GAME_ASSET_ROOT} to {EXPORT_DIR}")
        q = queryDB()
        print(f"Found {len(q)} files.")
        for bundle, path in q:
            exportAsset(bundle, path)
    print("Processing finished successfully.")

if __name__ == '__main__':
    main()
