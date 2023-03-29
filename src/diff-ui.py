import helpers
from common import Args

uiFile = "translations/localify/ui.json"
diffFile = "dump-diff.json"

def parseArgs():
    args = Args("Diff UI files")
    args.add_argument("-tl", action="store_true", help="Also check translations file as old values")
    args.add_argument("-r", "--reverse", action="store_true", help="Import translated values from diff into ui.json")
    return args.parse_args()

def diffUi(args):
    oldFile = helpers.readJson("src/data/static_dump_old.json")
    newFile = helpers.readJson("src/data/static_dump.json")
    oldValues = oldFile.values()

    if args.tl:
        uiData = helpers.readJson(uiFile)
        uiValues = uiData.keys()

    dump = dict()
    for v in newFile.values():
        if v not in oldValues:
            if args.tl and v in uiValues: continue
            dump[v] = ""
    helpers.writeJson(diffFile, dump)

def addNew():
    diffData = helpers.readJson(diffFile)
    uiData = helpers.readJson(uiFile)
    for k, v in list(diffData.items()):
        if v != "" and k not in uiData:
            uiData[k] = v
            del diffData[k]
    helpers.writeJson(uiFile, uiData)
    helpers.writeJson(diffFile, diffData)


def main():
    args = parseArgs()
    if args.reverse:
        addNew()
    else:
        diffUi(args)

if __name__ == '__main__':
    main()