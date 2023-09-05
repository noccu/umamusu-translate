import shutil
from argparse import SUPPRESS
from concurrent.futures import Future, ThreadPoolExecutor
from os.path import isfile, join, realpath

import requests

import common.constants as const
from common import patch, logger
from common.types import TranslationFile, GameBundle

HOSTNAME = "https://prd-storage-umamusume.akamaized.net/dl/resources"
GENERIC_ENDPOINT = HOSTNAME + "/Generic/{0:.2}/{0}"
ASSET_ENDPOINT = HOSTNAME + "/Windows/assetbundles/{0:.2}/{0}"
MANIFEST_ENDPOINT = HOSTNAME + "/Manifest/{0:.2}/{0}"


def download(file, t: str = "story"):
    if t in ("sound", "movie", "font"):
        url = GENERIC_ENDPOINT.format(file)
    elif t.startswith("manifest"):
        url = MANIFEST_ENDPOINT.format(file)
    else:
        url = ASSET_ENDPOINT.format(file)
    logger.conditionalDetail(f"Downloading {file}", f"Downloading {file} from {url}", logger.INFO)
    return requests.get(url)


def save(bundle: GameBundle, args):
    localFile = join(args.backup_dir, bundle.bundleName)

    if not args.forcedl and isfile(localFile):
        logger.conditionalDetail(
            f"Copying {bundle.bundleName}",
            f"Copying {bundle.bundleName} from {localFile}",
            logger.INFO,
        )
        shutil.copyfile(localFile, bundle.bundlePath)
    else:
        data = download(bundle.bundleName, bundle.bundleType)
        if data.status_code == 200:
            with open(bundle.bundlePath, "wb") as f:
                f.write(data.content)
        else:
            logger.error(f"Error downloading file {bundle.bundleName}")
            logger.debug(f"Status: {data.status_code}\nContent:{data.text}")
            return 0
    return 1


def restore(file, args):
    if args.src:
        bundle = GameBundle.fromName(args.src, load=False, bType=args.srctype)
    else:
        file = TranslationFile(file, readOnly=True)
        bundle = GameBundle.fromName(file.bundle, load=False, bType=file.type)
    if not args.force_restore and bundle.exists and not bundle.isPatched:
        logger.info(f"Bundle {bundle.bundleName} not patched, skipping.")
        return 0
    logger.debug(f"Saving file to {bundle.bundlePath}")
    return save(bundle, args)


def parseArgs(args=None):
    ap = patch.Args("Restore game files from backup or CDN download")
    ap.add_argument(
        "--forcedl", action="store_true", help="Force new file dl over copying from local backup"
    )
    ap.add_argument("-bdir", "--backup-dir", default=realpath("dump"), help="Local backup dir")
    ap.add_argument("-src", help="Target filename/bundle hash")
    ap.add_argument(
        "-srctype", default="story", help="Type of src arg. This is the m column in the meta file"
    )
    ap.add_argument("-dst", help=SUPPRESS)
    ap.add_argument(
        "--uninstall",
        action="store_true",
        help="Restore all files back to originals (may download)",
    )
    ap.add_argument(
        "-F", "--force-restore", action="store_true", help="Ignore checks and always restore files"
    )
    args = ap.parse_args(args)
    return args


def main(args: patch.Args = None):
    args = args or parseArgs(args)
    if args.src:
        restore(args.src, args)
    else:
        processed = 0

        def update(f: Future):
            nonlocal processed
            processed += f.result()

        with ThreadPoolExecutor() as pool:
            for type in const.TARGET_TYPES if args.uninstall else (args.type,):
                files = patch.searchFiles(type, args.group, args.id, args.idx, changed=args.changed)
                for file in files:
                    pool.submit(restore, file, args).add_done_callback(update)
        print(f"Restored {processed} files.")

    if args.uninstall:
        from pathlib import Path

        from common.patch import getUmaInstallDir

        uma = getUmaInstallDir()
        if uma:
            (uma / "version.dll").unlink(missing_ok=True)
            (uma / "uxtheme.dll").unlink(missing_ok=True)
        Path(const.GAME_MASTER_FILE).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
