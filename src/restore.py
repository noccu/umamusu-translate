import requests
import common
from common import GAME_ASSET_ROOT
from os.path import join, realpath, isfile
import shutil

# Globals & Parameter parsing
HOSTNAME = 'https://prd-storage-umamusume.akamaized.net/dl/resources'
ASSETS_ENDPOINT = HOSTNAME + '/Windows/assetbundles/{0:.2}/{0}'
LOCAL_DUMP_DIR = realpath("dump") # A folder where original files were copied to before. (and not modified)

args = common.Args().parse()
if args.getArg("-h"):
    common.usage("[-g <group>] [-id <id>] [-src <file>]",
                 "-src overwrites other options")

TARGET_TYPE = args.getArg("-t", "story").lower()
TARGET_GROUP = args.getArg("-g", False)
TARGET_ID = args.getArg("-id", False)
TARGET_IDX = args.getArg("-idx", False)
TARGET_FILE = args.getArg("-src", False)
FORCE_DL = args.getArg("-F", False)


def download(file):
    url = ASSETS_ENDPOINT.format(file)
    print(f"Downloading {file} from {url}")
    return requests.get(url)

def save(fileName):
    dstPath = join(GAME_ASSET_ROOT, fileName[:2], fileName)
    localFile = join(LOCAL_DUMP_DIR, fileName)

    print(f"Saving file to {dstPath}")
    if not FORCE_DL and isfile(localFile):
        print (f"Copying file from {localFile}")
        shutil.copyfile(localFile, dstPath)
    else:
        data = download(fileName)
        if data.status_code == 200:
            with open(dstPath, "wb") as f:
                f.write(data.content)
        else:
            print(f"Error downloading file {fileName}")

#* Main
if TARGET_FILE:
    save(TARGET_FILE)
else:
    files = common.searchFiles(TARGET_TYPE, TARGET_GROUP, TARGET_ID, TARGET_IDX)
    for file in files:
        file = common.TranslationFile(file)
        save(file.bundle)
