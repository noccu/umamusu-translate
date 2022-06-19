import common
from common import TranslationFile
import re
from math import ceil
import helpers

REPLACEMENT_DATA = None
LL_CACHE = None, None
SUPPORTED_TAGS = ["i", "b", "color", "size"]
RE_TAGS = re.compile(r"(?<!\\)</?" + f"(?:{'|'.join(SUPPORTED_TAGS)})" + r"(?:=[^>]+)?(?<!\\)>")
RE_BREAK_WORDS = re.compile(r"<?/?([^ <>=]*)=?[^ <>]*[> ]{0,2}")  # yes we want to allow null matches


def processText(file: TranslationFile, text: str, opts: dict):
    if opts.get("redoNewlines"):
        text = cleannewLines(text)
    if opts.get("replaceMode"):
        text = replace(text, opts["replaceMode"])
    if opts.get("lineLength") != 0:
        text = adjustLength(file, text, opts)

    text = resizeText(file, text, force = opts.get("forceResize"))
    return text


# def _cleanRep(m):
#     # don't add spaces after opening tags
#     if m[1]:
#         x = m[1]
#         if m[1][1] == "/":
#             x += " "
#     else: return " "


def cleannewLines(text: str):
    # return re.sub(f"({RE_TAGS.pattern})?" + r" *(?:\\n|\r?\n) *", _cleanRep, text)
    return re.sub(r" *(?:\\n|\r?\n) *", " ", text)


def adjustLength(file: TranslationFile, text: str, opts, **overrides):
    # todo: Find better way to deal with options
    numLines: int = overrides.get("numLines", 0)
    targetLines: int = overrides.get("targetLines", opts.get("targetLines", 3))
    lineLen: int = overrides.get("lineLength", opts.get("lineLength", -1))
    if lineLen == -1: lineLen = calcLineLen(file, opts.get('verbose'))
    if lineLen == 0: return text  # auto mode can return 0
    pureText = RE_TAGS.sub("", text)

    if len(pureText) < lineLen:
        if opts.get("verbose"):
            print("Short text line, skipping: ", text)
        return text

    if numLines > 0:
        lineLen = ceil(len(pureText) / numLines)
    if lineLen > 0:
        # check if it's ok already
        lines = re.split(r"\r?\n|\\n", pureText)
        tooLong = [line for line in lines if len(line) > lineLen]
        if not tooLong and len(lines) <= targetLines:
            if opts.get("verbose"): print("Text passes length check, skipping: ", text)
            return text.replace("\n", "\\n") if file.escapeNewline else text  # I guess this ensures it's correct but should really be skipped

        # adjust if not
        text = cleannewLines(text)
        lines = [""]
        pureLen = [0]
        lastIsOpenTag = 0
        for m in RE_BREAK_WORDS.finditer(text):
            isTag = m.group(0).startswith("<") and m.group(1) and m.group(1) in SUPPORTED_TAGS
            if numLines > 0:  # allow one-word "overflow" in line split mode
                lineFits = pureLen[-1] < lineLen
            else:
                lineFits = pureLen[-1] + len(m.group(0)) - 2 < lineLen  # -2 = -1 for spaces (common), -1 for <= comparison
            if isTag or lineFits or len(m[0]) < 2 or len(lines[-1]) == 0:
                lines[-1] += m.group(0)
            else:
                if lines[-1][-1] not in (" ", ">"):
                    lines[-1] = lines[-1] + " "
                if lastIsOpenTag: # move tags to new line
                    lines.append(lines[-1][-lastIsOpenTag:].strip())
                    lines[-2] = lines[-2][:-lastIsOpenTag]
                    lines[-1] += m[0]
                else:
                    lines.append(m.group(0))
                pureLen.append(0)
            if not isTag:
                pureLen[-1] += len(m[0])
                lastIsOpenTag = 0
            elif m[0][1] != "/":
                lastIsOpenTag = m.end() - m.start()

        nLines = len(lines)
        if numLines < 1 and nLines > 1 and pureLen[-1] < lineLen / 3.25:
            linesStr = '\n\t'.join(lines)
            if opts.get("verbose"):
                print(f"Last line is short, balancing on line number:\n\t{linesStr}")
            return adjustLength(file, text, opts, numLines = nLines, lineLen = -2)

    if 0 < targetLines < len(lines):
        try:
            linesStr = '\n\t'.join(lines)
            print(f"Exceeded target lines ({targetLines} -> {len(lines)}) by {len(text) - lineLen * targetLines} in {file.name}:\n\t{linesStr}")
        except UnicodeEncodeError:
            print(f"Exceeded target lines ({targetLines} -> {len(lines)}) by {len(text) - lineLen * targetLines} in storyId {file.getStoryId()}: Lines not shown due to terminal/system codepage errors.")
    return getNewline(file).join(lines)


def resizeText(tlFile: TranslationFile, text: str, force=False):
    size = tlFile.data.get("textSize")
    if not size: return text
    if text.startswith("<s"):
        if force:
            text = re.sub(r"^<size=\d+>(.+?) *(?:\\+n)?</size>$", r"\1", text, flags=re.DOTALL)
        else:
            return text  # ignore already-sized textpy src\
    return f"<size={size}>{text}{getNewline(tlFile)}</size>"


def getNewline(tlFile: TranslationFile):
    return "\\n" if tlFile.escapeNewline else "\n"


def replace(text: str, mode):
    if mode == "none":
        return text

    global REPLACEMENT_DATA
    if REPLACEMENT_DATA is None:
        REPLACEMENT_DATA = helpers.readJson("src/data/replacer.json")
        for rep in REPLACEMENT_DATA:
            rep['re'] = re.compile(rep['re'], flags=re.IGNORECASE)
    for rep in REPLACEMENT_DATA:
        if mode == "limit" and "limit" in rep: continue
        if rep.get("disabled", False): continue
        text = rep['re'].sub(rep['repl'], text)
    return text


def main():
    ap = common.Args("Process text for linebreaks (game length limits), common errors, and standardized formatting",
                     types=common.SUPPORTED_TYPES)
    ap.add_argument("-src", help="Target Translation File, overwrites other file options")
    ap.add_argument("-V", "--verbose", action="store_true", help="Print additional info")
    # Roughly 42-46 for most training story dialogue, 63-65 for wide screen stories (events etc)
    # Through overflow (thanks anni update!) up to 4 work for landscape content,
    # and up to 5 for portrait (quite pushing it though)
    ap.add_argument("-ll", dest="lineLength", default=-1, type=int, help="Characters per line. 0: disable, -1: auto")
    ap.add_argument("-nl", dest="redoNewlines", action="store_true",
                    help="Remove existing newlines for complete reformatting")
    ap.add_argument("-rep", dest="replaceMode", choices=["all", "limit", "none"], default="limit",
                    help="Mode/aggressiveness of replacements")
    ap.add_argument("-fsize", "--force-resize", dest="forceResize", action="store_true",
                    help="Re-resize text when input already had size tags. (Still requires size key in tlfile)")
    # 3 is old max and visually ideal as intended by the game. Through overflow (thanks anni update!) up to 4 work for
    # landscape content, and up to 5 for portrait (quite pushing it though)
    ap.add_argument("-tl", dest="targetLines", default=3, type=int,
                    help="Target lines. Length adjustment skips input obeying -ll and not exceeding -tl")
    args = ap.parse_args()

    processFiles(args)


def processFiles(args):
    if args.src:
        files = [args.src]
    else:
        files = common.searchFiles(args.type, args.group, args.id, args.idx)
    print(f"Processing {len(files)} files...")
    if args.lineLength == -1: print(f"Automatically setting line length based on story type/id or file value")
    for file in files:
        file = common.TranslationFile(file)

        for block in file.genTextContainers():
            if "enText" in block and len(block['enText']) != 0 and "skip" not in block:
                block['enText'] = processText(file, block['enText'], vars(args))
        file.save()
    print("Files processed.")


def calcLineLen(file: TranslationFile, verbose):
    global LL_CACHE
    if LL_CACHE[0] is file:  # should be same as id() -> fast
        return LL_CACHE[1]

    lineLength = file.data.get('lineLength')
    if lineLength is None:
        if (file.type in ("lyrics", "race")
            or (file.type == "story"
                and common.parseStoryId(file.type, file.getStoryId(), fromPath=False)[0] in ("02", "04", "09"))):
            lineLength = 65
        else:
            lineLength = 45
    LL_CACHE = file, lineLength
    if verbose:
        print(f"Line length set to {lineLength} for {file.name}")
    return lineLength


if __name__ == '__main__':
    main()
