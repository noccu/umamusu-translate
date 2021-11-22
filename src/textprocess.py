import common
import re

args = common.Args().parse()
if args.getArg("-h"):
    common.usage("[-g <group>] [-id <id>] [-src <json file>] [-ll <line length>]",
                 "At least 1 arg is required.",
                 "-src overwrites other options.")

TARGET_GROUP = args.getArg("-g", None)
TARGET_ID = args.getArg("-id", None)
TARGET_FILE = args.getArg("-src", None)
LINE_LENGTH = args.getArg("-ll", 63)

if not TARGET_FILE and not TARGET_GROUP and not TARGET_ID: raise SystemExit("At least 1 arg is required.")

def process(text: str, options: dict):
    if "noNewlines" in options:
        text = cleannewLines(text)
    if "lineLen" in options:
        text = adjustLength(text, options["lineLen"] or LINE_LENGTH)
    return text

def cleannewLines(text: str):
    return re.sub("\r?\n", " ", text)

def adjustLength(text: str, lineLen: int = 0, numLines: int = 0, targetLines: int = 0):
    if len(text) < lineLen:
        print("Short text line, skipping: ", text, "")
        return text


    if lineLen > 0:
        #check if it's ok already
        lines = text.splitlines()
        tooLong = [line for line in lines if len(line) > lineLen]
        if not tooLong:
            print("Text passes length check, skipping: ", text, "")
            return text

        #adjust if not
        text = cleannewLines(text)
        # python regexes kinda suck
        lines = re.findall(f"(?:(?<= )|(?<=^)).{{1,{lineLen}}}(?= |$)|(?<= ).+$", text)
        nLines = len(lines)
        if nLines > 1 and len(lines[-1]) < min(lineLen, len(text)) / nLines:
            print("Last line is short, balancing on line number: ", lines, "")
            return adjustLength(text, numLines = nLines)

    elif numLines > 0:
        lineLen = len(text) / numLines
        lines = re.findall(f"(?:(?<= )|(?<=^)).{{{lineLen},}}?(?= |$)|(?:(?<= )|(?<=^)).+$", text)

    if targetLines > 0 and len(lines) > targetLines:
        print("Exceeded target lines at:", lines)
    return "\n".join(lines)

def main():
    if TARGET_FILE:
        files = [TARGET_FILE]
    else:
        files = common.searchFiles(TARGET_GROUP, TARGET_ID)

    print(f"Processing {len(files)} files...")
    for file in files:
        file = common.TranslationFile(file)
        for block in file.getTextBlocks():
            if not "enText" in block or len(block['enText']) == 0: continue
            block['enText'] = process(block['enText'], {"lineLen": LINE_LENGTH})
        file.save()
    print("Files processed.")

if __name__ == '__main__':
    main()