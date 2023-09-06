import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# from sys import stdout
from functools import reduce
from pathlib import Path
from time import time as now

import common.constants as const
import filecopy as backup
from common import patch, logger
from common.types import GameBundle, TranslationFile


class ConfigError(Exception):
    pass


class PatchError(Exception):
    pass


class TranslationFileError(PatchError):
    pass


class AlreadyPatchedError(PatchError):
    def __init__(self, bundle: str):
        super().__init__(f"{bundle} is already patched")
        self.bundle = bundle


class NoAssetError(PatchError):
    def __init__(self, bundle: str):
        super().__init__(f"{bundle} does not exist in your game data")
        self.bundle = bundle


class PatchManager:
    totalFilesProcessed = 0
    totalFilesImported = 0

    def __init__(self, args: argparse.Namespace) -> None:
        self.config(args)

    def config(self, args=None, **kwargs):
        if args:
            self.args = args
        else:
            for k, v in kwargs.items():
                if hasattr(self.args, k):
                    setattr(self.args, k, v)
                else:
                    raise ConfigError(f"Invalid config arg: {k}: {v}")
        if self.args.overwrite:
            self.args.dst = const.GAME_ASSET_ROOT
            self.fcArgs = backup.parseArgs([])
            self.fcArgs.restore_missing = False
            self.fcArgs.full_path = False

    def start(self):
        startTime = now()
        print(
            f"Importing group {self.args.group or 'all'}, id {self.args.id or 'all'}, idx {self.args.idx or 'all'} " 
            f"from translations/{self.args.type} to {self.args.dst}"
        )
        files = patch.searchFiles(
            self.args.type, self.args.group, self.args.id, self.args.idx, changed=self.args.changed
        )
        nFiles = len(files)
        self.totalFilesProcessed += nFiles
        nSuccess = nSkipped = nErrors = 0
        print(f"Found {nFiles} files.")

        # Not sure if threads are useful but multi-process takes too long upfront for low counts.
        with ProcessPoolExecutor() if nFiles > 25 else ThreadPoolExecutor() as pool:
            # map seems to be a tiny bit faster maybe?
            # chunksize seems to affect nothing, haven't tested >100 files tho
            for result in pool.map(self.patchFile, files):
                if result is None:
                    nErrors += 1
                elif result is False:
                    nSkipped += 1
                else:
                    nSuccess += 1
        self.totalFilesImported += nFiles
        print(
            f"Imported {nSuccess} files in {deltaTime(startTime)} seconds. "
            f"Skipped: {nSkipped}, Errors: {nErrors} (Check import.log for details)"
        )

    def patchFile(self, file: str) -> bool:
        isModified = False
        try:
            isModified, reason = self.patch(file)
            if isModified:
                print(f"Imported {file} ({reason})")
            else:
                logger.info(f"Skipped {file} ({reason})")
        except Exception:
            logger.error(f"Error importing {file}", exc_info=True)
            # raise PatchError(f"UnityPy error: {repr(e)}, skipping {tlFile.bundle}.")
            isModified = None
        return isModified

    def loadTranslationFile(self, path):
        try:
            return TranslationFile(path, readOnly=True)
        except Exception:
            raise TranslationFileError(f"Couldn't load translation data from {path}.")

    def loadBundle(self, tlFile: TranslationFile):
        bundle = GameBundle.fromName(tlFile.bundle, load=False)
        if not bundle.exists:
            raise NoAssetError(tlFile.bundle)
        if self.args.update:
            # Find the right output file as it may not be in game dir!
            b = GameBundle(GameBundle.createPath(self.args.dst, tlFile.bundle), load=False)
            if b.isPatched:
                tlModTime = tlFile.data.get("modified")
                if tlModTime and b.patchedTime != tlModTime:
                    bundle.importState = "translations modified"
                else:
                    raise AlreadyPatchedError(tlFile.bundle)
            else:
                bundle.importState = "new"
        else:
            bundle.importState = "overwrite"
        bundle.load()
        bundle.linkedTlFile = tlFile
        return bundle

    def patch(self, path: str):
        """Swaps game assets with translation file data, returns modified state."""
        tlFile = self.loadTranslationFile(path)
        if self.args.skip_mtl and not tlFile.data.get("humanTl"):
            return False, "Skip MTL requested"
        if self.args.use_tlg and isUsingTLG() and tlFile.data.get("tlg"):
            convertTlFile(tlFile)
            logger.info(f"Writing TLG version: {tlFile.name}")
            return False, "Prefer TLG version requested"
        try:
            bundle = self.loadBundle(tlFile)
        except PatchError as reason:
            return False, reason

        if tlFile.type in ("story", "home"):
            patcher = StoryPatcher(self, bundle)
        elif tlFile.type == "race":
            patcher = RacePatcher(self, bundle)
        elif tlFile.type == "preview":
            patcher = PreviewPatcher(self, bundle)
        elif tlFile.type == "lyrics":
            patcher = LyricsPatcher(self, bundle)

        patcher.patch()
        if patcher.isModified:
            if self.args.overwrite and not bundle.isPatched:
                backup.copy(bundle, self.fcArgs)
            bundle.markPatched(tlFile)
            bundle.save(dstFolder=Path(self.args.dst))

        return patcher.isModified, bundle.importState


class StoryPatcher:
    def __init__(self, manager: PatchManager, bundle: GameBundle) -> None:
        self.manager = manager
        self.skipped = 0
        self.totalBlocks = len(bundle.linkedTlFile.textBlocks)
        self.bundle = bundle
        self.assetData = bundle.rootAsset.read_typetree()

    def _adjustCLipLength(self, assetData:dict, textBlock:dict, blockIdx:int):
        # Calculate length
        # index length = sum(blocklenghts)
        # blocklength = cliplength + startframe + 1
        # cliplength = max(0, voicelength OR (text-length * cps / fps)) + waitframe
        # waitframe: usually 12 if voiced, 45 otherwise BUT random exceptions occur
        origClipLen = textBlock.get("origClipLength")
        enText = textBlock.get("enText")
        if origClipLen is None or not enText:
            return
        newTxtLen = len(enText) / self.manager.args.cps * self.manager.args.fps
        newClipLen = textBlock.get("newClipLength")  # manual length override
        if newClipLen:
            # todo: this shouldn't happen or be cared about, really (error is fine)
            try:
                newClipLen = int(newClipLen)
            except ValueError:
                newClipLen = None
                logger.warning(f"{blockIdx}: Invalid clip length defined, falling back to calculated value.")
            logger.debug("Using manually defined clip length")
        if newClipLen is None:  # support error above
            newClipLen = int(assetData["WaitFrame"] + max(newTxtLen, assetData["VoiceLength"]))

        # todo: should revert to original on patched files
        if newClipLen <= origClipLen:
            logger.debug(f"{blockIdx}: New clip length <= original. Skipping.")
            return
        assetData["ClipLength"] = newClipLen
        newBlockLen = newClipLen + assetData["StartFrame"] + 1
        self.assetData["BlockList"][blockIdx]["BlockLength"] = newBlockLen
        logger.debug(f"{blockIdx}: Adjusted TextClip length: {origClipLen} -> {newClipLen}")

        if "animData" not in textBlock:
            logger.debug(f"{blockIdx}: Text length adjusted but no anim data found")
            return
        for animGroup in textBlock["animData"]:
            newAnimLen = animGroup["origLen"] + newClipLen - origClipLen
            if newAnimLen <= animGroup["origLen"]:
                logger.debug(f"{blockIdx}: New anim data <= original. Skipping.")
                return
            animAsset = self.bundle.assets[animGroup["pathId"]]
            if animAsset is None:
                logger.debug(f"{blockIdx}: Can't find animation asset ({animGroup['pathId']})")
                return
            animData = animAsset.read_typetree()
            animData["ClipLength"] = newAnimLen
            animAsset.save_typetree(animData)
            logger.debug(f"{blockIdx}: Adjusted AnimClip length: {animGroup['origLen']} -> {newAnimLen}")

    def patch(self):
        logger.debug(f"Patching {self.bundle.bundleName}")
        for textBlock in self.bundle.linkedTlFile.textBlocks:
            blockIdx = textBlock["blockIdx"]
            asset = self.bundle.assets.get(textBlock["pathId"])
            if asset is None:
                logger.warning(f"{blockIdx}: Can't find path id, skipping.")
                # ?: is there a reason we didn't skip here? untested!
                self.skipped += 1
                continue
            # Not translated
            if not textBlock["enText"] and not textBlock["enName"]:
                self.skipped += 1
                continue

            assetData = asset.read_typetree()
            assetData["Text"] = textBlock["enText"] or assetData["Text"]
            assetData["Name"] = textBlock["enName"] or assetData["Name"]

            self._adjustCLipLength(assetData, textBlock, blockIdx)

            if "choices" in textBlock:
                jpChoices, enChoices = assetData["ChoiceDataList"], textBlock["choices"]
                if len(jpChoices) != len(enChoices):
                    logger.warning(f"{blockIdx}: Choice lengths do not match, skipping choice block.")
                else:
                    for idx, choice in enumerate(enChoices):
                        if enChoice := choice["enText"]:
                            jpChoices[idx]["Text"] = enChoice

            if "coloredText" in textBlock:
                jpColored, enColored = assetData["ColorTextInfoList"], textBlock["coloredText"]
                if len(jpColored) != len(enColored):
                    logger.warning(f"{blockIdx}: Colored text lengths do not match, skipping color block...")
                else:
                    for idx, text in enumerate(enColored):
                        if enText := text["enText"]:
                            jpColored[idx]["Text"] = enText
            asset.save_typetree(assetData)

        try:
            self.assetData["TypewriteCountPerSecond"] = self.manager.args.fps * 3
            self.assetData["Length"] = reduce(
                lambda x, b: x + b["BlockLength"], 
                self.assetData["BlockList"], 
                0
            )
            self.save()
        except Exception as e:
            logger.error(f"Unexpected error at {blockIdx}: {repr(e)}")

    def save(self):
        if self.isModified:
            self.bundle.rootAsset.save_typetree(self.assetData)

    @property
    def isModified(self):
        return self.skipped != self.totalBlocks


class RacePatcher(StoryPatcher):
    def patch(self):
        for i, textBlock in enumerate(self.bundle.linkedTlFile.textBlocks):
            # blockIdx = textBlock['blockIdx'] - 1  # race keys start at 1
            if textBlock["enText"]:
                self.assetData["textData"][i]["text"] = textBlock["enText"]
            else:
                self.skipped += 1
                continue
        self.save()


class PreviewPatcher(RacePatcher):
    def patch(self):
        for blockIdx, textBlock in enumerate(self.bundle.linkedTlFile.textBlocks):
            if not textBlock["enText"] and not textBlock["enName"]:
                self.skipped += 1
                continue

            if textBlock["enName"]:
                self.assetData["DataArray"][blockIdx]["Name"] = textBlock["enName"]
            if textBlock["enText"]:
                self.assetData["DataArray"][blockIdx]["Text"] = textBlock["enText"]
        self.save()


class LyricsPatcher(StoryPatcher):
    def __init__(self, manager: PatchManager, bundle: GameBundle) -> None:
        super().__init__(manager, bundle)
        self.assetData = bundle.rootAsset.read()
        self.assetText = "time,lyrics\n"

    def patch(self):
        for textBlock in self.bundle.linkedTlFile.textBlocks:
            # Format the CSV text. Their parser uses quotes, no escape chars.
            # For novelty: \t = space; \v and \f = ,; \r = \n
            text = textBlock["enText"]
            if not text:
                text = textBlock["jpText"]
                self.skipped += 1
            elif "," in text or '"' in text:
                text = '"' + text.replace('"', '""') + '"'
            self.assetText += f"{textBlock['time']},{text}\n"
        self.save()

    def save(self):
        if self.isModified:
            self.assetData.script = bytes(self.assetText, "utf8")
            self.assetData.save()


def deltaTime(startTime: float):
    delta = now() - startTime
    m, s = divmod(delta, 60)
    return f"{m:.0f}m {s:.3f}s"


def parseArgs(args=None):
    ap = patch.Args("Write Game Assets from Translation Files")
    ap.add_argument(
        "-O",
        "--overwrite",
        action="store_true",
        help="(Over)Write files straight to game directory",
    )
    ap.add_argument("-U", "--update", action="store_true", help="Skip already imported files")
    ap.add_argument(
        "-FI",
        "--full-import",
        dest="fullImport",
        action="store_true",
        help="Import all available types",
    )
    ap.add_argument(
        "-wf",
        "--write-log",
        action="store_true",
        help="Print more detailed info to file",
    )
    ap.add_argument(
        "-cps",
        default=28,
        type=int,
        help="Characters per second, for unvoiced lines (excludes choices)",
    )
    ap.add_argument(
        "-fps", default=30, type=int, help="Framerate, for calculating the right text speed"
    )
    ap.add_argument(
        "-tlg", "--use-tlg", action="store_true", help="Auto-write any TLG versions when detected"
    )
    ap.add_argument(
        "-nomtl", "--skip-mtl", action="store_true", help="Only import human translations"
    )
    return ap.parse_args(args)


def main(args: patch.Args = None):
    args = args or parseArgs(args)
    if args.write_log:
        logger.setFile("import.log")

    if args.use_tlg:
        global isUsingTLG, convertTlFile
        from common.patch import isUsingTLG
        from manage import convertTlFile
    startTime = now()
    patcher = PatchManager(args)
    try:
        patcher.start()
        if args.fullImport:
            for type in const.TARGET_TYPES[1:]:
                patcher.config(type=type)
                patcher.start()
            print(f"Updated a total of {patcher.totalFilesImported} files in {deltaTime(startTime)}")
    finally:
        logger.closeFile()


if __name__ == "__main__":
    main()
