import ass
import srt
import common
import re
from Levenshtein import ratio
# from datetime import timedelta

args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-src <translation file> -sub <subtitle file> [-off offset -npre]",
                 "Imports translations from subtitle files. A few conventions are used.",
                 "Files are only modified if they can be assumed to merge properly. This check relies on text block lenghts."
                 "-offset is subtracted from the game file's text block length during this checking. (default 0)",
                 "Events for example, have an unshown title logo display line. This script skips those automatically but requires offset to be set for correct checking, as per above.",
                 "-npre flags text lines as prefixed by the char name",
                 "\n"
                 "Conventions are to have 1 subtitle line per game text block/screen. Include empty lines if needed (say, if you leave a line untranslated).",
                 "For exceptions, the effect field is used as a mark in ASS. SRT does not provide mechanisms for this and will fail to import (correctly).",
                 "For block splits, the mark is 'Split'. Either on EXTRANOUS (the split off) lines, OR on ALL lines, with either: empty lines/comments between 'groups', or with a NUMBER added: 'Split00', 'Split01', ...",
                 "For text effects that span multiple lines, ADDITIONAL lines are marked with 'Effect'")

TARGET_FILE = args.getArg("-src", None)
SUBTITLE_FILE = args.getArg("-sub", None)

OFFSET = args.getArg("-off", 0)
if type(OFFSET) is not int:
    OFFSET = int(OFFSET)
NAME_PREFIX = args.getArg("-npre", False)

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
    idx += 1
    textList[idx]['enText'] = specialProcessing(newText)
    return idx

def isDuplicateBlock(textList, idx):
    return textList[idx]['jpName'] == "<username>" and textList[idx - 1]['jpName'] == "<username>" and ratio(textList[idx]['jpText'], textList[idx-1]['jpText']) > 0.6

# ASS
def cleanLine(text):
    text = text.replace("\\N", "\n")
    text = re.sub(r"\{.+\}", "", text)
    return text

def processASS():
    with open(SUBTITLE_FILE, encoding='utf_8_sig') as f:
        doc = ass.parse(f)

    tlFile = common.TranslationFile(TARGET_FILE)
    textList = tlFile.getTextBlocks()

    filtered = list()
    inSplit = None
    lastSplit = None
    for line in doc.events:
        if "MainText" in line.style:
            cleanText = cleanLine(line.text)
            if line.effect.startswith("Split"):
                if inSplit and line.effect[-2:] == lastSplit:
                    filtered[-1] += f"\n{cleanText}"
                    continue
                lastSplit = line.effect[-2:]
                inSplit = True
            else:
                inSplit = False

            filtered.append(cleanText)

    if len(filtered) != len(textList) - OFFSET:
        print(f"Block lenghts don't match: {len(filtered)} to {len(textList)} - {OFFSET}")
        raise SystemExit

    idx = 0
    for line in filtered:
        # skip title logo on events
        if textList[idx]['jpText'].startswith("イベントタイトルロゴ表示"):
            idx += 1
        
        textList[idx]['enText'] = specialProcessing(line)
        if len(line) == 0:
            print(f"Untranslated line at {textList[idx]['blockIdx']}")

        idx += 1
    tlFile.save()

# SRT
def processSRT():
    tlFile = common.TranslationFile(TARGET_FILE)
    textList = tlFile.getTextBlocks()
    idx = 0
    with open(SUBTITLE_FILE, encoding='utf_8') as f:
        doc = list(srt.parse(f))

        if len(doc) != len(textList) - OFFSET:
            print(f"Block lenghts don't match: {len(doc)} to {len(textList)} - {OFFSET}")
            raise SystemExit
            
        for sub in doc:
            if not sub.content.startswith(">"):
                if sub.content.startswith("Trainer:"):
                    if not "choices" in textList[idx-1]:
                        print(f"Found assumed choice subtitle, but no matching choice found at block {textList[idx-1]['blockIdx']}, skipping...")
                        continue
                    for entry in textList[idx - 1]["choices"]:
                        entry['enText'] = specialProcessing(sub.content)
                    continue # don't increment idx
                if isDuplicateBlock(textList, idx):
                    print(f"Found gender dupe at block {textList[idx]['blockIdx']}, duplicating.")
                    idx = duplicateSub(textList, idx, sub.content) + 1
                    continue
                else:
                    textList[idx]['enText'] = specialProcessing(sub.content)
                idx += 1
                # print(sub.content)

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