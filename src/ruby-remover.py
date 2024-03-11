import common
import sqlite3
from types import SimpleNamespace


def removeRuby(args, db: sqlite3.Connection):
    storyId = common.StoryId.queryfy(
        common.StoryId(args.type, args.set, args.group, args.id, args.idx)
    )
    del storyId.set
    del storyId.type

    q = db.execute(f"select h, n from a where n like 'story/data/__/____/ast_ruby_{storyId}'")
    patched = total = 0
    dummytl = SimpleNamespace(data=dict())
    for bundle, path in q:
        bundle = common.GameBundle.fromName(bundle, load=False)
        if bundle.isPatched:
            if args.verbose:
                print(
                    f"Skipping {common.StoryId.parseFromPath(path)} ({bundle.bundleName}): Already patched"
                )
        else:
            bundle.load()
            tree = bundle.rootAsset.read_typetree()
            tree["DataArray"] = []
            bundle.rootAsset.save_typetree(tree)
            bundle.markPatched(dummytl)
            bundle.save()
            patched += 1
        total += 1
    return patched, total


def main():
    ap = common.Args("Removes ruby data from assets")
    ap.add_argument("-dst", default=common.GAME_META_FILE, help="Path to master.mdb file")
    args = ap.parse_args()
    args.type = "story"
    try:
        with sqlite3.connect(args.dst, isolation_level=None) as db:
            db.execute("PRAGMA journal_mode = MEMORY;")
            p, t = removeRuby(args, db)
            print(f"Processed {p}/{t} files")
    finally:
        db.close()


if __name__ == "__main__":
    main()
