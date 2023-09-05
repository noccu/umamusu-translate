# Silly stuff because… uh, yeah.
import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL  # Pass-through
from sys import stdout
from pathlib import Path


_FORMATTER = logging.Formatter("[$levelname] $filename: $message", style="$")
_HANDLER = logging.StreamHandler(stdout)
_HANDLER.setFormatter(_FORMATTER)
_LOGGER = logging.getLogger("UmaTL_Shared")
_LOGGER.addHandler(_HANDLER)
_FILE_LOGGER = None

def levelFromArgs(args):
    if getattr(args, "verbose", None):
        _LOGGER.setLevel(INFO)
    elif getattr(args, "debug", None):
        _LOGGER.setLevel(DEBUG)

def getLevel():
    return _LOGGER.level

def conditionalDetail(msg, detailedMsg, detailLevel):
    if _LOGGER.level <= detailLevel:
        log(detailLevel, detailedMsg)
    else:
        print(msg)

def setFile(filename: str = "umatl.log", level = logging.INFO):
    from datetime import datetime, timezone
    global _FILE_LOGGER
    closeFile()
    logDir = Path("logs")
    logDir.mkdir(exist_ok=True)
    _FILE_LOGGER = logging.FileHandler(logDir.joinpath(filename), encoding="utf8")
    _FILE_LOGGER.setFormatter(_FORMATTER)
    _FILE_LOGGER.setLevel(level)
    _LOGGER.addHandler(_FILE_LOGGER)
    date = datetime.now(timezone.utc).isoformat(" ", "seconds")  
    if _FILE_LOGGER.stream.tell() > 1:
        _FILE_LOGGER.stream.write("\n")
    _FILE_LOGGER.stream.write(f"== {date} ==\n")

def closeFile():
    if _FILE_LOGGER is not None:
        _FILE_LOGGER.close()

setLevel = _LOGGER.setLevel
debug = _LOGGER.debug
info = _LOGGER.info
warning = _LOGGER.warning
error = _LOGGER.error
critical = _LOGGER.critical
log = _LOGGER.log


# Hehe
# def __getattr__(__name: str):
#     return getattr(_LOGGER, __name, None) or getattr(logging, __name)

# Hehehe
# modules[__name__] = _LOGGER
