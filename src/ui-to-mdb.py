import common
import helpers

def tlgToMdb(file):
    uiFile = "translations/localify/ui.json"
    uiData = helpers.readJson(uiFile)
    if file:
        files = (common.TranslationFile(file, load=False),)
    else:
        files = [common.TranslationFile(p, load=False) for p in common.searchFiles("mdb", None, None)]
    for mdbFile in files:
        # if mdbFile.file.parent != "mdb": continue # ignore subdirs
        mdbFile.reload()
        changed = False
        for jp, en in mdbFile.textBlocks.items():
            enResult = uiData.get(jp)
            if enResult is not None:
                jpLookup = jp
            else:
                jpLookup = jp.replace("\\\\n", "\n") if mdbFile.escapeNewline else jp.replace("\r\n", "\n")
                enResult = uiData.get(jpLookup)
                if enResult is None: continue

            if en and enResult: 
                r = input(f"Duplicate for \"{jp}\"\n[UI] {enResult}\n[MDB ({mdbFile.name})] {en}\nChoose to use (ui, mdb, rep, x, stop): ")
                if r == "ui":
                    mdbFile.textBlocks[jpLookup] = enResult
                    del uiData[jpLookup]
                    changed = True
                elif r == "mdb":
                    del uiData[jpLookup]
                elif r == "rep":
                    r = input("Replace with: ")
                    mdbFile.textBlocks[jpLookup] = r
                    changed = True
                    del uiData[jpLookup]
                elif r == "stop":
                    helpers.writeJson(uiFile, uiData)
                    if changed:
                        mdbFile.save()
                    print("Progress saved, stopping.")
                    return
            elif enResult:
                mdbFile.textBlocks[jpLookup] = enResult
                del uiData[jpLookup]
                changed = True
            elif en:
                del uiData[jpLookup]
        if changed:
            mdbFile.save()
    helpers.writeJson(uiFile, uiData)

def main():
    args = common.Args("Extract strings from TLG's UI -> MDB, or between MDB files for splitting", defaultArgs=False)
    args.add_argument("-f", "-file", dest="file", help="The MDB file to check")
    args.add_argument("-mdb", help="Split MDB mode", action="store_true")
    args = args.parse_args()

    if args.mdb:
        raise NotImplementedError
    
    tlgToMdb(args.file)

if __name__ == '__main__':
    main()