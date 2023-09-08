import json
from pathlib import PurePath, Path
import shutil

from common import utils, patch, logger
from common.types import TranslationFile

ROOT = PurePath("src")
LOCAL_DUMP = ROOT / "data" / "static_dump.json"
LOCALIFY_DATA_DIR = Path("localify") / "localized_data"
HASH_FILE_STATIC = LOCALIFY_DATA_DIR / "static.json"
HASH_FILE_DYNAMIC = LOCALIFY_DATA_DIR / "dynamic.json"
CONFIG_FILE = Path("localify") / "config.json"
TL_FILE = PurePath("translations") / "localify" / "ui.json"
STRING_BLACKLIST = ("現在の予約レース",)


def updateTlData(dumpData: dict, tlData: dict):
    for _, text in dumpData.items():
        if text not in tlData:
            tlData[text] = ""


def updateHashData(dumpData: dict, tlData: dict, hashData: tuple[dict, dict]):
    for hash, text in dumpData.items():
        translatedText = tlData.get(text)
        if len(hash) > 5:
            data = hashData[1]
            key = hash
        else:
            data = hashData[0]
            key = text

        inBlacklist = False
        if translatedText and not (inBlacklist := key in STRING_BLACKLIST):
            # special case for effectively removing text
            data[key] = "" if translatedText == "<empty>" else translatedText
        else:
            if inBlacklist:
                logger.warning(f"{key} causes issues with the game, skipping...")
            # Remove previously translated hashes that no longer are to prevent garbled text
            if key in data:
                logger.debug(f"Missing {text} at {hash}. Removing existing: {hashData[hash]}")
                del data[key]


def importDump(path: PurePath, args) -> dict:
    isExternal = path != LOCAL_DUMP
    # load local dump to update if using an external file
    localDumpData = utils.readJson(LOCAL_DUMP) if isExternal else None

    if path.suffix != ".json":
        # if it's not a json file then it's definitely external as we only use static_dump.json
        assert isExternal, "Dump file is not json and not external"

        with open(path, "r", encoding="utf8") as f:
            data = "{" + f.read()[:-2] + "}"  # remove trailing newline and comma
            data = json.loads(data)
    else:
        data = utils.readJson(path)

    if isExternal:
        data = {**localDumpData, **data} if args.overwrite else {**data, **localDumpData}
    animationCheck = list()
    # copy to list so we don't run into issues deleting keys in our loop obj
    for key, val in list(data.items()):
        # remove non-japanese data (excluding static)
        if len(key) > 5 and utils.isEnglish(val):
            del data[key]
            continue
        # remove animated text
        if len(animationCheck) == 0 or (
            val.startswith(animationCheck[-1][1]) and len(val) - len(animationCheck[-1][1]) < 2
        ):
            animationCheck.append((key, val))
        else:
            if len(animationCheck) > 4:
                for k, _ in animationCheck:
                    del data[k]
            animationCheck.clear()
    if args.save or args.import_only:
        utils.writeJson(LOCAL_DUMP, data)
    return data


def importTlgStatic(dumpPath, tlData):
    data = utils.readJson(dumpPath)
    for k in data.keys():
        if k not in tlData:
            tlData[k] = ""


def clean(mode):
    """Clean ui.json and/or static_dump.json of empty translations.
    Keep the dump's static hashes regardless."""
    # Remove empty translations
    translations = {
        jp: en 
        for jp, en in utils.readJson(TL_FILE).items() 
        if en
    }
    if mode in ("both", "ui"):
        utils.writeJson(file=TL_FILE, data=translations)

    if mode in ("both", "dump"):
        utils.writeJson(
            file=DUMP_FILE,
            data={
                ui_hash: jp
                for ui_hash, jp in utils.readJson(DUMP_FILE).items()
                if len(ui_hash) <= 5 or jp in translations
            },
        )  # Keep static hashes even if untranslated

    if mode == "dyn":
        staticVals = utils.readJson(HASH_FILE_STATIC).values()
        dynamicData = utils.readJson(HASH_FILE_DYNAMIC)
        for hash, en in list(dynamicData.items()):
            if en != "" and en in staticVals:
                del dynamicData[hash]
        utils.writeJson(HASH_FILE_DYNAMIC, dynamicData)


def order():
    for file in [LOCAL_DUMP, HASH_FILE_STATIC, HASH_FILE_DYNAMIC]:
        stringKey = file == HASH_FILE_STATIC
        data = utils.readJson(file)
        data = dict(sorted(data.items(), key=lambda x: x[0] if stringKey else int(x[0])))
        utils.writeJson(file, data)


def convertMdb():
    """Writes any mdb files marked to do so in the index as TLG format dicts, returns the paths written."""
    converted = list()
    for entry in utils.readJson("src/mdb/index.json"):
        files = entry["files"].items() if entry.get("files") else ((entry.get("file"), None),)
        for file, info in files:
            if not (isinstance(info, dict) and info.get("tlg")) and not entry.get("tlg"):
                continue
            subdir = entry["table"] if entry.get("subdir") else ""
            fn = f"{file}.json"
            tlData = utils.readJson(Path("translations/mdb") / subdir / fn).get("text", dict())
            data = dict()
            for k, v in tlData.items():
                if not v:
                    continue
                v = TextHasher.normalize(v)
                data[TextHasher.hash(k)] = v
                if entry.get("winBreaks") or (isinstance(info, dict) and info.get("winBreaks")):
                    data[TextHasher.hash(k, True)] = v
            if data:
                path = LOCALIFY_DATA_DIR / entry["table"] / fn
                utils.writeJson(path, data)
                converted.append(path.relative_to(LOCALIFY_DATA_DIR.parent))
    print(f"Converted {len(converted)} files.")
    return converted


def convertTlFile(tlFile: TranslationFile, overwrite=False):
    converted = list()
    path = LOCALIFY_DATA_DIR / tlFile.type / (tlFile.getStoryId() + ".json")
    if not overwrite and path.exists() and path.stat().st_mtime >= tlFile.file.stat().st_mtime:
        return
    data = dict()
    for b in tlFile.genTextContainers():
        if text := b.get("enText"):
            data[TextHasher.hash(b["jpText"])] = TextHasher.normalize(text)
        if name := b.get("enName"):
            data[TextHasher.hash(b["jpName"])] = TextHasher.normalize(name)
    utils.writeJson(path, data)
    converted.append(path)
    return converted


def updConfigDicts(cfgPath, dictPaths: list):
    """Update the dicts key in the cfgPath file with the given dictPaths."""
    try:
        data = utils.readJson(cfgPath)
    except FileNotFoundError:
        logger.error("Config file not found")
        return
    dicts = ["localized_data\\dynamic.json", *[str(x) for x in dictPaths]]
    data["dicts"] = dicts
    data["static_dict"] = "localized_data\\static.json"
    data["text_data_dict"] = ""
    data["character_system_text_dict"] = ""
    data["race_jikkyo_comment_dict"] = ""
    data["race_jikkyo_message_dict"] = ""
    data["stories_path"] = ""
    utils.writeJson(cfgPath, data)


class TextHasher:
    mapA = {ord(c): None for c in ("\r", ",")}
    mapB = {ord(c): None for c in (",")}

    @classmethod
    def hash(cls, text: str, winBreak=False):
        """Returns a 64bit C hash of text, with full or partial replacements"""
        # Cleaning done by texthashtool. There is a version that cleans \n too, seems unneeded.
        text = TextHasher.normalize(text.translate(cls.mapB if winBreak else cls.mapA), winBreak)
        # Implement vc++ std::hash (FNV1a)
        # mask = 2 ** 64 - 1 # Mask is used to emulate 64bit mult product
        o = 14695981039346656037  # FNV_offset_basis
        for c in text.encode("utf_16_le"):
            o ^= c
            o *= 1099511628211  # FNV_prime
            o &= 18446744073709551615  # Integer form of mask
        return o

    @staticmethod
    def normalize(txt: str, winBreak=False):
        """Makes sure the text is correct for use in TLG.
        Windows linebreaks are required for some game content."""
        return txt.replace("\\n", "\r\n" if winBreak else "\n")


# Based on code from http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
class FileWatcher:
    FILE_LIST_DIRECTORY = 0x0001

    def __init__(self) -> None:
        global requests
        import requests

        cfg = utils.readJson(utils.getUmaInstallDir() / "config.json")
        self.port = cfg["httpServerPort"]  # we want to ride the KeyError if it happens
        print(f"Communicating with TLG on port {self.port}")

    def watch(self, path):
        import win32con
        import win32file

        self.openHandle = win32file.CreateFile(
            str(path),
            self.FILE_LIST_DIRECTORY,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_BACKUP_SEMANTICS,
            None,
        )
        print(f"Watching {path}...\nExit with CTRL+C")
        while True:
            try:
                results = win32file.ReadDirectoryChangesW(
                    self.openHandle, 512, False, win32con.FILE_NOTIFY_CHANGE_LAST_WRITE, None, None
                )
            except win32file.error as e:
                if e.winerror == 995:  # operation cancelled
                    return
                else:
                    raise
            if not results:
                print("Error watching file")
                return
            for _action, file in results:
                if len(results) > 2 or "cache" in results[-1][1]:
                    break  # ignore change cascade (?)
                if file in ("static.json", "dynamic.json"):
                    self._reloadTlg()
                    break

    def close(self):
        if not self.openHandle:
            return
        import ctypes
        from ctypes import wintypes

        def _errcheck(value, func, args):
            if not value:
                raise ctypes.WinError()
            return args

        CancelIoEx = ctypes.WinDLL("kernel32").CancelIoEx
        CancelIoEx.restype = wintypes.BOOL
        CancelIoEx.errcheck = _errcheck
        CancelIoEx.argtypes = (
            wintypes.HANDLE,
            ctypes.c_void_p,  # ignoring this
        )
        CancelIoEx(wintypes.HANDLE(self.openHandle.handle), None)
        self.openHandle.Close()
        # todo maybe: rewrite this whole thing as proper win32 async/overlapped IO

    def _reloadTlg(self):
        print("Reloading TLG files...")
        try:
            resp = requests.post(
                f"http://127.0.0.1:{self.port}/sets",
                json={"type": "reload_all"},
                headers={"Content-Type": "application/json"},
            )
        except requests.ConnectionError:
            print("Communication error.")
            return
        print("Files reloaded")
        logger.info(f"{resp.status_code}: {resp.text}")


def watch():
    import threading
    import time

    watcher = FileWatcher()
    try:
        t = threading.Thread(
            target=watcher.watch,
            args=(utils.getUmaInstallDir() / "localized_data",),
            daemon=True,
        )
        t.start()
        time.sleep(9999)  # wait for exit
    except KeyboardInterrupt:
        print("Stop requested...")
        watcher.close()
    finally:
        t.join(15)
        print("Exiting")
    # Manual form
    # while True:
    #     x = input("Action (r,q): ")
    #     if x == "r":
    #         watcher._reloadTlg()
    #     else:
    #         return


def move():
    print("Copying UI translations")
    installDir = utils.getUmaInstallDir()
    if installDir:
        try:
            dst = installDir / LOCALIFY_DATA_DIR.name
            # Following disabled to check TLG status. First install must be manual.
            # dst.mkdir(exist_ok=True)
            # Using rglob for future functionality
            dynFiles = list()
            for f in LOCALIFY_DATA_DIR.rglob("*.json"):
                subPath = f.relative_to(LOCALIFY_DATA_DIR)
                fn = dst / subPath
                fn.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, fn)
                if len(subPath.parts) > 1:
                    dynFiles.append(LOCALIFY_DATA_DIR.name / subPath)
            updConfigDicts(installDir / "config.json", dynFiles)
        except PermissionError:
            logger.error(
                f"No permission to write to {installDir}.\n"
                "Update perms, run as admin, or copy files yourself."
            )
        except FileNotFoundError as e:
            if not installDir.exists():
                logger.error(
                    f"Obtained install dir doesn't exist: {str(installDir)}\n"
                    "Possibly corrupt or double game install. Copy UI files manually."
                )
            elif not dst.exists():
                logger.warning("TLG not installed. See guide if you wish to translate UI elements.")
            else:
                logger.error(
                    f"{repr(e)}\n"
                    f"A patch file with/for UI translations is missing.\n"
                    f"Data may have been corrupted somehow, restore the files in {LOCALIFY_DATA_DIR}."
                )
    else:
        logger.error("Couldn't find game install path, files not moved.")


def parseArgs(args=None):
    ap = patch.Args("Manages localify data files for UI translations", defaultArgs=False)
    ap.add_argument(
        "-new",
        "--populate",
        action="store_true",
        help="Add dump (local or target) entries to ui.json for translating",
    )
    # ? in hindsight I don't think it's useful to not import as
    # ? we need both dump and tl file for the whole thing to
    # ? work right but ok. can't say there's no choice at least :^)
    ap.add_argument(
        "-save",
        "-add",
        action="store_true",
        help="Save target dump entries to local dump on import",
    )
    ap.add_argument(
        "-upd",
        "--update",
        action="store_true",
        help="Create/update the final json files used by TLG",
    )
    ap.add_argument(
        "-clean",
        "--clean",
        choices=["dump", "ui", "both", "dyn"],
        nargs="?",
        const="both",
        default=False,
        help="Remove untranslated entries from ui tl file and/or local dump. Defaults to 'both'",
    )
    ap.add_argument(
        "-sort", "-order", action="store_true", help="Sort keys in local dump and final files"
    )
    ap.add_argument(
        "-O",
        "--overwrite",
        action="store_true",
        help="Overwrite/update local dump keys instead of only adding new ones",
    )
    ap.add_argument(
        "-I",
        "--import-only",
        action="store_true",
        help="Purely import target dump to local and exit."
        "Implies -save and -src (auto mode, can be overridden)",
    )
    ap.add_argument("-M", "--move", action="store_true", help="Move final json files to game dir.")
    ap.add_argument(
        "-src",
        default=LOCAL_DUMP,
        const=None,
        nargs="?",
        type=PurePath,
        help="Target dump file for imports. Auto-detects in game dir if no path given",
        metavar="path",
    )
    ap.add_argument(
        "-tlg",
        default=None,
        const=PurePath(utils.getUmaInstallDir(), "static_dump.json"),
        nargs="?",
        type=PurePath,
        help="Import TLG's static dump too. Auto-detects in game dir if no path given",
        metavar="path",
    )
    ap.add_argument(
        "-mdb",
        "--convert-mdb",
        action="store_true",
        help="Import some mdb strings for TLG to improve formatting",
    )
    ap.add_argument(
        "-conv",
        "--convert-asset",
        nargs="?",
        const=True,
        default=False,
        help="Write TLG versions of [specified] asset files marked as such",
        metavar="path",
    )
    ap.add_argument(
        "-w",
        "-watch",
        "--watch",
        action="store_true",
        help="Watch TLG UI files for changes and auto-reload (requires game open with TLG)",
    )
    ap.add_argument(
        "-so",
        "-bd",
        "--backup-dump",
        "--save-old",
        action="store_true",
        help="Backup the old dump file (for diffing)",
    )
    args = ap.parse_args(args)

    if args.src is None or (args.import_only and args.src == LOCAL_DUMP):
        args.src = LOCAL_DUMP
        path = utils.getUmaInstallDir()
        if path:
            path = path / "dump.txt"
            if path.exists():
                args.src = path
            else:
                logger.error("Dump file not found.")
        else:
            logger.error("Couldn't find game path.")

        print(f"Using dump: {args.src}")

    global DUMP_FILE
    DUMP_FILE = args.src

    return args


def main(args: patch.Args = None):
    args = args or parseArgs(args)

    if args.convert_mdb:
        mdbDicts = convertMdb()
        updConfigDicts(CONFIG_FILE, mdbDicts)

    if args.convert_asset is True:
        # We currently don't use the needed default args
        raise NotImplementedError("Provide a direct path.")
        files = patch.searchFiles(args.type, args.group, args.id, args.idx)
        for file in files:
            convertTlFile(TranslationFile(file), overwrite=args.overwrite)
    elif isinstance(args.convert_asset, str):
        convertTlFile(TranslationFile(args.convert_asset), overwrite=args.overwrite)

    if args.backup_dump:
        print("Backing up dump file...")
        shutil.copyfile(LOCAL_DUMP, LOCAL_DUMP.with_stem("static_dump_old"))
    if args.populate or args.update or args.import_only:
        dumpData = importDump(DUMP_FILE, args)
        if args.import_only:
            return
        tlData = utils.readJson(TL_FILE)
        if args.populate:
            updateTlData(dumpData, tlData)
            if args.tlg:
                importTlgStatic(args.tlg, tlData)
            utils.writeJson(TL_FILE, tlData)
        elif args.update:
            hashData = utils.readJson(HASH_FILE_STATIC), utils.readJson(HASH_FILE_DYNAMIC)
            updateHashData(dumpData, tlData, hashData)
            utils.writeJson(HASH_FILE_STATIC, hashData[0])
            utils.writeJson(HASH_FILE_DYNAMIC, hashData[1])

    if args.clean:
        clean(args.clean)
    if args.sort:
        order()
    if args.move:
        move()
    if args.watch:
        watch()


if __name__ == "__main__":
    main()
