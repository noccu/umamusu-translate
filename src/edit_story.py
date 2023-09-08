from argparse import SUPPRESS
from pathlib import Path
from common import constants, patch
from editor.app import Editor


def parseArgs(args=None):
    ap = patch.Args("Story editor", types=constants.SUPPORTED_TYPES)
    ap.add_argument("-src", type=Path)
    ap.add_argument("-dst", help=SUPPRESS)
    args = ap.parse_args(args)
    return args


def main(args=None):
    args = args or parseArgs(args)
    files = args.src or patch.searchFiles(
        args.type, args.group, args.id, args.idx, targetSet=args.set, changed=args.changed
    )
    if not files:
        print(("No files match given criteria"))
        return

    editor = Editor()
    editor.fileMan.importFiles(files)
    editor.start()


if __name__ == "__main__":
    main()
