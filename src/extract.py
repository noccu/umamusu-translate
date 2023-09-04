import csv
import sqlite3
from pathlib import Path, PurePath
from typing import Optional, Union

from Levenshtein import ratio as similarity

from common import patch
from common.constants import GAME_ASSET_ROOT, GAME_META_FILE, TARGET_TYPES
from common.utils import sanitizeFilename
from common.types import StoryId, GameBundle, TranslationFile


def queryDB(db=None, storyId: StoryId = None):
    storyId = StoryId.queryfy(storyId)

    if storyId.type == "story":
        pattern = (
            f"{storyId.type}/data/{storyId.group}/{storyId.id}/{storyId.type}timeline%{storyId.idx}"
        )
    elif storyId.type == "home":
        pattern = f"{storyId.type}/data/{storyId.set}/{storyId.group}/{storyId.type}timeline_{storyId.set}_{storyId.group}_{storyId.id}{storyId.idx}%"
    elif storyId.type == "race":
        pattern = (
            f"{storyId.type}/storyrace/text/storyrace_{storyId.group}{storyId.id}{storyId.idx}%"
        )
    elif storyId.type == "lyrics":
        pattern = f"live/musicscores/m{storyId.id}/m{storyId.id}_lyrics"
    elif storyId.type == "preview":
        pattern = f"outgame/announceevent/loguiasset/ast_announce_event_log_ui_asset_0{storyId.id}"

    externalDb = bool(db)
    if not externalDb:
        db = sqlite3.connect(GAME_META_FILE)
    cur = db.execute(f"SELECT h, n FROM a WHERE n LIKE '{pattern}';")
    results = cur.fetchall()
    if not externalDb:
        db.close()

    return results


def extractAsset(asset: GameBundle, storyId: StoryId, tlFile=None) -> Union[None, TranslationFile]:
    asset.load()

    if not asset.rootAsset.serialized_type.nodes:
        return

    tree = asset.rootAsset.read_typetree()
    export = {
        "bundle": asset.bundleName,
        "type": args.type,
        "storyId": "",
        "title": "",
        "text": list(),
    }
    transferExisting = DataTransfer(tlFile, export)

    if args.type == "race":
        export["storyId"] = tree["m_Name"][-9:]

        for block in tree["textData"]:
            textData = extractText("race", block)
            transferExisting(storyId, textData)
            export["text"].append(textData)
    elif args.type == "lyrics":
        # data = index.read()
        # export['storyId'] = data.name[1:5]
        # export['text'] = extractText("lyrics", data.text)
        export["storyId"] = tree["m_Name"][1:5]

        r = csv.reader(tree["m_Script"].splitlines(), skipinitialspace=True)
        header = True
        # intern-kun can't help goof up even csv
        for row in r:
            if header:
                header = False
                continue
            textData = extractText("lyrics", row)
            transferExisting(storyId, textData)
            export["text"].append(textData)
    elif args.type == "preview":
        export["storyId"] = tree["m_Name"][-4:]
        for block in tree["DataArray"]:
            textData = extractText("preview", block)
            transferExisting(storyId, textData)
            export["text"].append(textData)
    else:
        export["storyId"] = str(storyId) if args.type == "home" else tree["StoryId"]
        export["title"] = tree["Title"]

        for block in tree["BlockList"]:
            for clip in block["TextTrack"]["ClipList"]:
                pathId = clip["m_PathID"]
                textData = extractText(args.type, asset.assets[pathId])
                if not textData:
                    continue

                if "origClipLength" in textData:
                    # if args.verbose: print(f"Attempting anim data export at BlockIndex {block['BlockIndex']}")
                    clipsToUpdate = list()
                    for trackGroup in block["CharacterTrackList"]:
                        for key in trackGroup.keys():
                            if key.endswith("MotionTrackData") and trackGroup[key]["ClipList"]:
                                clipsToUpdate.append(trackGroup[key]["ClipList"][-1]["m_PathID"])
                    if clipsToUpdate:
                        textData["animData"] = list()
                        for clipPathId in clipsToUpdate:
                            animAsset = asset.assets[clipPathId]
                            if animAsset:
                                animData = animAsset.read_typetree()
                                animGroupData = dict()
                                animGroupData["origLen"] = animData["ClipLength"]
                                animGroupData["pathId"] = clipPathId
                                textData["animData"].append(animGroupData)
                            elif args.verbose:
                                print(
                                    f"Couldn't find anim asset ({clipPathId}) at BlockIndex {block['BlockIndex']}"
                                )
                    elif args.verbose:
                        print(f"Anim clip list empty at BlockIndex {block['BlockIndex']}")

                textData["pathId"] = pathId  # important for re-importing
                textData["blockIdx"] = block[
                    "BlockIndex"
                ]  # to help translators look for specific routes
                transferExisting(storyId, textData)
                export["text"].append(textData)

    if not export["text"]:
        return  # skip empty text assets
    export = TranslationFile.fromData(export)
    if transferExisting.file:
        export.snapshot(copyFrom=transferExisting.file)
    return export


def extractText(assetType, obj):
    if assetType == "race":
        # obj is already read
        o = {"jpText": obj["text"], "enText": "", "blockIdx": obj["key"]}
    elif assetType == "lyrics":
        time, text, *_ = obj
        o = {"jpText": text, "enText": "", "time": time}
        return o
    elif assetType == "preview":
        o = {
            "jpName": obj["Name"],
            "enName": "",
            "jpText": obj["Text"],
            "enText": "",
        }
    elif obj.serialized_type.nodes:
        tree = obj.read_typetree()
        o = {
            "jpName": tree["Name"],
            "enName": "",  # todo: auto lookup
            "jpText": tree["Text"],
            "enText": "",
            "nextBlock": tree["NextBlock"],  # maybe for adding blocks to split dialogue later
        }
        # home has no auto mode so adjustments aren't needed
        if assetType == "story":
            o["origClipLength"] = tree["ClipLength"]
            o["voiceIdx"] = tree["CueId"]
        elif assetType == "home":
            o["voiceIdx"] = tree["CueId"]
        choices = tree["ChoiceDataList"]  # always present
        if choices:
            o["choices"] = list()
            for c in choices:
                o["choices"].append(
                    {"jpText": c["Text"], "enText": "", "nextBlock": c["NextBlock"]}
                )

        textColor = tree["ColorTextInfoList"]  # always present
        if textColor:
            o["coloredText"] = list()
            for c in textColor:
                o["coloredText"].append({"jpText": c["Text"], "enText": ""})
    return o if o["jpText"] else None


class DataTransfer:
    def __init__(self, file: TranslationFile = None, newData: dict = None):
        self.file = file
        self.offset = 0
        self.simRatio = 0.9 if args.update and args.type != "lyrics" else 0.99
        self._printedName = False
        if (newData and file) and (x := file.data.get("humanTl")):
            newData["humanTl"] = x

    def print(self, text):
        if not self._printedName:
            print(f"\nIn {self.file.name}:")
            self._printedName = True
        print(f"\t{text}")

    def __call__(self, storyId: StoryId, textData):
        # Existing files are skipped before reaching here
        # so there's no point in checking when we know the result already.
        # Only continue when forced to.
        if not args.overwrite or self.file == 0:
            return

        if self.file is None:
            file = next(
                (Path(args.dst).joinpath(storyId.asPath())).glob(f"{storyId.idx}*.json"),
                None,
            )
            if file is None:  # Check we actually found a file above
                self.file = 0
                return

            self.file = TranslationFile(file)

        textSearch = True
        targetBlock = None
        textBlocks = self.file.textBlocks
        txtIdx = 0
        if "blockIdx" in textData:
            txtIdx = max(textData["blockIdx"] - 1 - self.offset, 0)
            if txtIdx < len(textBlocks):
                targetBlock = textBlocks[txtIdx]
                if (
                    not args.upgrade
                    and similarity(targetBlock["jpText"], textData["jpText"]) < self.simRatio
                ):
                    targetBlock = None
                else:
                    textSearch = False

        if textSearch:
            if args.verbose:
                self.print("Searching by text")
            for i, block in enumerate(textBlocks):
                if similarity(block["jpText"], textData["jpText"]) > self.simRatio:
                    if args.verbose:
                        self.print(f"Found text at block {i}")
                    self.offset = txtIdx - i
                    targetBlock = block
                    break
            if not targetBlock:
                self.print(
                    f"At bIdx/time {textData.get('blockIdx', textData.get('time', 'no_idx'))}: jpText not found in file."
                )

        if targetBlock:
            if args.upgrade:
                textData["jpText"] = targetBlock["jpText"]
            textData["enText"] = targetBlock["enText"]
            if "enName" in targetBlock:
                if args.upgrade:
                    textData["jpName"] = targetBlock["jpName"]
                textData["enName"] = targetBlock["enName"]
            if "choices" in targetBlock and (choices := textData.get("choices")):
                for txtIdx, choice in enumerate(choices):
                    try:
                        if args.upgrade:
                            choice["jpText"] = targetBlock["choices"][txtIdx]["jpText"]
                        choice["enText"] = targetBlock["choices"][txtIdx]["enText"]
                    except IndexError:
                        self.print(f"New choice at bIdx {targetBlock['blockIdx']}.")
                    except KeyError:
                        self.print(f"Choice mismatch when attempting data transfer at {txtIdx}")
            if "coloredText" in targetBlock and (coloredText := textData.get("coloredText")):
                for txtIdx, cText in enumerate(coloredText):
                    if args.upgrade:
                        cText["jpText"] = targetBlock["coloredText"][txtIdx]["jpText"]
                    cText["enText"] = targetBlock["coloredText"][txtIdx]["enText"]
            if "skip" in targetBlock:
                textData["skip"] = targetBlock["skip"]
            if "newClipLength" in targetBlock:
                textData["newClipLength"] = targetBlock["newClipLength"]
            if args.upgrade and textData.get("origClipLength"):
                textData["origClipLength"] = targetBlock["origClipLength"]
                for i, group in enumerate(textData.get("animData", [])):
                    group["origLen"] = targetBlock["animData"][i]["origLen"]


def exportAsset(bundle: Optional[str], path: str, db=None):
    if args.update:  # update mode, path = tlfile, bundle = None
        assert db is not None
        tlFile = TranslationFile(path)
        if args.upgrade and tlFile.version == TranslationFile.latestVersion:
            print(f"File already on latest version, skipping: {path}")
            return

        storyId = StoryId.parse(args.type, tlFile.getStoryId())
        try:
            bundle, _ = queryDB(db, storyId)[0]  # get the newest bundle hash/name
        except IndexError:
            print(f"Error looking up {storyId}. Corrupt data or removed asset?")
            return
        if not args.upgrade and bundle == tlFile.bundle:
            if args.verbose:
                print(f"Bundle {bundle} not changed, skipping.")
            return
        print(f"{'Upgrading' if args.upgrade else 'Updating'} {bundle}")
    else:  # path = unity internal, bundle = newest from SQL lookup
        tlFile = None
        storyId = StoryId.parseFromPath(args.type, path)

    exportDir = (
        Path(args.dst)
        if args.type in ("lyrics", "preview")
        else Path(args.dst).joinpath(storyId.asPath())
    )

    # Skip if already exported and we're not overwriting
    if not args.overwrite:
        file = next(exportDir.glob(f"{storyId.getFilenameIdx()}*.json"), None)
        if file is not None:
            if args.verbose:
                print(f"Skipping existing: {file.name}")
            return

    asset = GameBundle.fromName(bundle, load=False)
    if not asset.exists:
        print(f"AssetBundle {bundle} does not exist in your game data, skipping...")
        return
    if not args.upgrade and asset.isPatched:
        if args.verbose:
            print(f"Skipping patched asset: {asset.bundleName}")
        return
    try:
        outFile = extractAsset(asset, storyId, tlFile)
        if not outFile:
            return
    except Exception:
        print(
            f"Failed extracting bundle {bundle}, g {storyId.group}, id {storyId.id} idx {storyId.idx} to {exportDir}"
        )
        raise

    # Remove invalid path chars (win)
    title = sanitizeFilename(outFile.data.get("title", ""))
    idxString = f"{storyId.idx} ({title})" if title else storyId.getFilenameIdx()
    outFile.setFile(str(exportDir / f"{idxString}.json"))
    outFile.save()


def parseArgs(args=None):
    ap = patch.Args("Extract Game Assets to Translation Files")
    ap.add_argument("-dst")
    ap.add_argument(
        "-O",
        "--overwrite",
        action="store_true",
        help="Overwrite existing Translation Files",
    )
    ap.add_argument(
        "-upd",
        "--update",
        nargs="*",
        choices=TARGET_TYPES,
        help=(
            "Re-extract existing files, optionally limited to given type.\n"
            "Implies -O, ignores -dst and -t"
        ),
    )
    ap.add_argument(
        "-upg",
        "--upgrade",
        action="store_true",
        help=(
            "Attempt tlfile version upgrade with minimal extraction.\n"
            "Can be used on patched files.\n"
            "Implies -O and -upd, uses type from -upd or -t"
        ),
    )
    args = ap.parse_args()

    if args.dst is None:
        args.dst = PurePath("translations") / args.type
    if args.upgrade or args.update is not None:
        args.overwrite = True
        # Doesn't make sense to upgrade non-existent files.
        if args.update is None:
            args.update = [args.type]
        # check if upd was given without type spec and use all types if so
        elif len(args.update) == 0:
            args.update = TARGET_TYPES
    return args


def main(_args: patch.Args = None):
    global args
    args = _args or parseArgs(_args)
    if args.update is not None:
        print(f"{'Upgrading' if args.upgrade else 'Updating'} exports...")
        db = sqlite3.connect(GAME_META_FILE)
        try:
            for type in args.update:  # set correctly by arg parsing
                args.dst = PurePath("translations") / type
                args.type = type
                files = patch.searchFiles(
                    type,
                    args.group,
                    args.id,
                    args.idx,
                    targetSet=args.set,
                    changed=args.changed,
                )
                print(f"Found {len(files)} files for {type}.")
                for i, file in enumerate(files):
                    try:
                        exportAsset(None, file, db)
                    except Exception:
                        print(f"Failed in file {i} of {type}: {file}")
                        raise  # TODO consider continuing
        finally:
            db.close()
    else:
        print(
            f"Extracting type {args.type}, set {args.set}, group {args.group}, id {args.id}, idx {args.idx} (overwrite: {args.overwrite})\n"
            f"from {GAME_ASSET_ROOT} to {args.dst}"
        )
        q = queryDB(storyId=StoryId(args.type, args.set, args.group, args.id, args.idx))
        print(f"Found {len(q)} files.")
        for bundle, path in q:
            exportAsset(bundle, path)
    print("Processing finished successfully.")


if __name__ == "__main__":
    main()
