from typing import Union
import regex
import json
from pathlib import Path
from os import PathLike
import winreg


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

def getUmaInstallPath():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\DMM GAMES\Launcher\Content\umamusume") as k:
            return Path(winreg.QueryValueEx(k, "Path")[0])
    except:
        return None