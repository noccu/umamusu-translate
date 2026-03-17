from os import environ, name as osname
from pathlib import Path

IS_WIN = osname == "nt"
DMM_CONFIG = Path(environ["APPDATA"], "dmmgameplayer5", "dmmgame.cnf") if IS_WIN else None

if IS_WIN:
    if custom_root:= environ.get("UMA_DATA_DIR"):
        GAME_ROOT = Path(custom_root)
    else:
        GAME_ROOT = Path(environ["LOCALAPPDATA"], "..", "LocalLow", "Cygames", "umamusume").resolve()
    GAME_ASSET_ROOT = GAME_ROOT.joinpath("dat")
    GAME_META_FILE = GAME_ROOT.joinpath("meta")
    GAME_MASTER_FILE = GAME_ROOT.joinpath("master", "master.mdb")
else:
    _none: Path = None  # Fuckery to gaslight IDE into common scenario
    GAME_ROOT = GAME_ASSET_ROOT = GAME_META_FILE = GAME_MASTER_FILE = _none
SUPPORTED_TYPES = [
    "story",
    "home",
    "race",
    "lyrics",
    "preview",
    "ruby",
    "mdb",
]  # Update indexing on next line
TARGET_TYPES = SUPPORTED_TYPES[:-2]  # Classic asset types we want to read/write.
NAMES_BLACKLIST = ["<username>", "", "モノローグ", "合成音声"]  # Special-use game names, don't touch

TRANSLATION_FOLDER = Path("translations")

# Keys found by croakfang
DB_KEY_BASE = "F170CEA4DFCEA3E1A5D8C70BD1000000"
DB_KEY_RAW = "6D5B65336336632554712D73505363386D34377B356370233734532973433633"
DB_KEY = "9C2BAB97BCF8C0C4F1A9EA7881A213F6C9EBF9D8D4C6A8E43CE5A259BDE7E9FD"
BUNDLE_BASE_KEY = "532B4631E4A7B9473E7CFB"

def set_meta(path: str | Path):
    global GAME_META_FILE
    GAME_META_FILE = Path(path)
