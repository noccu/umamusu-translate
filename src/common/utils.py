import json
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Union, Optional
from functools import cache

import regex

from .constants import DMM_CONFIG, IS_WIN


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


def currentTimestamp():
    return int(datetime.now(timezone.utc).timestamp())


def timestampToDate(ts):
    return datetime.fromtimestamp(ts)


## Game ##

@cache
def getUmaInstallDir() -> Optional[Path]:
    """Return the path to the directory umamusume.exe was installed in, or None if it can't be found."""
    try:
        with open(DMM_CONFIG, encoding="utf-8") as f:
            dmm_uma_config = next(
                (game for game in json.load(f)["contents"] if game["productId"] == "umamusume"),
                None,
            )
            if dmm_uma_config is not None:
                return Path(dmm_uma_config["detail"]["path"])
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
                    return Path(winreg.QueryValueEx(k, "Path")[0])
            except OSError:
                pass


## Files ##


def _to_json(o):
    try:
        return o.__json__()
    except Exception:
        raise TypeError


def readJson(file: Union[str, PurePath]) -> Union[dict, list]:
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)


def writeJson(file: Union[str, Path], data, indent=4):
    if not isinstance(file, Path):
        file = Path(file)
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, "w", encoding="utf8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent, default=_to_json)


def mkdir(path, parents=True, exists=True):
    Path(path).mkdir(parents=parents, exist_ok=exists)


def sanitizeFilename(fn: str):
    """Remove invalid path chars (win)"""
    delSet = {34, 42, 47, 58, 60, 62, 63, 92, 124}
    sanitizedName = ""
    for c in fn:
        cp = ord(c)
        if cp > 31 and cp not in delSet:
            sanitizedName += c
    return sanitizedName

def isJson(f: str):
    return f.endswith(".json")
