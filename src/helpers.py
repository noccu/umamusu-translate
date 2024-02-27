from typing import Optional, Union
import json
from pathlib import Path
from os import PathLike, environ, name as osname

import regex

IS_WIN = osname == "nt"
DMM_CONFIG = Path(environ["APPDATA"]) / "dmmgameplayer5" / "dmmgame.cnf" if IS_WIN else None
__GAME_INSTALL_DIR = False
__IS_USING_TLG = None


def readJson(file: PathLike) -> Union[dict, list]:
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)


def writeJson(file: PathLike, data, indent=4):
    file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, "w", encoding="utf8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, default=_to_json)


def _to_json(o):
    try:
        return o.__json__()
    except Exception:
        raise TypeError


def mkdir(path, parents=True, exists=True):
    Path(path).mkdir(parents=parents, exist_ok=exists)


def isParseableInt(x):
    try:
        int(x)
        return True
    except ValueError:
        return False


def isJapanese(text):
    # Should be cached according to docs
    return regex.search(
        r"[\p{scx=Katakana}\p{scx=Hiragana}\p{Han}\p{InHalfwidth_and_Fullwidth_Forms}\p{General_Punctuation}]{3,}",
        text,
    )


def isEnglish(text):
    return regex.fullmatch(
        r"[^\p{scx=Katakana}\p{scx=Hiragana}\p{Han}\p{InHalfwidth_and_Fullwidth_Forms}。]+",
        text,
    )


def getUmaInstallDir() -> Optional[Path]:
    """Return the path to the directory umamusume.exe was installed in, or None if it can't be found."""
    global __GAME_INSTALL_DIR
    if __GAME_INSTALL_DIR is not False:
        return __GAME_INSTALL_DIR
    __GAME_INSTALL_DIR = None
    try:
        with open(DMM_CONFIG, encoding="utf-8") as f:
            dmm_um_config = next(
                (game for game in json.load(f)["contents"] if game["productId"] == "umamusume"),
                None,
            )
            if dmm_um_config is not None:
                __GAME_INSTALL_DIR = Path(dmm_um_config["detail"]["path"])
    except FileNotFoundError:
        # Older DMM installs might not have the DMM config file,
        # if it wasn't found try an old registry check approach
        if IS_WIN:
            import winreg

            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\WOW6432Node\DMM GAMES\Launcher\Content\umamusume",
                ) as k:
                    __GAME_INSTALL_DIR = Path(winreg.QueryValueEx(k, "Path")[0])
            except OSError:
                pass
    return __GAME_INSTALL_DIR


def isUsingTLG() -> bool:
    global __IS_USING_TLG
    if __IS_USING_TLG is not None:
        return __IS_USING_TLG
    __IS_USING_TLG = (getUmaInstallDir() / "config.json").exists()
    return __IS_USING_TLG


def sanitizeFilename(fn: str):
    """Remove invalid path chars (win)"""
    delSet = {34, 42, 47, 58, 60, 62, 63, 92, 124}
    sanitizedName = ""
    for c in fn:
        cp = ord(c)
        if cp > 31 and cp not in delSet:
            sanitizedName += c
    return sanitizedName
