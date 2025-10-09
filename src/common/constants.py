from os import environ, name as osname
from pathlib import Path

IS_WIN = osname == "nt"
DMM_CONFIG = Path(environ["APPDATA"], "dmmgameplayer5", "dmmgame.cnf") if IS_WIN else None

if IS_WIN:
    GAME_ROOT = environ.get("UMA_DATA_DIR")
    if GAME_ROOT:
        GAME_ROOT = Path(GAME_ROOT)
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
DB_KEY = "9c2bab97bcf8c0c4f1a9ea7881a213f6c9ebf9d8d4c6a8e43ce5a259bde7e9fd"
BUNDLE_BASE_KEY = "532b4631e4a7b9473e7cfb"

def set_meta(path: str | Path):
    global GAME_META_FILE
    GAME_META_FILE = Path(path)
