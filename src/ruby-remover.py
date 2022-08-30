import common
import sqlite3
from types import SimpleNamespace

def removeRuby(args, db: sqlite3.Connection):
    storyId = f"{args.group}{args.id}{args.idx}"
    q = db.execute(f"select h, n from a where n like 'story/data/__/____/ast_ruby_{storyId}'")
    patched = total = 0
    dummytl = SimpleNamespace(data=dict())
    for bundle, path in q:
        bundle = common.GameBundle.fromName(bundle, load = False)
        bundle.readPatchState()
        if bundle.isPatched:
            storyId = "".join(common.parseStoryId("story", path))
            if args.verbose: print(f"Skipping {storyId} ({bundle.bundleName}): Already patched")
        else:
            bundle.load()
            tree = bundle.rootAsset.read_typetree()
            tree['DataArray'] = []
            bundle.rootAsset.save_typetree(tree)
            bundle.setPatchState(dummytl)
            bundle.save()
            patched += 1
        total += 1
    return patched, total

def main():
    ap = common.Args("Removes ruby data from assets")
    ap.add_argument("-dst", default=common.GAME_META_FILE, help="Path to master.mdb file")
    args = ap.parse_args()
    args.type = "story"
    args.group =args.group or "__"
    args.id = args.id or "____"
    args.idx = args.idx or "___"
    try:
        with sqlite3.connect(args.dst, isolation_level=None) as db:
            db.execute("PRAGMA journal_mode = MEMORY;")
            p, t = removeRuby(args, db)
            print(f"Processed {p}/{t} files")
    finally:
        db.close()

if __name__ == '__main__':
    main()