from os import environ, name as osname, path
from pathlib import Path

IS_WIN = osname == "nt"
DMM_CONFIG = Path(environ["APPDATA"]) / "dmmgameplayer5" / "dmmgame.cnf" if IS_WIN else None

if IS_WIN:
    GAME_ROOT = path.realpath(path.join(environ["LOCALAPPDATA"], "../LocalLow/Cygames/umamusume/"))
    GAME_ASSET_ROOT = path.join(GAME_ROOT, "dat")
    GAME_META_FILE = path.join(GAME_ROOT, "meta")
    GAME_MASTER_FILE = path.join(GAME_ROOT, "master", "master.mdb")
else:
    GAME_ROOT = GAME_ASSET_ROOT = GAME_META_FILE = GAME_MASTER_FILE = None
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
