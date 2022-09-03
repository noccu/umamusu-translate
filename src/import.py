import argparse
from pathlib import Path
from traceback import print_exc
from sys import stdout
from functools import reduce

import common
from common import GameBundle


class ConfigError(Exception): pass
class PatchError(Exception): pass
class AlreadyPatchedError(PatchError): pass
class TranslationFileError(PatchError): pass
class NoAssetError(PatchError): pass


class PatchManager:
    def __init__(self, args: argparse.Namespace) -> None:
        self.errorLog = stdout
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
            self.args.dst = common.GAME_ASSET_ROOT
        if self.args.write_log and self.errorLog is stdout:
            self.errorLog = open("import.log", "w")
        elif not self.args.write_log and self.errorLog is not stdout:
            self.errorLog.close()
            self.errorLog = stdout

    def start(self):
        print(f"Importing group {self.args.group or 'all'}, id {self.args.id or 'all'}, idx {self.args.idx or 'all'} from translations\{self.args.type} to {self.args.dst}")
        files = common.searchFiles(self.args.type, self.args.group, self.args.id, self.args.idx, changed = self.args.changed)
        nFiles = len(files)
        nErrors = 0
        print(f"Found {nFiles} files.")

        for file in files:
            try:
                if self.patch(file):
                    print(f"Imported {file}")
                else:
                    nFiles -= 1
            except (NoAssetError, AlreadyPatchedError):
                nFiles -= 1  # Expected behaviour; don't print
            except PatchError as e:
                nFiles -= 1
                print(f"Skipped {file}: {e}")
            except:
                nFiles -= 1
                nErrors += 1
                print(f"Error importing {file}")
                if self.args.write_log:
                    print(f"Error in {file}", file=self.errorLog)
                    print_exc(chain=True, file=self.errorLog)
                else:
                    raise
        print(f"Imported {nFiles} files.")
        if nErrors > 0:
            print(f"There were {nErrors} errors. Check import.log for details.")

    def finish(self):
        if self.errorLog is not stdout: self.errorLog.close()

    def loadTranslationFile(self, path):
        try:
            self.tlFile = common.TranslationFile(path, readOnly=True)
        except:
            raise TranslationFileError(f"Couldn't load translation data from {path}.")

    def loadBundle(self, name: str):
        bundle = GameBundle.fromName(name, load=False)
        if not bundle.exists:
            raise NoAssetError(f"{name} does not exist in your game data.")

        if self.args.update:
            savePath = GameBundle.createPath(self.args.dst, name)
            bundle.readPatchState(customPath=savePath)
            if bundle.isPatched:
                tlModTime = self.tlFile.data.get("modified")
                if tlModTime and bundle.patchedTime != tlModTime:
                    print("translations modified... ", end="", flush=True)
                else:
                    raise AlreadyPatchedError(f"{self.tlFile.bundle} already patched.")

        try:
            return bundle.load()
        except Exception as e:
            raise PatchError(f"UnityPy error: {repr(e)}, skipping {name}.")

    def patch(self, path: str):
        """Swaps game assets with translation file data, returns modified state."""
        self.loadTranslationFile(path)
        bundle = self.loadBundle(self.tlFile.bundle)

        if self.tlFile.type in ("story", "home"):
            patcher = StoryPatcher(self, bundle)
        elif self.tlFile.type == "race":
            patcher = RacePatcher(self, bundle)
        elif self.tlFile.type == "preview":
            patcher = PreviewPatcher(self, bundle)
        elif self.tlFile.type == "lyrics":
            patcher = LyricsPatcher(self, bundle)

        patcher.patch()
        if patcher.isModified:
            bundle.setPatchState(self.tlFile)
            bundle.save(dstFolder=Path(self.args.dst))

        return patcher.isModified


class StoryPatcher:
    def __init__(self, manager: PatchManager, bundle: GameBundle) -> None:
        self.manager = manager
        self.skipped = 0
        self.totalBlocks = len(self.manager.tlFile.textBlocks)
        self.bundle = bundle
        self.assetData = bundle.rootAsset.read_typetree()

    def patch(self):
        for textBlock in self.manager.tlFile.textBlocks:
            blockIdx = textBlock['blockIdx']
            try:
                asset = self.bundle.assets[textBlock['pathId']]
            except KeyError:
                print(f"{self.bundle.bundleName}: {blockIdx}: Can't find path id, skipping.")
                continue
            else:
                assetData = asset.read_typetree()

            if not textBlock['enText'] and not textBlock['enName']:
                self.skipped += 1
                continue
            else:
                assetData['Text'] = textBlock['enText'] or assetData['Text']
                assetData['Name'] = textBlock['enName'] or assetData['Name']

                # Calculate length
                # index length = sum(blocklenghts)
                # blocklength = cliplength + startframe + 1
                # cliplength = max(0, voicelength OR (text-length * cps / fps)) + waitframe
                # waitframe: usually 12 if voiced, 45 otherwise BUT random exceptions occur
                if "origClipLength" in textBlock and textBlock['enText']:
                    newTxtLen = len(textBlock['enText']) / self.manager.args.cps * self.manager.args.fps
                    newClipLen = int(assetData['WaitFrame'] + max(newTxtLen, assetData['VoiceLength']))
                    if textBlock.get("newClipLength"): # manual length override
                        try:
                            newClipLen = int(textBlock["newClipLength"])
                        except ValueError:
                            print(f"{self.bundle.bundleName}: {blockIdx}: Invalid clip length defined, falling back to calculated value.")
                        else:
                            if newClipLen < textBlock['origClipLength']: print(f"{self.bundle.bundleName}: {blockIdx}: Shorter clip length defined, currently only lengthening is supported. Length will cap to original.")
                    if newClipLen > textBlock['origClipLength']:
                        newBlockLen = newClipLen + assetData['StartFrame'] + 1
                        assetData['ClipLength'] = newClipLen
                        self.assetData['BlockList'][blockIdx]['BlockLength'] = newBlockLen
                        if self.manager.args.verbose:
                            print(f"Adjusted TextClip length at {blockIdx}: {textBlock['origClipLength']} -> {newClipLen}")

                        if "animData" in textBlock:
                            for animGroup in textBlock['animData']:
                                newAnimLen = animGroup['origLen'] + newClipLen - textBlock['origClipLength']
                                if newAnimLen > animGroup['origLen']:
                                    try:
                                        animAsset = self.bundle.assets[animGroup['pathId']]
                                    except KeyError:
                                        if self.manager.args.verbose: print(f"Can't find animation asset ({animGroup['pathId']}) at {blockIdx}")
                                    else:
                                        animData = animAsset.read_typetree()
                                        animData['ClipLength'] = newAnimLen
                                        animAsset.save_typetree(animData)
                                        if self.manager.args.verbose:
                                            print(f"Adjusted AnimClip length at {blockIdx}: {animGroup['origLen']} -> {newAnimLen}")
                        elif self.manager.args.verbose:
                            print(f"Text length adjusted but no anim data found at {blockIdx}")

                if 'choices' in textBlock:
                    jpChoices, enChoices = assetData['ChoiceDataList'], textBlock['choices']
                    if len(jpChoices) != len(enChoices):
                        print("Choice lengths do not match, skipping choice block.")
                    else:
                        for idx, choice in enumerate(textBlock['choices']):
                            if choice['enText']:
                                jpChoices[idx]['Text'] = choice['enText']

                if 'coloredText' in textBlock:
                    jpColored, enColored = assetData['ColorTextInfoList'], textBlock['coloredText']
                    if len(jpColored) != len(enColored):
                        print("Colored text lengths do not match, skipping color block...")
                    else:
                        for idx, text in enumerate(textBlock['coloredText']):
                            if text['enText']:
                                jpColored[idx]['Text'] = text['enText']
            asset.save_typetree(assetData)

        try:
            self.assetData['TypewriteCountPerSecond'] = self.manager.args.fps * 3
            self.assetData['Length'] = reduce(lambda x, b: x + b['BlockLength'], self.assetData['BlockList'], 0)
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
        for textBlock in self.manager.tlFile.textBlocks:
            blockIdx = textBlock['blockIdx'] - 1  # race keys start at 1
            if textBlock['enText']:
                self.assetData['textData'][blockIdx]['text'] = textBlock['enText']
            else:
                self.skipped += 1
                continue
        self.save()


class PreviewPatcher(RacePatcher):
    def patch(self):
        for blockIdx, textBlock in enumerate(self.manager.tlFile.textBlocks):
            if not textBlock['enText'] and not textBlock['enName']:
                self.skipped += 1
                continue

            if textBlock['enName']: self.assetData['DataArray'][blockIdx]['Name'] = textBlock['enName']
            if textBlock['enText']: self.assetData['DataArray'][blockIdx]['Text'] = textBlock['enText']
        self.save()


class LyricsPatcher(StoryPatcher):
    def __init__(self, manager: PatchManager, bundle: GameBundle) -> None:
        super().__init__(manager, bundle)
        self.assetData = bundle.rootAsset.read()
        self.assetText = "time,lyrics\n"

    def patch(self):
        for textBlock in self.manager.tlFile.textBlocks:
            # Format the CSV text. Their parser uses quotes, no escape chars. For novelty: \t = space; \v and \f = ,; \r = \n
            text = textBlock['enText']
            if not text:
                text = textBlock['jpText']
                self.skipped += 1
            elif "," in text or '"' in text:
                text = '"' + text.replace('"', '""') + '"'
            self.assetText += f"{textBlock['time']},{text}\n"
        self.save()

    def save(self):
        if self.isModified:
            self.assetData.script = bytes(self.assetText, "utf8")
            self.assetData.save()


def main():
    ap = common.Args("Write Game Assets from Translation Files")
    ap.add_argument("-O", "--overwrite", action="store_true", help="(Over)Write files straight to game directory")
    ap.add_argument("-U", "--update", action="store_true", help="Skip already imported files")
    ap.add_argument("-FI", "--full-import", dest="fullImport", action="store_true", help="Import all available types")
    ap.add_argument("-wf", "--write-log", action="store_true",
                    help="Ignore some errors and print debug info to file instead of terminal (stdout)")
    ap.add_argument("-cps", default=28, type=int, help="Characters per second, for unvoiced lines (excludes choices)")
    ap.add_argument("-fps", default=30, type=int, help="Framerate, for calculating the right text speed")

    args = ap.parse_args()
    process(args)


def process(args):
    patcher = PatchManager(args)
    try:
        patcher.start()
        if args.fullImport:
            for type in common.TARGET_TYPES[1:]:
                patcher.config(type=type)
                patcher.start()
    finally:
        patcher.finish()


if __name__ == '__main__':
    main()
