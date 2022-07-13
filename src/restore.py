import requests
import common
from common import GAME_ASSET_ROOT, GameBundle
from os.path import join, realpath, isfile
import shutil
from argparse import SUPPRESS
from concurrent.futures import ThreadPoolExecutor

HOSTNAME = 'https://prd-storage-umamusume.akamaized.net/dl/resources'
ASSETS_ENDPOINT = HOSTNAME + '/Windows/assetbundles/{0:.2}/{0}'


def download(file):
    url = ASSETS_ENDPOINT.format(file)
    print(f"Downloading {file} from {url}")
    return requests.get(url)


def save(bundle:GameBundle, backupDir, forceDl=False):
    localFile = join(backupDir, bundle.bundleName)

    if not forceDl and isfile(localFile):
        print(f"Copying file from {localFile}")
        shutil.copyfile(localFile, bundle.bundlePath)
    else:
        data = download(bundle.bundleName)
        if data.status_code == 200:
            with open(bundle.bundlePath, "wb") as f:
                f.write(data.content)
        else:
            print(f"Error downloading file {bundle.bundleName}")

def restore(file, args):
    file = common.TranslationFile(file)
    bundle = GameBundle.fromName(file.bundle, load=False)
    bundle.readPatchState()
    if bundle.exists and not bundle.isPatched:
        print(f"Bundle {bundle.bundleName} not patched, skipping.")
        return

    save(bundle, args.backup_dir, args.forcedl)


def main():
    ap = common.Args("Restore game files from backup or CDN download")
    ap.add_argument("-F", "--forcedl", action="store_true", help="Force new file dl over copying from local backup")
    ap.add_argument("-bdir", "--backup-dir", default=realpath("dump"), help="Local backup dir")
    ap.add_argument("-src", help="Target filename/bundle hash")
    ap.add_argument("-dst", help=SUPPRESS)
    ap.add_argument("--uninstall", action="store_true", help="Restore all files back to originals (may download)")
    args = ap.parse_args()

    if args.src:
        save(args.src, args.backup_dir, args.forcedl)
    else:
        processed = 0
        with ThreadPoolExecutor() as pool:
            for type in common.TARGET_TYPES if args.uninstall else (args.type,):
                files = common.searchFiles(type, args.group, args.id, args.idx, changed = args.changed)
                processed += len(files)
                for file in files:
                    pool.submit(restore, file, args)
        print(f"Restored {processed} files.")

    if args.uninstall:
        from helpers import getUmaInstallDir
        from pathlib import Path
        uma = getUmaInstallDir()
        if uma:
            (uma / "version.dll").unlink(missing_ok=True)
            (uma / "uxtheme.dll").unlink(missing_ok=True)
        Path(common.GAME_ROOT, "master", "master.mdb").unlink(missing_ok=True)


if __name__ == '__main__':
    main()
