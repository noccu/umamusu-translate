import common
import ass
import srt
import re
from Levenshtein import ratio
from enum import Enum, auto
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
        self.choicePrefix = ">"
        
    @classmethod
    def fromArgs(cls, args):
        o = cls()
        for k, v in vars(args).items():
            if hasattr(o, k):
                setattr(o, k, v)
        return o

class TextLine:
    def __init__(self, text, name = "", effect = "") -> None:
        self.text: str = text
        self.name: str = name.lower()
        self.effect: str = effect.lower()

    def isChoice(self) -> bool:
        return self.effect == "choice"

class BasicSubProcessor:
    skipNames = ["<username>", "", "モノローグ"]

    def __init__(self, srcFile, options = SubTransferOptions()):
        self.srcFile = common.TranslationFile(srcFile)
        self.srcLines = self.srcFile.textBlocks
        self.subLines: list[TextLine] = list()
        self.format = SubFormat.NONE
        self.options = options

    def saveSrc(self):
        self.srcFile.save()

    def getJp(self, idx):
        return self.srcLines[idx]['jpText']
    def getEn(self, idx):
        return TextLine(self.srcLines[idx]['enText'], self.srcLines[idx]['enName'])
    def setEn(self, idx, line: TextLine):
        self.srcLines[idx]['enText'] = self.filter(line, self.srcLines[idx])
        if "jpName" in self.srcLines[idx]:
            if self.srcLines[idx]['jpName'] in self.skipNames:
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

    def cleanLine(self, text):
        if text.startswith(self.options.choicePrefix): text = text[len(self.options.choicePrefix):]
        return text

    def filter(self, line: TextLine, target):
        filter = self.options.filter
        if filter:
            if "npre" in filter:
                m = re.match(r"\[?([^\]:]+)\]?: (.+)", line.text, flags=re.DOTALL)
                if m:
                    line.name, line.text = m.group(1,2)
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
        for line in self.subLines:
            if not line.effect and (line.text.startswith(self.options.choicePrefix)):
                line.effect = "choice"
            line.text = self.cleanLine(line.text)

    def duplicateSub(self, idx: int, line: TextLine = None):
        # duplicate text and choices
        self.setEn(idx, self.getEn(idx-1))
        choices = self.getChoices(idx-1)
        if choices and self.getChoices(idx):
            for c, choice in enumerate(choices):
                self.setChoices(idx, c, TextLine(choice['enText']))

        # Add sub text to matching (next) block and return it as new pos
        if line:
            if idx < len(self.srcLines) - 1:
                idx += 1
                self.setEn(idx, line)
            else:
                print("Attempted to duplicate beyond last line of file. Subtitle file does not match?")
        return idx

    def isDuplicateBlock(self, idx: int) -> bool:
        if self.srcFile.type != "story": return False
        prevName = self.srcLines[idx - 1]['jpName']
        curName = self.srcLines[idx]['jpName']
        if not self.options.dupeCheckAll and curName not in self.skipNames: return False
        return curName == prevName and ratio(self.getJp(idx), self.getJp(idx-1)) > 0.6

class AssSubProcessor(BasicSubProcessor):
    def __init__(self, srcFile, subFile, opts) -> None:
        super().__init__(srcFile, opts)
        self.format = SubFormat.ASS
        with open(subFile, encoding='utf_8_sig') as f:
            self.preprocess(ass.parse(f))

    def cleanLine(self, text):
        text = re.sub(r"\{(?:\\([ib])1|(\\[ib])0)\}", r"<\1\2>", text) # transform italic/bold tags
        text = re.sub(r"\{.+?\}", "", text) # remove others
        text = text.replace("\\N", "\n")
        text = super().cleanLine(text)
        return text

    def preprocess(self, parsed):
        lastSplit = None
        for line in parsed.events:
            if re.match("skip", line.effect, re.IGNORECASE): continue
            if line.name == "Nameplate": continue
            if not re.search("MainText|Default|Button", line.style, re.IGNORECASE): continue
            
            line.text = self.cleanLine(line.text)
            if re.match("split", line.effect, re.IGNORECASE):
                if lastSplit and line.effect[-2:] == lastSplit:
                    self.subLines[-1].text += f"\n{line.text}"
                    continue
                lastSplit = line.effect[-2:]
            else: lastSplit = None

            if not line.effect and line.style.endswith("Button") or line.name == "Choice":
                line.effect = "choice"
            self.subLines.append(TextLine(line.text, line.name, line.effect))
            
class SrtSubProcessor(BasicSubProcessor):
    def __init__(self, srcFile, subFile, opts) -> None:
        super().__init__(srcFile, opts)
        self.format = SubFormat.SRT
        with open(subFile, encoding='utf_8') as f:
            self.preprocess(srt.parse(f))

    def preprocess(self, parsed):
        for line in parsed:
            if len(self.subLines):
                m = re.search(r" {2,}$", self.subLines[-1].text)
                if m:
                    self.subLines[-1].text = self.subLines[-1].text[:m.start()] + f" \n{line.content}"
                    continue
            self.subLines.append(TextLine(line.content))
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
    lastChoice = [0, 0]

    for subLine in p.subLines:
        if idx == srcLen:
            print(f"File filled at idx {idx}. Next file part starts at: {subLine.text}")
            break

        # skip title logo on events and dummy text
        if p.getJp(idx).startswith("イベントタイトルロゴ表示") or re.match("※*ダミーテキスト", p.getJp(idx)):
            idx += 1
        # races can have "choices" but their format is different because there is always only 1 and can be treated as normal text
        if storyType == "story":
            if subLine.isChoice():
                if not p.getChoices(idx-1):
                    print(f"Found assumed choice subtitle, but no matching choice found at block {p.getBlockIdx(idx-1)}, skipping...")
                    continue
                if lastChoice[0] == idx: # Try adding multiple choice translations
                    try: p.setChoices(idx-1, lastChoice[1], subLine)
                    except IndexError: print(f"Choice idx error at {p.getBlockIdx(idx-1)}")
                else: # Copy text to all choices
                    p.setChoices(idx-1, None, subLine)
                lastChoice[0] = idx
                lastChoice[1] += 1
                continue # don't increment idx
            elif idx > 0 and p.getChoices(idx-1) and idx - lastChoice[0] > 0:
                print(f"Missing choice subtitle at block {p.getBlockIdx(idx-1)}")
            lastChoice[1] = 0
        
        # Add text
        if p.isDuplicateBlock(idx):
            print(f"Found gender dupe at block {p.getBlockIdx(idx)}, duplicating.")
            idx = p.duplicateSub(idx, subLine) + 1
            continue
        else:
            if len(subLine.text) == 0:
                print(f"Untranslated line at {p.getBlockIdx(idx)}")
            else:
                p.setEn(idx, subLine)
        idx += 1
    # check niche case of duplicate last line (idx is already increased)
    if idx < srcLen:
        if p.isDuplicateBlock(idx):
            print("Last line is duplicate! (check correctness)")
            p.duplicateSub(idx)
        else:
            print(f"Lacking {srcLen - idx} subtitle(s).")

    p.saveSrc()

def main():
    ap = common.Args("Imports translations from subtitle files. A few conventions are used.", defaultArgs=False,
                        epilog="Ideally 1 sub line per 1 game text screen. Add empty lines for untranslated.\
                        \nASS: Actor field for names, Effect field for 'choice', 'skip', 'split' (all lines)\
                        \nSRT: Prefix name 'Name: Dialogue', '>' for choices, 2+ spaces for splits (all except last line)")
    ap.add_argument("src", help="Target Translation File, overwrites other file options")
    ap.add_argument("sub", help="Target subtitle file. Supports ASS, SRT, TXT")
    ap.add_argument("-OVRNAMES", dest="overrideNames", action="store_true", help="Replace existing names with names from subs")
    ap.add_argument("-DUPEALL", dest="dupeCheckAll", action="store_true", help="Check all lines for duplicates instead of only trainer's/narration")
    ap.add_argument("-filter", nargs="+", choices=["npre", "brak"],
                    help="Process some common patterns (default: %(default)s)\
                    \nnpre: remove char name prefixes and extract them to enName field\
                    \nbrak: sync enclosing brackets with original text")
    ap.add_argument("-cpre", dest="choicePrefix", default=">", help="Prefix string that marks choices")
    args = ap.parse_args()
    process(args.src, args.sub, SubTransferOptions.fromArgs(args))
    print("Successfully transferred.")

if __name__ == '__main__':
    main()