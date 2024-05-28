from os import environ, name as osname
from pathlib import Path

IS_WIN = osname == "nt"
DMM_CONFIG = Path(environ["APPDATA"], "dmmgameplayer5", "dmmgame.cnf") if IS_WIN else None

if IS_WIN:
    GAME_ROOT = Path(environ["LOCALAPPDATA"], "..", "LocalLow", "Cygames", "umamusume").resolve()
    GAME_ASSET_ROOT = GAME_ROOT.joinpath("dat")
    GAME_META_FILE = GAME_ROOT.joinpath("meta")
    GAME_MASTER_FILE = GAME_ROOT.joinpath("master", "master.mdb")
else:
    _none:Path = None  # Fuckery to gaslight IDE into common scenario
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
NAMES_BLACKLIST = ["<username>", "", "モノローグ"]  # Special-use game names, don't touch

TRANSLATION_FOLDER = Path("translations")
