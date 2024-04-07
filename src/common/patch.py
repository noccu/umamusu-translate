import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePath, PosixPath
from typing import Union
from functools import cache

import regex

from . import utils, logger
from .constants import GAME_ASSET_ROOT, TARGET_TYPES, TRANSLATION_FOLDER
from .types import StoryId


def find_git_changed_files(changeType, minStoryId:tuple, jsonOnly=True):
    from subprocess import PIPE, run

    found: list[Path] = list()
    targetType, targetGroup, targetId = minStoryId
    cmd = (
        ["git", "status", "--short", "--porcelain"]
        if changeType is True
        else ["git", "show", "--pretty=", "--name-status", changeType]
    )
    # Assumes git-config quotedPath = true (default) but works either way it seems.
    for line in (
        run(cmd, stdout=PIPE)
        .stdout.decode("unicode-escape")
        .encode("latin-1")
        .decode()
        .splitlines()
    ):
        m = regex.match(r'.?[AM]\s*"?([^"]+)"?', line)
        # Ignore other statuses like "new/??"
        if not m:
            continue
        path = Path(m[1])
        if (
            path.parts[0] != "translations" 
            or path.parts[1] != targetType
            or (jsonOnly and not utils.isJson(path.name))
            or targetGroup and path.parts[2] != targetGroup
            or targetId and path.parts[3] != targetId
        ):
            continue
        found.append(path)
    return found

def searchFiles(
    targetType: Union[str, PurePath],
    targetGroup,
    targetId,
    targetIdx=None,
    targetSet=None,
    changed=False,
    jsonOnly=True,
) -> list[Path]:
    if changed:
        return find_git_changed_files(changed, (targetType, targetGroup, targetId), jsonOnly)
    found: list[Path] = list()
    searchDir = (
        targetType
        if isinstance(targetType, PurePath)
        else TRANSLATION_FOLDER.joinpath(targetType)
    )
    for root, dirs, files in os.walk(searchDir):
        root = Path(root)
        dirType = len(dirs[0]) if dirs else -1
        if targetSet and dirType == 5:
            dirs[:] = [d for d in dirs if d == targetSet]
        elif targetGroup and dirType == 2:
            dirs[:] = [d for d in dirs if d == targetGroup]
        elif targetId:
            if targetType in ("lyrics", "preview"):
                found.extend(
                    root.joinpath(file)
                    for file in files
                    if PurePath(file).stem == targetId and (utils.isJson(file) if jsonOnly else True)
                )
                continue  #? probably return
            elif dirType == 4:
                dirs[:] =  [d for d in dirs if d == targetId]
        if not files:
            continue
        if targetIdx:
            found.extend(
                root.joinpath(file)
                for file in files
                if file.startswith(targetIdx) and (utils.isJson(file) if jsonOnly else True)
            )  #todo: consider full filename check for flexibility
        else:
            found.extend(
                root.joinpath(file) for file in files 
                if (utils.isJson(file) if jsonOnly else True)
            )
    return found

@cache
def patchVersion():
    try:
        with open(".git/refs/heads/master", "r") as f:
            v = f.readline()
    except FileNotFoundError:
        v = os.path.getmtime("tl-progress.md")
        v = datetime.fromtimestamp(v, tz=timezone.utc).isoformat()
    except Exception:
        v = "unknown"
    return v


class RawDefaultFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    pass


class Args(argparse.ArgumentParser):
    loggerLevelSet = False
    def __init__(self, desc, defaultArgs=True, types: tuple = None, **kwargs) -> None:
        super().__init__(
            description=desc,
            conflict_handler="resolve",
            formatter_class=RawDefaultFormatter,
            **kwargs,
        )
        self.add_argument("-v", "--version", action="store_true", help="Show version and exit")
        self.add_argument(
            "--read-defaults",
            "--read-config",
            action="store_true",
            help="Overwrite args with data from umatl.json config",
        )
        self.add_argument("-vb", "--verbose", action="store_true", help="Print more detailed info")
        self.add_argument("-dbg", "--debug", action="store_true", help="Print debug info")
        self.hasDefault = defaultArgs
        if defaultArgs:
            self.add_argument(
                "-t",
                "--type",
                choices=types or TARGET_TYPES,
                default=types[0] if types else TARGET_TYPES[0],
                help="The type of assets to process.",
            )
            self.add_argument("-s", "--set", help="The set to process")
            self.add_argument("-g", "--group", help="The group to process")
            self.add_argument("-id", help="The id (subgroup) to process")
            self.add_argument("-idx", help="The specific asset index to process")
            self.add_argument(
                "-sid",
                "-story",
                "--story",
                help="The storyid to process, can be partial",
            )
            self.add_argument(
                "--changed",
                nargs="?",
                default=False,
                const=True,
                help="Limit to changed files (requires git)",
            )
            self.add_argument("-src", type=Path, default=GAME_ASSET_ROOT)
            self.add_argument("-dst", type=Path, default=Path("dat/").resolve())
        elif types:
            self.add_argument(
                "-t",
                "--type",
                choices=types,
                default=types[0],
                help="The type of assets to process.",
            )

    def parse_args(self, *args, **kwargs):
        a = super().parse_args(*args, **kwargs)
        if a.version:
            print(f"Patch version: {patchVersion()}")
            sys.exit()
        if a.read_defaults:
            cfg = UmaTlConfig()
            for k, v in cfg.script.items():
                setattr(a, k, v)
        if self.hasDefault and a.story:
            a.story = StoryId.parse(a.type, a.story)
            a.set = a.set or a.story.set
            a.group = a.group or a.story.group
            a.id = a.id or a.story.id
            a.idx = a.idx or a.story.idx
        if a.debug:
            a.verbose = False
        # Set level only for main script (prevent sub-calls from overwriting).
        if not Args.loggerLevelSet:
            logger.levelFromArgs(a)
            Args.loggerLevelSet = True
        return a

    @classmethod
    def fake(cls, **kwargs):
        return argparse.Namespace(**kwargs)

@cache
def isUsingTLG() -> bool:
    path = utils.getUmaInstallDir()
    if path is None:
        return
    return path.joinpath("config.json").exists()


class UmaTlConfig:
    cfg = None
    core = None
    empty = {}
    filename = Path("umatl.json")

    def __init__(self) -> None:
        # Resolve to make sure it works on both abs and rel paths.
        cur_script = PosixPath(sys.argv[0]).resolve()
        ctx = str(
            cur_script.relative_to(PosixPath("src").resolve()).with_suffix("")
        )
        if not UmaTlConfig.cfg:
            try:
                UmaTlConfig.cfg = utils.readJson(UmaTlConfig.filename)
                UmaTlConfig.core = UmaTlConfig.cfg.get("core", UmaTlConfig.empty)
            except FileNotFoundError:
                self.createDefault()
        self.script = UmaTlConfig.cfg.get(ctx, UmaTlConfig.empty)

    @staticmethod
    def save():
        utils.writeJson(UmaTlConfig.filename, UmaTlConfig.cfg, 2)

    @staticmethod
    def createDefault():
        if UmaTlConfig.filename.exists():
            print("UmaTL config file already exists.")
            return
        data = {
            "core": {},
            "import": {"update": True, "skip_mtl": True},
            "mdb/import": {"skill_data": False},
        }
        UmaTlConfig.cfg = data
        try:
            UmaTlConfig.save()
        except PermissionError:
            print(
                "Error: Lacking permissions to create the config file in this location. \n"
                "Edit the patch folder's permissions or move it to a different location."
            )
            sys.exit()
        print(
            "UmaTL uses the umatl.json config file for user preferences when directed to.\n"
            "This happens automatically when used as a patch. The file can be opened in a text editor."
        )
