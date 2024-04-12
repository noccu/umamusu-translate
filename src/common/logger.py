# Silly stuff because… uh, yeah.
import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL  # Pass-through
from sys import stdout
from pathlib import Path


_FORMATTER = logging.Formatter("[$levelname] $filename: $message", style="$")
_STDOUT_HANDLER = logging.StreamHandler(stdout)
_STDOUT_HANDLER.setFormatter(_FORMATTER)
_LOGGER = logging.getLogger("UmaTL_Shared")
# Set logger to lowest level and config handlers instead
_LOGGER.setLevel(DEBUG)
_LOGGER.addHandler(_STDOUT_HANDLER)
_FILE_HANDLER = None

def levelFromArgs(args):
    if getattr(args, "verbose", None):
        _STDOUT_HANDLER.setLevel(INFO)
    elif getattr(args, "debug", None):
        _STDOUT_HANDLER.setLevel(DEBUG)
    else:
        _STDOUT_HANDLER.setLevel(WARNING)

def getLevel():
    # todo: generalize
    return _STDOUT_HANDLER.level

def conditionalDetail(msg, detailedMsg, detailLevel):
    if _STDOUT_HANDLER.level <= detailLevel:
        log(detailLevel, detailedMsg)
    else:
        print(msg)

def setFile(filename: str = "umatl.log", level = logging.DEBUG):
    from datetime import datetime, timezone
    global _FILE_HANDLER
    closeFile()
    logDir = Path("logs")
    logDir.mkdir(exist_ok=True)
    _FILE_HANDLER = logging.FileHandler(logDir.joinpath(filename), encoding="utf8")
    _FILE_HANDLER.setFormatter(_FORMATTER)
    _FILE_HANDLER.setLevel(level)
    _LOGGER.addHandler(_FILE_HANDLER)
    date = datetime.now(timezone.utc).isoformat(" ", "seconds")  
    _FILE_HANDLER.stream.write(f"{'\n' if _FILE_HANDLER.stream.tell() > 1 else ''}== {date} ==\n")

def closeFile():
    if _FILE_HANDLER is not None:
        _FILE_HANDLER.close()

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
