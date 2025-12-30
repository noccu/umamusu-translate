import re
from math import ceil

from common import utils, patch, logger
from common.constants import SUPPORTED_TYPES
from common.types import StoryId, TranslationFile

REPLACEMENT_DATA = None
LL_CACHE = None, None
SUPPORTED_TAGS = ["i", "b", "color", "size"]
RE_TAGS = re.compile(r"(?<!\\)</?" + f"(?:{'|'.join(SUPPORTED_TAGS)})" + r"(?:=[^>]+)?(?<!\\)>")
RE_BREAK_WORDS = re.compile(r"<?/?([^ <>=]*)=?[^ <>]*[> ]{0,2}")  # allow null matches


def processText(file: TranslationFile, text: str, opts: dict):
    if opts.get("redoNewlines"):
        text = cleannewLines(text)
    if opts.get("replaceMode"):
        text = replace(text, opts["replaceMode"], opts.get("extrarep", False))
    if opts.get("lineLength") is not None and opts.get("lineLength") != 0:
        text = adjustLength(file, text, opts)

    text = resizeText(file, text, force=opts.get("forceResize"))
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
    if opts.get("exclusiveNewlines") and re.match("\n|\\n", text):
        return
    # todo: Find better way to deal with options
    numLines: int = overrides.get("numLines", 0)
    targetLines: int = overrides.get("targetLines", opts.get("targetLines", 3))
    lineLen: int = overrides.get("lineLength", opts.get("lineLength", -1))
    if lineLen == -1:
        lineLen = calcLineLen(file)
        logger.debug(f"Line length set to {lineLen} for {file.name}")
    if lineLen == 0:
        return text  # auto mode can return 0
    # Calculate an estimation of raw characters from size-based length
    # Adjusted by font size
    fontsize = file.data.get("textSize", 24)
    sizeMod = 1.07 * (fontsize / 24) ** 0.6
    lineLen = int((lineLen * (1.135 * lineLen**0.05) + 1) * sizeMod)
    pureText = RE_TAGS.sub("", text)

    if len(pureText) < lineLen:
        logger.info(f"Short text line, skipping: {text}")
        return text

    if numLines > 0:
        lineLen = ceil(len(pureText) / numLines)
    if lineLen > 0:
        # check if it's ok already
        lines = re.split(r"\r?\n|\\n", pureText)
        tooLong = [line for line in lines if len(line) > lineLen]
        if not tooLong and len(lines) <= targetLines:
            logger.info(f"Text passes length check, skipping: {text}")
            # I guess this replace ensures it's correct but should really be skipped
            return text.replace("\n", "\\n") if file.escapeNewline else text

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
                # -2 = -1 for spaces (common), -1 for <= comparison
                lineFits = pureLen[-1] + len(m.group(0)) - 2 < lineLen
            if isTag or lineFits or len(m[0]) < 2 or len(lines[-1]) == 0:
                lines[-1] += m.group(0)
            else:
                if lines[-1][-1] not in (" ", ">"):
                    lines[-1] = lines[-1] + " "
                if lastIsOpenTag:  # move tags to new line
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
            logger.info(f"Last line is short, balancing on line number:\n\t" + "\n\t".join(lines))
            return adjustLength(file, text, opts, numLines=nLines, lineLen=-2)

    if 0 < targetLines < len(lines):
        try:
            linesStr = "\n\t".join(lines)
            print(
                f"Exceeded target lines ({targetLines} -> {len(lines)}) "
                f"by {len(text) - lineLen * targetLines} in {file.name}:\n\t{linesStr}"
            )
        except UnicodeEncodeError:
            print(
                f"Exceeded target lines ({targetLines} -> {len(lines)}) "
                f"by {len(text) - lineLen * targetLines} in storyId {file.getStoryId()}\n"
                "Lines and title not shown due to terminal/system codepage errors."
            )
    return getNewline(file).join(lines)


def resizeText(tlFile: TranslationFile, text: str, force=False):
    size = tlFile.data.get("textSize")
    if not size:
        return text
    if text.startswith("<s"):
        if force:
            text = re.sub(r"^<size=\d+>(.+?) *(?:\\+n)?</size>$", r"\1", text, flags=re.DOTALL)
        else:
            return text  # ignore already-sized textpy src\
    return f"<size={size}>{text} {getNewline(tlFile)}</size>"


def getNewline(tlFile: TranslationFile):
    return "\\n" if tlFile.escapeNewline else "\n"


def replace(text: str, mode, extra_rep=False):
    if mode == "none":
        return text

    global REPLACEMENT_DATA
    if REPLACEMENT_DATA is None:
        REPLACEMENT_DATA = utils.readJson("src/data/replacer.json")
        for rep in REPLACEMENT_DATA:
            rep["re"] = re.compile(rep["re"], flags=re.IGNORECASE)
    for rep in REPLACEMENT_DATA:
        if mode == "limit" and "limit" in rep:
            continue
        if rep.get("disabled", False):
            continue
        text = rep["re"].sub(rep["repl"], text)

    # - UmaTL standard -
    if extra_rep:
        # Fix inconsistent case in stutters.
        text = re.sub(
            r"([A-Z])(?:-\1)+",
            lambda m: "-".join(m[1] * int(len(m[0][1:]) / 2 + 1)),
            text,
            flags=re.IGNORECASE,
        )

    return text


def calcLineLen(file: TranslationFile):
    global LL_CACHE
    if LL_CACHE[0] is file:  # should be same as id() -> fast
        return LL_CACHE[1]

    lineLength = file.data.get("lineLength")
    if lineLength in (None, -1, 0):
        if file.type == "lyrics":
            lineLength = 67
        elif file.type == "preview":
            lineLength = 41
        elif (file.type == "race") or (
            file.type == "story"
            and StoryId.parse(file.type, file.getStoryId()).group in ("02", "04", "09", "10", "13")
        ):
            lineLength = 48
        elif file.file.parent.name == "character_system_text":
            lineLength = 25
        else:
            lineLength = 34
    LL_CACHE = file, lineLength
    return lineLength


def parseArgs(args=None):
    ap = patch.Args(
        "Process text for linebreaks (game length limits), common errors, and standardized formatting",
        types=SUPPORTED_TYPES,
    )
    ap.set_defaults(src=None)
    # Roughly 42-46 for most training story dialogue, 63-65 for wide screen stories (events etc)
    # Through overflow (thanks anni update!) up to 4 work for landscape content,
    # and up to 5 for portrait (quite pushing it though)
    ap.add_argument(
        "-ll",
        dest="lineLength",
        default=-1,
        type=int,
        help="Characters per line. 0: disable, -1: auto",
    )
    ap.add_argument(
        "-nl",
        dest="redoNewlines",
        action="store_true",
        help="Remove existing newlines for complete reformatting",
    )
    ap.add_argument(
        "-xnl",
        dest="exclusiveNewlines",
        action="store_true",
        help="Only add newlines to text without any yet.",
    )
    ap.add_argument(
        "-rep",
        dest="replaceMode",
        choices=["all", "limit", "none"],
        default="limit",
        help="Mode/aggressiveness of replacements",
    )
    ap.add_argument(
        "-extrarep",
        action="store_true",
        help="Do extra processing. For special cases, based on UmaTL standards.",
    )
    ap.add_argument(
        "-fsize",
        "--force-resize",
        dest="forceResize",
        action="store_true",
        help="Re-resize text when input already had size tags. (Still requires size key in tlfile)",
    )
    # 3 is old max and visually ideal as intended by the game.
    # Through overflow (thanks anni update!) up to 4 work for
    # landscape content, and up to 5 for portrait (quite pushing it though)
    ap.add_argument(
        "-tl",
        dest="targetLines",
        default=3,
        type=int,
        help="Target lines. Length adjustment skips input obeying -ll and not exceeding -tl",
    )
    args = ap.parse_args(args)

    if args.exclusiveNewlines and args.redoNewlines:
        logger.critical("Incompatible newline options: force all + exclusive add.")
        raise SystemExit

    return args


def main(args: patch.Args = None):
    args = args or parseArgs(args)
    if args.src:
        files = [args.src]
    else:
        files = patch.searchFiles(
            args.type, args.group, args.id, args.idx, targetSet=args.set, changed=args.changed
        )
    print(f"Processing {len(files)} files...")
    if args.lineLength == -1:
        logger.info("Automatically setting line length based on story type/id or file value")
    for file in files:
        file = TranslationFile(file)

        for block in file.genTextContainers():
            if "enText" in block and len(block["enText"]) != 0 and "skip" not in block:
                block["enText"] = processText(file, block["enText"], vars(args))
        file.save()
    print("Files processed.")


if __name__ == "__main__":
    main()
