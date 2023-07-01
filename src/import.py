import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# from sys import stdout
from functools import reduce
from pathlib import Path
from time import time as now
from traceback import print_exc

import common.constants as const
import filecopy as backup
from common import patch
from common.types import GameBundle, TranslationFile


class ConfigError(Exception):
    pass


class PatchError(Exception):
    pass


class AlreadyPatchedError(PatchError):
    pass


class TranslationFileError(PatchError):
    pass


class NoAssetError(PatchError):
    pass


class PatchManager:
    totalFilesProcessed = 0
    totalFilesImported = 0

    def __init__(self, args: argparse.Namespace) -> None:
        # self.errorLog = stdout
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
        # if self.args.write_log and self.errorLog is stdout:
        #     self.errorLog = open("import.log", "w")
        # elif not self.args.write_log and self.errorLog is not stdout:
        #     self.errorLog.close()
        #     self.errorLog = stdout

    # TODO: replace with logger module probably
    # def __getstate__(self):
    #     data = self.__dict__.copy()
    #     del data['errorLog']
    #     return data

    def start(self):
        startTime = now()
        print(
            f"Importing group {self.args.group or 'all'}, id {self.args.id or 'all'}, idx {self.args.idx or 'all'} from translations/{self.args.type} to {self.args.dst}"
        )
        files = patch.searchFiles(
            self.args.type, self.args.group, self.args.id, self.args.idx, changed=self.args.changed
        )
        nFiles = len(files)
        self.totalFilesProcessed += nFiles
        nErrors = 0
        print(f"Found {nFiles} files.")

        # Not sure if threads are useful but multi-process takes too long upfront for low counts.
        with ProcessPoolExecutor() if nFiles > 25 else ThreadPoolExecutor() as pool:
            # map seems to be a tiny bit faster maybe?
            # chunksize seems to affect nothing, haven't tested >100 files tho
            for result in pool.map(self.patchFile, files):
                if result is None:
                    nErrors += 1
                    nFiles -= 1
                elif result is False:
                    nFiles -= 1
        self.totalFilesImported += nFiles
        print(f"Imported {nFiles} files in {deltaTime(startTime)} seconds.")
        if nErrors > 0:
            print(f"There were {nErrors} errors. Check import.log for details.")

    def patchFile(self, file: str) -> bool:
        isModified = False
        try:
            isModified, reason = self.patch(file)
            if isModified:
                print(f"Imported {file}{f' ({reason})' if reason else ''}")
            else:
                if self.args.verbose:
                    print(f"{file} not modified.")
        except (NoAssetError, AlreadyPatchedError) as e:
            if self.args.verbose:
                print(e)
        except PatchError as e:
            print(f"Skipped {file}: {e}")
        except Exception:
            print(f"Error importing {file}")
            if self.args.verbose:
                print_exc(chain=True)
                isModified = None
        return isModified

    def finish(self):
        pass
        # if self.errorLog is not stdout: self.errorLog.close()

    def loadTranslationFile(self, path):
        try:
            return TranslationFile(path, readOnly=True)
        except Exception:
            raise TranslationFileError(f"Couldn't load translation data from {path}.")

    def loadBundle(self, tlFile: TranslationFile):
        bundle = GameBundle.fromName(tlFile.bundle, load=False)
        if not bundle.exists:
            raise NoAssetError(f"{tlFile.bundle} does not exist in your game data.")
        if self.args.update:
            if (
                b := GameBundle(GameBundle.createPath(self.args.dst, tlFile.bundle), load=False)
            ).isPatched:
                tlModTime = tlFile.data.get("modified")
                if tlModTime and b.patchedTime != tlModTime:
                    bundle.importState = "translations modified"
                else:
                    raise AlreadyPatchedError(f"{tlFile.bundle} already patched.")
        try:
            bundle.load()
            bundle.linkedTlFile = tlFile
            return bundle
        except Exception as e:
            raise PatchError(f"UnityPy error: {repr(e)}, skipping {tlFile.bundle}.")

    def patch(self, path: str):
        """Swaps game assets with translation file data, returns modified state."""
        tlFile = self.loadTranslationFile(path)
        if self.args.skip_mtl and not tlFile.data.get("humanTl"):
            return False, None
        if self.args.use_tlg and isUsingTLG() and tlFile.data.get("tlg"):
            convertTlFile(tlFile)
            if self.args.verbose:
                print(f"Writing TLG version: {tlFile.name}")
            return False, None
        bundle = self.loadBundle(tlFile)

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

        return patcher.isModified, getattr(bundle, "importState", None)


class StoryPatcher:
    def __init__(self, manager: PatchManager, bundle: GameBundle) -> None:
        self.manager = manager
        self.skipped = 0
        self.totalBlocks = len(bundle.linkedTlFile.textBlocks)
        self.bundle = bundle
        self.assetData = bundle.rootAsset.read_typetree()

    def patch(self):
        for textBlock in self.bundle.linkedTlFile.textBlocks:
            blockIdx = textBlock["blockIdx"]
            try:
                asset = self.bundle.assets[textBlock["pathId"]]
            except KeyError:
                print(f"{self.bundle.bundleName}: {blockIdx}: Can't find path id, skipping.")
                continue
            else:
                assetData = asset.read_typetree()

            if not textBlock["enText"] and not textBlock["enName"]:
                self.skipped += 1
                continue
            else:
                assetData["Text"] = textBlock["enText"] or assetData["Text"]
                assetData["Name"] = textBlock["enName"] or assetData["Name"]

                # Calculate length
                # index length = sum(blocklenghts)
                # blocklength = cliplength + startframe + 1
                # cliplength = max(0, voicelength OR (text-length * cps / fps)) + waitframe
                # waitframe: usually 12 if voiced, 45 otherwise BUT random exceptions occur
                if "origClipLength" in textBlock and textBlock["enText"]:
                    newTxtLen = (
                        len(textBlock["enText"]) / self.manager.args.cps * self.manager.args.fps
                    )
                    newClipLen = int(
                        assetData["WaitFrame"] + max(newTxtLen, assetData["VoiceLength"])
                    )
                    if textBlock.get("newClipLength"):  # manual length override
                        try:
                            newClipLen = int(textBlock["newClipLength"])
                        except ValueError:
                            print(
                                f"{self.bundle.bundleName}: {blockIdx}: Invalid clip length defined, falling back to calculated value."
                            )
                        else:
                            if newClipLen < textBlock["origClipLength"]:
                                print(
                                    f"{self.bundle.bundleName}: {blockIdx}: Shorter clip length defined, currently only lengthening is supported. Length will cap to original."
                                )
                    if newClipLen > textBlock["origClipLength"]:
                        newBlockLen = newClipLen + assetData["StartFrame"] + 1
                        assetData["ClipLength"] = newClipLen
                        self.assetData["BlockList"][blockIdx]["BlockLength"] = newBlockLen
                        if self.manager.args.verbose:
                            print(
                                f"Adjusted TextClip length at {blockIdx}: {textBlock['origClipLength']} -> {newClipLen}"
                            )

                        if "animData" in textBlock:
                            for animGroup in textBlock["animData"]:
                                newAnimLen = (
                                    animGroup["origLen"] + newClipLen - textBlock["origClipLength"]
                                )
                                if newAnimLen > animGroup["origLen"]:
                                    try:
                                        animAsset = self.bundle.assets[animGroup["pathId"]]
                                    except KeyError:
                                        if self.manager.args.verbose:
                                            print(
                                                f"Can't find animation asset ({animGroup['pathId']}) at {blockIdx}"
                                            )
                                    else:
                                        animData = animAsset.read_typetree()
                                        animData["ClipLength"] = newAnimLen
                                        animAsset.save_typetree(animData)
                                        if self.manager.args.verbose:
                                            print(
                                                f"Adjusted AnimClip length at {blockIdx}: {animGroup['origLen']} -> {newAnimLen}"
                                            )
                        elif self.manager.args.verbose:
                            print(f"Text length adjusted but no anim data found at {blockIdx}")

                if "choices" in textBlock:
                    jpChoices, enChoices = assetData["ChoiceDataList"], textBlock["choices"]
                    if len(jpChoices) != len(enChoices):
                        print("Choice lengths do not match, skipping choice block.")
                    else:
                        for idx, choice in enumerate(textBlock["choices"]):
                            if choice["enText"]:
                                jpChoices[idx]["Text"] = choice["enText"]

                if "coloredText" in textBlock:
                    jpColored, enColored = assetData["ColorTextInfoList"], textBlock["coloredText"]
                    if len(jpColored) != len(enColored):
                        print("Colored text lengths do not match, skipping color block...")
                    else:
                        for idx, text in enumerate(textBlock["coloredText"]):
                            if text["enText"]:
                                jpColored[idx]["Text"] = text["enText"]
            asset.save_typetree(assetData)

        try:
            self.assetData["TypewriteCountPerSecond"] = self.manager.args.fps * 3
            self.assetData["Length"] = reduce(
                lambda x, b: x + b["BlockLength"], self.assetData["BlockList"], 0
            )
            self.save()
        except Exception as e:
            print(f"Unexpected error in {self.bundle.bundleName}: {repr(e)}")

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
        help="Ignore some errors and print debug info to file instead of terminal (stdout)",
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
        print("Error logs temporarily not supported, output will be in console.")

    if args.use_tlg:
        global isUsingTLG
        global convertTlFile
        from common.utils import isUsingTLG
        from manage import convertTlFile
    startTime = now()
    patcher = PatchManager(args)
    try:
        patcher.start()
        if args.fullImport:
            for type in const.TARGET_TYPES[1:]:
                patcher.config(type=type)
                patcher.start()
            print(
                f"Updated a total of {patcher.totalFilesImported} files in {deltaTime(startTime)}"
            )
    finally:
        patcher.finish()


if __name__ == "__main__":
    main()
