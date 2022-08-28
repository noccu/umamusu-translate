from typing import Optional, Union
import json
from pathlib import Path
from os import PathLike, environ, name as osname

import regex

DMM_CONFIG = Path(environ['APPDATA']) / "dmmgameplayer5" / "dmmgame.cnf"
IS_WIN = osname == "nt"
__GAME_INSTALL_DIR = False

def readJson(file: PathLike) -> Union[dict, list]:
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)


def writeJson(file: PathLike, data):
    file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, "w", encoding="utf8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=_to_json)


def _to_json(o):
    try:
        return o.__json__()
    except:
        raise TypeError


def findExisting(searchPath: PathLike, filePattern: str):
    searchPath = Path(searchPath)
    search = searchPath.glob(filePattern)
    for file in search:
        if file.is_file():
            return file
    return None


def isParseableInt(x):
    try:
        int(x)
        return True
    except ValueError:
        return False


def isJapanese(text):
    # Should be cached according to docs
    return regex.search(r"[\p{scx=Katakana}\p{scx=Hiragana}\p{Han}\p{InHalfwidth_and_Fullwidth_Forms}\p{General_Punctuation}]{3,}", text)


def isEnglish(text):
    return regex.fullmatch(r"[^\p{Katakana}\p{Hiragana}\p{Han}\p{InHalfwidth_and_Fullwidth_Forms}。]+", text)


def getUmaInstallDir() -> Optional[Path]:
    """Return the path to the directory umamusume.exe was installed in, or None if it can't be found."""
    global __GAME_INSTALL_DIR
    if __GAME_INSTALL_DIR is not False: return __GAME_INSTALL_DIR
    __GAME_INSTALL_DIR = None
    try:
        with open(DMM_CONFIG, encoding='utf-8') as f:
            dmm_um_config = next((game for game in json.load(f)['contents'] if game['productId'] == "umamusume"), None)
            if dmm_um_config is not None:
                __GAME_INSTALL_DIR = Path(dmm_um_config['detail']['path'])
    except FileNotFoundError:
        # Older DMM installs might not have the DMM config file, if it wasn't found try an old registry check approach
        if IS_WIN:
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                    r"SOFTWARE\WOW6432Node\DMM GAMES\Launcher\Content\umamusume") as k:
                    __GAME_INSTALL_DIR = Path(winreg.QueryValueEx(k, "Path")[0])
            except:
                pass
    return __GAME_INSTALL_DIR
