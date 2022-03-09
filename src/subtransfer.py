from pydoc import text
import ass
import srt
import common
import re
from Levenshtein import ratio
# from datetime import timedelta

args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-src <translation file> -sub <subtitle file> [-off <offset> -npre -auto]",
                 "Imports translations from subtitle files. A few conventions are used.",
                 "Files are only modified if they can be assumed to merge properly. This check relies on text block lenghts."
                 "-offset is subtracted from the game file's text block length during this checking. (default -1 = off, set to 0 to start checking)",
                 "Events for example, have an unshown title logo display line. This script skips those automatically but requires offset to be set for correct checking, as per above.",
                 "-npre flags text lines as prefixed by the char name",
                 "\n"
                 "Conventions are to have 1 subtitle line per game text block/screen. Include empty lines if needed (say, if you leave a line untranslated).",
                 "For exceptions, the effect field is used as a mark in ASS. SRT does not provide mechanisms for this and will fail to import (correctly).",
                 "For block splits, the mark is 'Split'. Either on EXTRANOUS (the split off) lines, OR on ALL lines, with either: empty lines/comments between 'groups', or with a NUMBER added: 'Split00', 'Split01', ...",
                 "For text effects that span multiple lines, ADDITIONAL lines are marked with 'Effect'")

TARGET_FILE = args.getArg("-src", None)
SUBTITLE_FILE = args.getArg("-sub", None)

OFFSET = args.getArg("-off", -1)
if type(OFFSET) is not int:
    OFFSET = int(OFFSET)
NAME_PREFIX = args.getArg("-npre", False)
AUTO = True
if OFFSET > -1: AUTO = False

# Helpers
def specialProcessing(text: str):
    if NAME_PREFIX:
        text = re.sub(r".+: (.+)", r"\1", text)
    return text

def duplicateSub(textList, idx, newText):
    # duplicate text and choices
    textList[idx]['enText'] = textList[idx-1]['enText']
    if "choices" in textList[idx-1]:
        for c, choice in enumerate(textList[idx-1]["choices"]):
            textList[idx]['choices'][c]['enText'] = choice['enText']

    # Add sub text to matching (next) block and return it as new pos
    if newText:
        if idx < len(textList) - 1:
            idx += 1
            textList[idx]['enText'] = specialProcessing(newText)
        else:
            print("Attempted to duplicate beyond last line of file. Subtitle file does not match?")
    return idx

def isDuplicateBlock(tlFile: common.TranslationFile, textList, idx):
    if tlFile.getType() != "story": return False
    prevName = textList[idx - 1]['jpName']
    curName = textList[idx]['jpName']
    return curName in ["<username>", "", "モノローグ"] and curName == prevName and ratio(textList[idx]['jpText'], textList[idx-1]['jpText']) > 0.6

# ASS
def cleanLine(text):
    text = text.replace("\\N", "\n")
    text = re.sub(r"\{.+?\}", "", text)
    return text

def assPreFilter(doc):
    filtered = list()
    inSplit = None
    lastSplit = None
    for line in doc.events:
        if re.search("MainText|Default|Button", line.style, re.IGNORECASE) and line.name != "Nameplate":
            if re.match("split", line.effect, re.IGNORECASE):
                if inSplit and line.effect[-2:] == lastSplit:
                    filtered[-1].text += f"\n{cleanLine(line.text)}"
                    continue
                lastSplit = line.effect[-2:]
                inSplit = True
            else:
                inSplit = False

            line.text = cleanLine(line.text)
            filtered.append(line)
    return filtered

def processASS():
    with open(SUBTITLE_FILE, encoding='utf_8_sig') as f:
        doc = ass.parse(f)
    processSubs(assPreFilter(doc), "ass")

# SRT
def processSRT():
    with open(SUBTITLE_FILE, encoding='utf_8') as f:
        doc = list(srt.parse(f))
    processSubs(doc, "srt")

def processSubs(subs, format):
    tlFile = common.TranslationFile(TARGET_FILE)
    storyType = tlFile.getType()
    textList = tlFile.getTextBlocks()
    idx = 0
    lastChoice = 0
    if not AUTO and len(subs) != len(textList) - OFFSET:
        print(f"Block lengths don't match: Sub: {len(subs)} to Src: {len(textList)} - {OFFSET}")
        raise SystemExit
        
    for line in subs:
        subText = line.content if format == "srt" else line.text
        if AUTO and idx == len(textList):
            print(f"File filled at idx {idx}. Next file part starts at: {subText}")
            break
        # skip title logo on events
        if textList[idx]['jpText'].startswith("イベントタイトルロゴ表示"):
            idx += 1
        # races can have "choices" but their format is different because there is always only 1 and can be treated as normal text
        if storyType == "story":
            if (subText.startswith(">") or subText.startswith("Trainer:") or 
            (format == "ass" and (line.effect == "choice" or line.style.endswith("Button")))):
                if not "choices" in textList[idx-1]:
                    print(f"Found assumed choice subtitle, but no matching choice found at block {textList[idx-1]['blockIdx']}, skipping...")
                    continue
                for entry in textList[idx-1]["choices"]:
                    entry['enText'] = specialProcessing(subText)
                    lastChoice = idx
                continue # don't increment idx
            elif idx > 0 and "choices" in textList[idx-1] and idx - lastChoice > 0:
                print(f"Missing choice subtitle at block {textList[idx-1]['blockIdx']}")
        if isDuplicateBlock(tlFile, textList, idx):
            print(f"Found gender dupe at block {textList[idx]['blockIdx']}, duplicating.")
            idx = duplicateSub(textList, idx, subText) + 1
            continue
        else:
            if len(subText) == 0:
                print(f"Untranslated line at {textList[idx]['blockIdx']}")
            else:
                textList[idx]['enText'] = specialProcessing(subText)
        idx += 1
    # check niche case of duplicate last line (idx is already increased)
    if idx < len(textList):
        if isDuplicateBlock(tlFile, textList, idx):
            print("Last line is duplicate! (check correctness)")
            duplicateSub(textList, idx, None)
        else:
            print(f"Lacking {len(textList) - idx} subtitle(s).")

    tlFile.save()

def main():
    if not TARGET_FILE and not SUBTITLE_FILE:
        print("No files to process given")
        raise SystemExit

    type = SUBTITLE_FILE[-3:]
    if type == "ass":
        processASS()
    elif type == "srt":
        processSRT()
    else:
        print("Unsupported subtitle format.")
        raise NotImplementedError

    print("Successfully transferred.")

main()