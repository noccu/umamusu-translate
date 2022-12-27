import requests
import common
from common import GameBundle
from os.path import join, realpath, isfile
import shutil
from argparse import SUPPRESS
from concurrent.futures import Future, ThreadPoolExecutor

HOSTNAME = 'https://prd-storage-umamusume.akamaized.net/dl/resources'
GENERIC_ENDPOINT = HOSTNAME + "/Generic/{0:.2}/{0}"
ASSET_ENDPOINT = HOSTNAME + "/Windows/assetbundles/{0:.2}/{0}"
MANIFEST_ENDPOINT = HOSTNAME + "/Manifest/{0:.2}/{0}"


def download(file, t:str = "story", verbose = False):
    if t in ('sound', 'movie', 'font'):
        endpoint = GENERIC_ENDPOINT
    elif t.startswith('manifest'):
        endpoint = MANIFEST_ENDPOINT
    else:
        endpoint = ASSET_ENDPOINT
    url = endpoint.format(file)
    if verbose:
        print(f"Downloading {file} from {url}")
    else:
        print(f"Downloading {file}")
    return requests.get(url)


def save(bundle:GameBundle, args):
    localFile = join(args.backup_dir, bundle.bundleName)

    if not args.forcedl and isfile(localFile):
        if args.verbose:
            print(f"Copying file from {localFile}")
        else:
            print(f"Copying {bundle.bundleName}")
        shutil.copyfile(localFile, bundle.bundlePath)
    else:
        data = download(bundle.bundleName, bundle.bundleType, args.verbose)
        if data.status_code == 200:
            with open(bundle.bundlePath, "wb") as f:
                f.write(data.content)
        else:
            print(f"Error downloading file {bundle.bundleName}")
            if args.verbose: print(f"Status: {data.status_code}\nContent:{data.text}")
            return 0
    return 1

def restore(file, args):
    if args.src:
        bundle = GameBundle.fromName(args.src, load=False)
        bundle.bundleType = args.srctype
    else:
        file = common.TranslationFile(file)
        bundle = GameBundle.fromName(file.bundle, load=False)
        bundle.readPatchState()
        if not args.force_restore and bundle.exists and not bundle.isPatched:
            print(f"Bundle {bundle.bundleName} not patched, skipping.")
            return 0

    if args.verbose: print(f"Saving file to {bundle.bundlePath}")
    return save(bundle, args)

def parseArgs(src = None):
    ap = common.Args("Restore game files from backup or CDN download")
    ap.add_argument("--forcedl", action="store_true", help="Force new file dl over copying from local backup")
    ap.add_argument("-bdir", "--backup-dir", default=realpath("dump"), help="Local backup dir")
    ap.add_argument("-src", help="Target filename/bundle hash")
    ap.add_argument("-srctype", default="story", help="Type of src arg. This is the m column in the meta file")
    ap.add_argument("-dst", help=SUPPRESS)
    ap.add_argument("--uninstall", action="store_true", help="Restore all files back to originals (may download)")
    ap.add_argument("-F", "--force-restore", action="store_true", help="Ignore checks and always restore files")
    args = ap.parse_args(src)
    return args

def main():
    args = parseArgs()
    if args.src:
        restore(args.src, args)
    else:
        processed = 0
        def update(f: Future):
            nonlocal processed
            processed += f.result()

        with ThreadPoolExecutor() as pool:
            for type in common.TARGET_TYPES if args.uninstall else (args.type,):
                files = common.searchFiles(type, args.group, args.id, args.idx, changed = args.changed)
                for file in files:
                    pool.submit(restore, file, args).add_done_callback(update)
        print(f"Restored {processed} files.")

    if args.uninstall:
        from helpers import getUmaInstallDir
        from pathlib import Path
        uma = getUmaInstallDir()
        if uma:
            (uma / "version.dll").unlink(missing_ok=True)
            (uma / "uxtheme.dll").unlink(missing_ok=True)
        Path(common.GAME_MASTER_FILE).unlink(missing_ok=True)


if __name__ == '__main__':
    main()
