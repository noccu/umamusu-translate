import argparse
import json
import os
from pathlib import Path, PurePath
import sys
from typing import Optional
import regex
from datetime import datetime, timezone

from .files import fileops
from .constants import GAME_ASSET_ROOT, TARGET_TYPES, IS_WIN, DMM_CONFIG
from .StoryId import StoryId

__GAME_INSTALL_DIR = None
__IS_USING_TLG = None


def searchFiles(
    targetType,
    targetGroup,
    targetId,
    targetIdx=False,
    targetSet=False,
    changed=False,
    jsonOnly=True,
) -> list[str]:
    def isJson(f: str):
        return PurePath(f).suffix == ".json" if jsonOnly else True

    found = list()
    if changed:
        from subprocess import run, PIPE

        cmd = (
            ["git", "status", "--short", "--porcelain"]
            if changed is True
            else ["git", "show", "--pretty=", "--name-status", changed]
        )
        # assumes git-config quotedPath = true, which is default I believe. :tmopera:
        for line in (
            run(cmd, stdout=PIPE)
            .stdout.decode("unicode-escape")
            .encode("latin-1")
            .decode()
            .splitlines()
        ):
            m = regex.match(r'.?([^\s])\s*"?([^"]+)"?', line)
            state, path = m[1], PurePath(m[2])
            if (
                state in ("A", "M")
                and path.parts[0] == "translations"
                and path.parts[1] == targetType
            ):
                if not isJson(path):
                    continue
                if targetGroup and path.parts[2] != targetGroup:
                    continue
                if targetId and path.parts[3] != targetId:
                    continue
                found.append(str(path))
    else:
        searchDir = (
            targetType
            if isinstance(targetType, os.PathLike)
            else os.path.join("translations", targetType)
        )
        for root, dirs, files in os.walk(searchDir):
            depth = len(dirs[0]) if dirs else -1
            if targetSet and depth == 5:
                dirs[:] = [d for d in dirs if d == targetSet]
            elif targetGroup and depth == 2:
                dirs[:] = [d for d in dirs if d == targetGroup]
            elif targetId:
                if targetType in ("lyrics", "preview"):
                    found.extend(
                        os.path.join(root, file)
                        for file in files
                        if PurePath(file).stem == targetId and isJson(file)
                    )
                    continue
                elif depth == 4:
                    dirs[:] = [d for d in dirs if d == targetId]
            if targetIdx and files:
                found.extend(
                    os.path.join(root, file)
                    for file in files
                    if file.startswith(targetIdx) and isJson(file)
                )
            else:
                found.extend(os.path.join(root, file) for file in files if isJson(file))
    return found


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
            self.add_argument("-src", default=GAME_ASSET_ROOT)
            self.add_argument("-dst", default=Path("dat/").resolve())
            self.add_argument("-vb", "--verbose", action="store_true", help="Print additional info")
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
        return a

    @classmethod
    def fake(cls, **kwargs):
        return argparse.Namespace(**kwargs)


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


class UmaTlConfig:
    cfg = None
    core = None
    empty = {}

    def __init__(self) -> None:
        # Resolve to make sure it works on both abs and rel paths.
        ctx = str(
            Path(sys.argv[0]).resolve().relative_to(Path("src").resolve()).with_suffix("")
        ).replace("\\", "/")
        if not UmaTlConfig.cfg:
            try:
                UmaTlConfig.cfg = fileops.readJson("umatl.json")
                UmaTlConfig.core = UmaTlConfig.cfg.get("core", UmaTlConfig.empty)
            except FileNotFoundError:
                self.createDefault()
        self.ensureCore()
        self.script = UmaTlConfig.cfg.get(ctx, UmaTlConfig.empty)

    def save(self):
        fileops.writeJson("umatl.json", UmaTlConfig.cfg, 2)

    def ensureCore(self):
        if "core" not in UmaTlConfig.cfg:
            UmaTlConfig.cfg["core"] = {}
            self.save()

    def createDefault(self):
        data = {
            "core": {},
            "import": {"update": True, "skip_mtl": False},
            "mdb/import": {"skill_data": False},
        }
        try:
            UmaTlConfig.cfg = data
            self.save()
        except PermissionError:
            print(
                "Error: Lacking permissions to create the config file in this location. \n"
                "Edit the patch folder's permissions or move it to a different location."
            )
            sys.exit()
        print(
            "Uma-tl uses the umatl.json config file for user preferences when requested.\n"
            "This seems to be your first time running uma-tl this way so a new file was created.\n"
            "Uma-tl has quit without doing anything this first time so you can edit the config before running it again. Defaults are:"
        )
        del data["core"]
        print(json.dumps(data, indent=2))
        sys.exit()
