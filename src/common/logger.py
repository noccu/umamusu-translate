# Silly stuff because… uh, yeah.
import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL  # Pass-through
from sys import stdout


_FORMATTER = logging.Formatter("[$levelname] $filename: $message", style="$")
_HANDLER = logging.StreamHandler(stdout)
_HANDLER.setFormatter(_FORMATTER)
_LOGGER = logging.getLogger("UmaTL_Shared")
_LOGGER.addHandler(_HANDLER)


def levelFromArgs(args):
    if getattr(args, "verbose", None):
        _LOGGER.setLevel(INFO)
    elif getattr(args, "debug", None):
        _LOGGER.setLevel(DEBUG)


setLevel = _LOGGER.setLevel
debug = _LOGGER.debug
info = _LOGGER.info
warning = _LOGGER.warning
error = _LOGGER.error
critical = _LOGGER.critical


# Hehe
# def __getattr__(__name: str):
#     return getattr(_LOGGER, __name, None) or getattr(logging, __name)

# Hehehe
# modules[__name__] = _LOGGER
