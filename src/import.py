import argparse
import common
from pathlib import Path
import UnityPy
from UnityPy.files import ObjectReader
from os import SEEK_END, PathLike
from traceback import print_exc
from sys import stdout
from functools import reduce

class ConfigError(Exception): pass
class PatchError(Exception): pass
class AlreadyPatchedError(PatchError): pass
class TranslationFileError(PatchError): pass
class NoAssetError(PatchError): pass

class PatchManager:
    editMark = b"\x08\x04"
    
    def __init__(self, args: argparse.Namespace) -> None:
        self.errorLog = stdout
        self.config(args)

    def config(self, args = None, **kwargs):
        if args:
            self.args = args
        else:
            for k, v in kwargs.items():
                if hasattr(self.args, k):
                    setattr(self.args, k, v)
                else:
                    raise ConfigError(f"Invalid config arg: {k}: {v}")
        if self.args.overwrite: self.args.dst = common.GAME_ASSET_ROOT
        if self.args.silent and self.errorLog is stdout:
                self.errorLog = open("import.log", "w")
        elif not self.args.silent and self.errorLog is not stdout:
                self.errorLog.close()
                self.errorLog = stdout

    def start(self):
        print(f"Importing group {self.args.group or 'all'}, id {self.args.id or 'all'}, idx {self.args.idx or 'all'} from translations\{self.args.type} to {self.args.dst}")
        files = common.searchFiles(self.args.type, self.args.group, self.args.id, self.args.idx)
        nFiles = len(files)
        nErrors = 0
        print(f"Found {nFiles} files.")

        for file in files:
            print(f"Importing {file}... ", end="", flush=True)
            try:
                if (self.patch(file)): 
                    print("done.")
                else:
                    nFiles -= 1
                    print("not modified.")
            except PatchError as e:
                nFiles -= 1
                print(f"skipped: {e}")
            except:
                nFiles -= 1
                nErrors += 1
                print("error.") # newline
                if self.args.silent:
                    print(f"Error in {file}", file=self.errorLog)
                    print_exc(chain=True, file=self.errorLog)
                else:
                    raise
        print(f"Imported {nFiles} files.")
        if nErrors > 0: print(f"There were {nErrors} errors. Check import.log for details.")

    def finish(self):
        if self.errorLog is not stdout: self.errorLog.close()

    def loadTranslationFile(self, path):
        try:
            self.tlFile = common.TranslationFile(path)
        except:
            raise TranslationFileError(f"Couldn't load translation data from {path}.")

    def loadBundle(self, bundle: str):
        bundlePath = Path(common.GAME_ASSET_ROOT, bundle[0:2], bundle)
        if not bundlePath.exists():
            raise NoAssetError(f"{bundle} does not exist in your game data.")
        elif self.args.update:
            savePath = Path(self.args.dst, bundle[0:2], bundle)
            if self.checkFilePatched(savePath):
                raise AlreadyPatchedError(f"{bundle} already patched.")

        try:
            self.bundle = UnityPy.load(str(bundlePath))
        except:
            raise PatchError(f"UnityPy error, skipping {bundle}.")
        self.rootAsset: ObjectReader = next(iter(self.bundle.container.values())).get_obj()
        self.assets: list[ObjectReader] = self.rootAsset.assets_file.files

    def patch(self, path: str):
        """Swaps game assets with translation file data, returns modified state."""
        self.loadTranslationFile(path)
        self.loadBundle(self.tlFile.bundle)
        if self.tlFile.type in ("story", "home"):
            patcher = StoryPatcher(self)
        elif self.tlFile.type == "race":
            patcher = RacePatcher(self)
        elif self.tlFile.type == "preview":
            patcher = PreviewPatcher(self)
        elif self.tlFile.type == "lyrics":
            patcher = LyricsPatcher(self)

        patcher.patch()
        if patcher.isModified:
            self.saveAsset()
            return True
        else: return False

    def saveAsset(self):
        # b = self.bundle.file.save() #! packer="original" or any compression doesn't seem to work, the game will crash or get stuck loading forever
        # b += b"\x08\x04"
        b = self.markFilePatched(self.bundle.file.save())
        fn = self.bundle.file.name
        fp = Path(self.args.dst, fn[0:2], fn)
        fp.parent.mkdir(parents=True, exist_ok=True)
        with open(fp, "wb") as f:
            f.write(b)

    @classmethod
    def markFilePatched(cls, data: bytes):
        return data + cls.editMark
    @classmethod
    def checkFilePatched(cls, filePath: PathLike):
        try:
            with open(filePath, "rb") as f:
                f.seek(-2, SEEK_END)
                if f.read(2) == cls.editMark:
                    return True
        except FileNotFoundError:
            pass # Should normally not occur
        return False

class StoryPatcher:
    def __init__(self, manager: PatchManager) -> None:
        self.manager = manager
        self.skipped = 0
        self.totalBlocks = len(self.manager.tlFile.textBlocks)
    def patch(self):
        mainTree = self.manager.rootAsset.read_typetree()

        for textBlock in self.manager.tlFile.textBlocks:
            blockIdx = textBlock['blockIdx']
            try:
                self.asset = self.manager.assets[textBlock['pathId']]
            except KeyError:
                print(f"{self.manager.tlFile.bundle}: {blockIdx}: Can't find path id, skipping.")
                continue
            else:
                assetData = self.asset.read_typetree()
            
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
                    if "newClipLength" in textBlock and textBlock["newClipLength"]:
                        try:
                            newClipLen = int(textBlock["newClipLength"])
                        except ValueError:
                            print(f"{self.manager.tlFile.bundle}: {blockIdx}: Invalid clip length, skipping.")
                            continue
                    newBlockLen = max(textBlock['origClipLength'], newClipLen) + assetData['StartFrame'] + 1
                    assetData['ClipLength'] = newClipLen
                    mainTree['BlockList'][blockIdx]['BlockLength'] = newBlockLen
                    if not self.manager.args.silent and newClipLen > textBlock['origClipLength']:
                        print(f"Adjusted TextClip length at {blockIdx}: {textBlock['origClipLength']} -> {newClipLen}")

                    if "animData" in textBlock:
                        for animGroup in textBlock['animData']:
                            animAsset = self.manager.assets[animGroup['pathId']]
                            if animAsset:
                                animData = animAsset.read_typetree()
                                animData['ClipLength'] = animGroup['origLen'] + newClipLen - textBlock['origClipLength']
                                animAsset.save_typetree(animData)
                                if not self.manager.args.silent:
                                    print(f"Adjusted AnimClip length at {blockIdx}: {animGroup['origLen']} -> {animData['ClipLength']}")
                            elif not self.manager.args.silent: print(f"Can't find animation asset ({animGroup['pathId']}) at {blockIdx}")
                    else:
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
            self.assetData = assetData
            self.save()

        try:
            mainTree['TypewriteCountPerSecond'] = self.manager.args.fps * 3
            mainTree['Length'] = reduce(lambda x, b: x + b['BlockLength'], mainTree['BlockList'], 0)
            self.manager.rootAsset.save_typetree(mainTree)
        except Exception as e:
            print(f"Unexpected error in {self.manager.tlFile.bundle}: {type(e).__name__}: {e}")
    def save(self):
        if self.isModified:
            self.asset.save_typetree(self.assetData)
    @property
    def isModified(self):
        return self.skipped != self.totalBlocks

class RacePatcher(StoryPatcher):
    def __init__(self, manager: PatchManager) -> None:
        super().__init__(manager)
        self.asset = self.manager.rootAsset
        self.assetData = self.asset.read_typetree()
    def patch(self):
        for textBlock in self.manager.tlFile.textBlocks:
            blockIdx = textBlock['blockIdx'] - 1 # race keys start at 1
            if textBlock['enText']: self.assetData['textData'][blockIdx]['text'] = textBlock['enText']
            else: self.skipped += 1; continue
        self.save()

class PreviewPatcher(RacePatcher):
    def patch(self):
        for blockIdx, textBlock in enumerate(self.manager.tlFile.textBlocks):
            if not textBlock['enText'] and not textBlock['enName']:
                self.skipped += 1
                continue
            else:
                if textBlock['enName']: self.assetData['DataArray'][blockIdx]['Name'] = textBlock['enName']
                if textBlock['enText']: self.assetData['DataArray'][blockIdx]['Text'] = textBlock['enText']
        self.save()

class LyricsPatcher(StoryPatcher):
    def __init__(self, manager: PatchManager) -> None:
        super().__init__(manager)
        self.asset = self.manager.rootAsset
        self.assetData = self.asset.read()
        self.assetText = "time,lyrics\n"
    def patch(self):
        for textBlock in self.manager.tlFile.textBlocks:
            # Format the CSV text. Their parser uses quotes, no escape chars. For novelty: \t = space; \v and \f = ,; \r = \n
            text = textBlock['enText']
            if not text:
                text = textBlock['jpText']
                self.skipped += 1
            elif "," in text or "\"" in text:
                text = '"' + text.replace('\"','\"\"') + '"'
            self.assetText += f"{textBlock['time']},{text}\n"
        self.save()

    def save(self):
        if self.isModified:
            self.assetData.script = bytes(self.assetText, "utf8")
            self.assetData.save()


def main():
    ap = common.NewArgs("Write Game Assets from Translation Files")
    ap.add_argument("-O", dest="overwrite", action="store_true", help="(Over)Write files straight to game directory")
    ap.add_argument("-U", "--update", dest="update", action="store_true", help="Skip already imported files")
    ap.add_argument("-FI", "--full-import", dest="fullImport", action="store_true", help="Import all available types")
    ap.add_argument("-S", "--silent", dest="silent", action="store_true", help="Ignore some errors and print debug info to file. Default: terminal (stdout)")
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