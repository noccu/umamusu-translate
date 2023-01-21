import re
from enum import Enum, auto
from datetime import timedelta
from typing import Union

from Levenshtein import ratio
import ass
import srt

import common
import helpers

class SubFormat(Enum):
    NONE = auto()
    SRT = auto()
    ASS = auto()
    TXT = auto()

class SubTransferOptions():
    def __init__(self) -> None:
        self.setDefault()
    # separate so it can be used to reset
    def setDefault(self):
        self.overrideNames = False
        self.dupeCheckAll = False
        self.filter = None
        self.choicePrefix = [">"]
        self.strictChoices = True
        self.noDupeSubs: Union[bool, str] = False
        self.writeSubs = False
        self.notlComments = False
        self.mainStyles = "MainText|Default|Button"
        self.timeSync = False
        self.assetSync = False
        
    @classmethod
    def fromArgs(cls, args):
        o = cls()
        for k, v in vars(args).items():
            if hasattr(o, k):
                setattr(o, k, v)
        return o

class TextLine:
    def __init__(self, text, name = "", effect = "", start = None, end = None) -> None:
        self.text: str = text
        self.name: str = name
        self.effect: str = effect.lower()
        self.start: timedelta = start
        self.end: timedelta = end

    def isChoice(self) -> bool:
        return self.effect == "choice"

class BasicSubProcessor:
    npreRe = re.compile(r"\[?([^\]:]{2,40})\]?: (.+)", flags=re.DOTALL)

    def __init__(self, srcFile, options = SubTransferOptions()):
        self.srcFile = common.TranslationFile(srcFile)
        self.srcLines = self.srcFile.textBlocks
        self.subLines: list[TextLine] = list()
        self.format = SubFormat.NONE
        self.options = options
        self.cpreRe = re.compile("|".join(options.choicePrefix), re.IGNORECASE) # match searches start only
        # self.idx = 0 #TODO: track idx on class

        self.choiceNames = list()
        for cpre in options.choicePrefix:
            if len(cpre) > 1:
                idx = cpre.rfind(":") # update this when npre logic changes
                if idx > 0:
                    self.choiceNames.append(cpre[0:idx])

    def saveSrc(self):
        self.srcFile.save()

    def getJp(self, idx):
        return self.srcLines[idx]['jpText']
    def getEn(self, idx):
        return TextLine(self.srcLines[idx]['enText'], self.srcLines[idx]['enName'])
    def setEn(self, idx, line: TextLine):
        self.srcLines[idx]['enText'] = self.filter(line, self.srcLines[idx])
        if "jpName" in self.srcLines[idx]:
            if self.srcLines[idx]['jpName'] in common.NAMES_BLACKLIST:
                self.srcLines[idx]['enName'] = "" # forcefully clear names that should not be translated
            elif line.name and (not self.srcLines[idx]['enName'] or self.options.overrideNames):
                self.srcLines[idx]['enName'] = line.name

    def getChoices(self, idx):
        if not "choices" in self.srcLines[idx]: return None
        else: return self.srcLines[idx]['choices']
    def setChoices(self, idx, cIdx, line: TextLine):
        if not "choices" in self.srcLines[idx]: return None
        else:
            if (cIdx):
                self.srcLines[idx]['choices'][cIdx]['enText'] = self.filter(line, self.srcLines[idx]['choices'][cIdx])
            else:
                for entry in self.srcLines[idx]['choices']:
                    entry['enText'] = self.filter(line, entry)

    def getBlockIdx(self, idx):
        return self.srcLines[idx]['blockIdx']

    def cleanLine(self, text: str):
        return text.strip()

    def filter(self, line: TextLine, target):
        filter = self.options.filter
        if filter:
            if "brak" in filter:
                if target['jpText'].startswith("（"):
                    if not line.text.startswith("("):
                        line.text = f"({line.text})"
                elif line.text.startswith("("):
                        m = re.match(r"^\((.+)\)$", line.text, flags=re.DOTALL)
                        if m:
                            line.text = m.group(1)
        return line.text

    def preprocess(self):
        lastName = None
        for line in self.subLines:
            # Check for choices first
            if not line.effect:
                m = self.cpreRe.match(line.text)
                if m:
                    line.effect = "choice"
                    line.text = line.text[len(m.group(0)):]
                    continue # choices have no name
            # Check for names
            if m := self.npreRe.match(line.text):
                line.name, line.text = m.group(1,2)
            if not line.name and lastName:
                line.name = lastName
            else:
                lastName = line.name
            # Check for choices indicated by names
            if not line.effect and line.name in self.choiceNames:
                line.effect = "choice"
            line.text = self.cleanLine(line.text)

    def addSub(self, idx: int, subLine:TextLine):
        if idx > len(self.srcLines) - 1:
            print("Attempted to add sub beyond last line of file.")
            return idx

        # Attempt to match untranslated text
        if subLine.effect == "notl":
            subLine.text = "<UNTRANSLATED>"
        else:
            while len(subLine.text) == 0 or\
            re.match(r"（.+）$|(?:[…。―ー？！、　]*(?:(?:げほ|ごほ|[はくふワあアえ]*)[ぁァッぅっ]*)*)+$", self.getJp(idx)) and\
            not (len(subLine.text) < 15 or re.match(r"[(<*)].+[>*)]$|^(?:\W*[gnfh]*[eao]*[gfh]*\W*)+$", subLine.text, flags=re.IGNORECASE)):
                print(f"Marking untranslated line at {self.getBlockIdx(idx)}")
                # print("debug:", p.getJp(idx), subLine.text)
                self.setEn(idx, TextLine("<UNTRANSLATED>"))
                idx += 1
                if idx > len(self.srcLines) - 1:
                    return idx

        self.setEn(idx, subLine)
        idx += 1
        return idx

    def duplicateSub(self, idx: int, line: TextLine = None):
        # duplicate text and choices
        self.setEn(idx, self.getEn(idx-1))
        choices = self.getChoices(idx-1)
        if choices and self.getChoices(idx):
            for c, choice in enumerate(choices):
                self.setChoices(idx, c, TextLine(choice['enText']))

        return idx + 1

    def isDuplicateBlock(self, idx: int) -> bool:
        if self.srcFile.type != "story": return False
        prevName = self.srcLines[idx - 1]['jpName']
        curName = self.srcLines[idx]['jpName']
        if not self.options.dupeCheckAll and curName not in common.NAMES_BLACKLIST: return False
        return curName == prevName and ratio(self.getJp(idx), self.getJp(idx-1)) > 0.6

    def timeSync(self):
        i = 1
        end = len(self.subLines)
        while i < end:
            line = self.subLines[i]
            lastLine = self.subLines[i-1]
            if line.start == lastLine.end:
                lastLine.text += f"\n{line.text}"
                lastLine.end = line.end
                del self.subLines[i]
                end -= 1
                continue
            i+=1

    def assetSync(self):
        '''Attempts to join unmarked split lines based on timings derived from the game asset'''
        subFromBundle = createSubs(self.srcFile)
        if subFromBundle:
            subFromBundle = subFromBundle.events
        else:
            return
        self.shiftTimes(self.subLines, subFromBundle[0].end - self.subLines[0].end)
        print(f"Subs start at: {self.subLines[0].start}")
        if self.subLines[0].start.seconds > 1:
            self.shiftTimes(self.subLines, subFromBundle[0].start - self.subLines[0].start)
            print(f"Timing auto-adjusted to start at: {self.subLines[0].start}")

        i = 1
        j = 0
        while j < len(self.srcFile.textBlocks) and i < len(self.subLines):
            subLine = self.subLines[i]
            bundleLine = subFromBundle[j]
            lastSub = self.subLines[i-1]
            if self.getJp(j).startswith("イベントタイトルロゴ表示") or re.match("※*ダミーテキスト|欠番", self.getJp(j)):
                j += 1
                bundleLine = subFromBundle[j]

            if subLine.name == lastSub.name and (subLine.start + subLine.end) / 2 < bundleLine.end:
                lastSub.text += f"\n{subLine.text}"
                lastSub.end = subLine.end
                del self.subLines[i]
                continue
            i+=1
            j+=1

    @classmethod
    def shiftTimes(cls, textLines: list[TextLine], shiftDelta: timedelta):
        for line in textLines:
            line.start += shiftDelta
            line.end += shiftDelta

class AssSubProcessor(BasicSubProcessor):
    def __init__(self, srcFile, subFile, opts) -> None:
        super().__init__(srcFile, opts)
        self.format = SubFormat.ASS
        with open(subFile, encoding='utf_8_sig') as f:
            parsed = ass.parse(f)
        lastTimeStamp = zeroDelta = timedelta()
        def sort(x):
            nonlocal lastTimeStamp
            if x.start == zeroDelta:
                return lastTimeStamp 
            else:
                lastTimeStamp = x.start
                return x.start
        parsed.events._lines.sort(key=sort)
        self.preprocess(parsed)
        if self.options.timeSync:
            self.timeSync()
        if self.options.assetSync:
            self.assetSync()


    def cleanLine(self, text):
        text = re.sub(r"\{(?:\\([ib])1|(\\[ib])0)\}", r"<\1\2>", text) # transform italic/bold tags
        text = re.sub(r"\{.+?\}", "", text) # remove others
        text = text.replace("\\N", "\n").replace("<\\", "</")
        text = super().cleanLine(text)
        return text


    def preprocess(self, parsed):
        lastSplit = None
        lastName = None
        mainTextRe = re.compile(self.options.mainStyles, re.IGNORECASE)
        charaStyleRe = re.compile("Chara", re.IGNORECASE)
        splitRe = re.compile("split", re.IGNORECASE)
        for line in parsed.events:
            # Custom translator-specific formats
            if line.name == "Nameplate" or charaStyleRe.search(line.style): 
                lastName = line.text
                continue
            isMainText = mainTextRe.search(line.style)
            if not isinstance(line, ass.Dialogue):
                if self.options.notlComments and isMainText: line.effect = "notl"
                elif not line.effect == "notl": continue
            elif not isMainText or line.effect in ("skip", "Skip"):
                continue
            
            line.text = self.cleanLine(line.text)
            if splitRe.match(line.effect):
                if lastSplit and line.effect[-2:] == lastSplit:
                    self.subLines[-1].text += f"\n{line.text}"
                    self.subLines[-1].end = line.end
                    continue
                lastSplit = line.effect[-2:]
            else: lastSplit = None

            if not line.effect and line.style.endswith("Button") or line.name == "Choice":
                line.effect = "choice"
            self.subLines.append(TextLine(line.text, line.name or lastName, line.effect, line.start, line.end))
            lastName = self.subLines[-1].name
            
class SrtSubProcessor(BasicSubProcessor):
    def __init__(self, srcFile, subFile, opts) -> None:
        super().__init__(srcFile, opts)
        self.format = SubFormat.SRT
        with open(subFile, encoding='utf_8') as f:
            self.preprocess(srt.parse(f))
        if self.options.timeSync:
            self.timeSync()
        if self.options.assetSync:
            self.assetSync()

    def preprocess(self, parsed):
        for line in parsed:
            if len(self.subLines):
                # Parse line splits from 2+ spaces at line end.
                m = re.search(r" {2,}$", self.subLines[-1].text)
                if m:
                    self.subLines[-1].text = self.subLines[-1].text[:m.start()] + f" \n{line.content}"
                    continue
            self.subLines.append(TextLine(line.content, start=line.start, end=line.end))
        super().preprocess()

class TxtSubProcessor(BasicSubProcessor):
    # Built on Holo's docs
    # Expects: No newlines in block, blocks separated by newline (or any number of blank lines).
    def __init__(self, srcFile, subFile, opts) -> None:
        super().__init__(srcFile, opts)
        self.format = SubFormat.TXT
        with open(subFile, "r", encoding="utf8") as f:
            self.preprocess(f)

    def preprocess(self, raw):
        self.subLines = [TextLine(l) for l in raw if helpers.isEnglish(l) and not re.match(r"\n+\s*", l)]

def process(srcFile, subFile, opts: SubTransferOptions):
    format = subFile[-3:]
    if format == "srt":
        p = SrtSubProcessor(srcFile, subFile, opts)
    elif format == "ass":
        p = AssSubProcessor(srcFile, subFile, opts)
    elif format == "txt":
        p = TxtSubProcessor(srcFile, subFile, opts)
    else:
        print("Unsupported subtitle format.")
        raise NotImplementedError

    storyType = p.srcFile.type
    idx = 0
    srcLen = len(p.srcLines)
    lastChoice = [0, 0] # text idx, choice idx
    errors = 0

    for subLine in p.subLines:
        if idx == srcLen:
            print(f"File filled at idx {idx}. Next file part starts at: {subLine.text}")
            break

        # skip title logo on events and dummy text
        if p.getJp(idx).startswith("イベントタイトルロゴ表示") or re.match("※*ダミーテキスト|欠番", p.getJp(idx)):
            idx += 1
        # Skip repeated subs (usually for style)
        if opts.noDupeSubs:
            # print(f"checking\n{subLine}\nto\n{p.getEn(idx-1).text}")
            if (opts.noDupeSubs == "strict" and subLine.text == p.getEn(idx-1).text)\
                or (opts.noDupeSubs == "loose" and subLine.text in p.getEn(idx-1).text):
                print(f"Dupe sub skipped at {p.getBlockIdx(idx)}: {subLine.text}")
                continue

        # races can have "choices" but their format is different because there is always only 1 and can be treated as normal text
        if storyType == "story":
            if subLine.isChoice():
                skipLine = True
                if p.getChoices(idx-1):
                    if lastChoice[0] == idx: # Try adding multiple choice translations
                        try: p.setChoices(idx-1, lastChoice[1], subLine)
                        except IndexError:
                            # can give false positives
                            skipLine = opts.strictChoices
                            print(f"Choice idx error at {p.getBlockIdx(idx-1)}{'' if skipLine else ' (ignored)'}")
                            if skipLine: errors += 1
                    else: # Copy text to all choices
                        p.setChoices(idx-1, None, subLine)
                    lastChoice[0] = idx
                    lastChoice[1] += 1
                    if skipLine: continue # don't increment idx
                elif opts.strictChoices:
                    print(f"Found assumed choice subtitle, but no matching choice found at block {p.getBlockIdx(idx-1)}, skipping...")
                    errors += 1
                    continue
            elif idx > 0 and p.getChoices(idx-1) and idx - lastChoice[0] > 0:
                print(f"Missing choice subtitle at block {p.getBlockIdx(idx-1)}")
                errors += 1
            lastChoice[1] = 0

        # Add text
        if p.isDuplicateBlock(idx):
            print(f"Found dupe source line at block {p.getBlockIdx(idx)}, duplicating.")
            idx = p.duplicateSub(idx, subLine)

        idx = p.addSub(idx, subLine)
    # check niche case of duplicate last line (idx is already increased)
    if idx < srcLen:
        if p.isDuplicateBlock(idx):
            print("Last line is duplicate! (check correctness)")
            p.duplicateSub(idx)
        else:
            print(f"Lacking {srcLen - idx} subtitle(s).")
            errors += 1

    p.saveSrc()
    if errors > 0:
        print(f"Transferred with {errors} errors.")
    else:
        print("Successfully transferred.")

def createSubs(tlFile, fps = 30):
    try:
        bundle = common.GameBundle.fromName(tlFile.bundle)
    except FileNotFoundError:
        print("Bundle doesn't exist.")
        return None
    title = tlFile.data.get('title', "")
    # if tlFile.version < 5:
    #     print(f"File version is too old to create subs, re-extract first: ${tlFile.name}")
    #     continue
    subs = ass.Document()
    subs.info._fields['Title'] = title
    subs.info._fields['ScriptType'] = subs.info.VERSION_ASS
    subs.styles._lines.append(ass.Style())
    ts = 0
    for block in tlFile.textBlocks:
        assetData = bundle.getAssetData(block.get('pathId'))
        voiced = True
        len = assetData.get('VoiceLength') 
        if len == -1: 
            len = assetData.get('ClipLength')
            voiced = False
        len += 1 # blocklen adds this too so I'm copying it here
        len /= fps
        ts += (assetData.get('StartFrame', 1) - 1) / fps # dunno why but this -1 improves timings
        line = ass.Dialogue(
            start=timedelta(seconds=ts), 
            end=timedelta(seconds=ts+len), 
            name=block.get('enName') or block.get('jpName', ""), 
            text=(block.get('enText') or block.get('jpText', "")).replace("\n", "\\N")
        )
        ts += len + (assetData.get('WaitFrame') / fps if voiced else 0)
        if block.get('choices'):
            line.effect = "choice"
        subs.events._lines.append(line)
    return subs

def writeSubs(sType, storyid):
    files = common.searchFiles(sType, *common.StoryId.parse(sType, storyid))
    for tlFile in files:
        tlFile = common.TranslationFile(tlFile)
        subs = createSubs(tlFile)
        if not subs: 
            return
        helpers.mkdir("subs")
        with open(f"subs/{tlFile.getStoryId()} {subs.info['Title']}.ass", "w", encoding='utf_8_sig') as f:
           subs.dump_file(f)


def main():
    ap = common.Args("Imports translations from subtitle files. A few conventions are used.", defaultArgs=False,
                        epilog="Ideally 1 sub line per 1 game text screen. Add empty lines for untranslated.\
                        \nASS: Actor field for names, Effect field for 'choice', 'skip', 'split' (all lines)\
                        \nSRT: Prefix name 'Name: Dialogue', '>' for choices, 2+ spaces for splits (all except last line)")
    ap.add_argument("src", help="Target Translation File, overwrites other file options")
    ap.add_argument("sub", help="Target subtitle file. Supports ASS, SRT, TXT")
    ap.add_argument("-OVRNAMES", dest="overrideNames", action="store_true", help="Replace existing names with names from subs")
    ap.add_argument("-DUPEALL", dest="dupeCheckAll", action="store_true", help="Check all lines for duplicates instead of only trainer's/narration")
    ap.add_argument("-filter", nargs="+", choices=["brak"],
                    help="Process some common patterns (default: %(default)s)\
                    \nbrak: sync enclosing brackets with original text")
    ap.add_argument("-cpre", dest="choicePrefix", nargs="+", default=[">"], help="Prefixes that mark choices. Supports regex\nChecks name as a special case if prefix includes ':'")
    ap.add_argument("--no-strict-choices", dest="strictChoices", action="store_false", help="Use choice sub line as dialogue when no choice in original")
    ap.add_argument("--skip-dupe-subs", dest="noDupeSubs", nargs="?", default = False, const = "strict", choices=["strict", "loose"], help="Skip subsequent duplicated subtitle lines")
    ap.add_argument("-ass --write-subs", dest="writeSubs", action="store_true", help="Write ASS subs from tl files\nsrc = story type, sub = storyid")
    ap.add_argument("--notl-comments", dest="notlComments", action="store_true", help="Try to find untranslated lines left in comments which match --main-styles.")
    ap.add_argument("-main --main-styles", dest="mainStyles", default="MainText|Default|Button", help="Filter by these ASS styles. No effect on non-ASS subs.\nA regexp that should match all useful text and choice styles.")
    ap.add_argument("--asset-sync", dest="assetSync", action="store_true", help="Auto-unsplit lines based on asset times.")
    ap.add_argument("--time-sync", dest="timeSync", action="store_true", help="Auto-unsplit lines based on sub times.")
    args = ap.parse_args()
    if args.writeSubs:
        writeSubs(args.src, args.sub)
    else:
        process(args.src, args.sub, SubTransferOptions.fromArgs(args))

if __name__ == '__main__':
    main()