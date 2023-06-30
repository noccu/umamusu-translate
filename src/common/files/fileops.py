import json
from os import PathLike
from pathlib import Path
from typing import Union


def _to_json(o):
    try:
        return o.__json__()
    except Exception:
        raise TypeError


def readJson(file: PathLike) -> Union[dict, list]:
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)


def writeJson(file: PathLike, data, indent=4):
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
