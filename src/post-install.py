from pathlib import Path
from zipfile import ZipFile
# from os import startfile
import shutil
from common import utils, patch, logger, constants
from manage import CONFIG_FILE as TLG_CFG
import requests

TLG_TARGETS = (
    "version.dll",
    "umpdc.dll",
    "xinput1_3.dll"
)
TMP_STORE = Path("temp")
SUCCESS = True


def call_api(url):
    data = requests.get(url)
    if data.status_code == 200:
        return data
    logger.error(f"Error calling API: {url}")
    logger.debug(f"Status: {data.status_code}\nContent:{data.text}")
    raise requests.HTTPError


def download_file(url:str, name:str):
    file_path = TMP_STORE.joinpath(name)
    if file_path.exists():
        print(f"Using existing temp file: {name}")
        return
    data = requests.get(url)
    if data.status_code == 200:
        with open(file_path, "wb") as f:
            f.write(data.content)
    else:
        logger.error(f"Error downloading file: {name}")
        logger.debug(f"Status: {data.status_code}\nContent:{data.text}")
        raise requests.HTTPError


def download_tlg():
    tlg_idx = -1
    if TLG_CFG.exists():
        overwrite = input(
            "\nIt looks like TLG is already installed (config.json exists).\n"
            "Continue and overwrite with newest release? [y]es, [n]o: "
        )
        if overwrite.startswith("n"):
            return
        # Ask to replace the correct file
        file_choice = "\n".join(f"{i}: {n}" for i, n in enumerate(TLG_TARGETS))
        tlg_idx = int(input(
            f"\nTLG and other mods can share these filenames\n{file_choice}\n"
            "Input the number corresponding to your TLG file: "
        ).strip()[0])
    # Find latest release
    print("Finding latest TLG release...")
    info = call_api("https://api.github.com/repos/MinamiChiwa/Trainers-Legend-G/releases/latest").json()
    try:
        archive = info["assets"][0]["browser_download_url"]
        size = int(info["assets"][0]["size"] *10**-6)
    except KeyError:
        print("Aborted: Couldn't locate TLG archive, please install manually.")
        raise
    # Download release
    print(f"Downloading TLG ({size} MB)...")
    download_file(archive, "tlg.zip")
    print("Download finished, installing...")
    install_tlg(tlg_idx)


def install_tlg(tlg_idx):
    # Delete old file when not a new install
    if tlg_idx != -1:
        try:
            utils.getUmaInstallDir().joinpath(TLG_TARGETS[tlg_idx]).unlink()
        except PermissionError:
            pass # Defer to message later.
    # Extract zip
    with ZipFile(TMP_STORE.joinpath("tlg.zip")) as zip:
        # Extract overwrites existing files
        tlg_dll = Path(zip.extract(TLG_TARGETS[0], TMP_STORE))
    # Copy config
    try:
        shutil.copyfile(TLG_CFG, utils.getUmaInstallDir().joinpath(TLG_CFG.name))
    except PermissionError:
        print(
            "No permission to write to the Uma Musume install dir.\n"
            "Please copy temp/version.dll & localify/config.json there yourself.\n"
            f"Install dir: {utils.getUmaInstallDir()}"
        )
        raise
    except FileExistsError:
        pass # Overwrite requested, copy dll
    # Copy DLL
    for name in (TLG_TARGETS if tlg_idx == -1 else (TLG_TARGETS[tlg_idx],)):
        try:
            shutil.copyfile(tlg_dll, utils.getUmaInstallDir().joinpath(name))
        except FileExistsError:
            # New install (no config) but dll exists. idx == -1
            print(
                f"File {name} already exists, renaming...\n"
                "You may need to adjust configs if you use other mods."
            )
            continue
        print(f"TLG successfully installed as {name}")
        break


def main():
    if not constants.IS_WIN:
        return
    print("Creating UmaTL config file.")
    patch.UmaTlConfig.createDefault()
    get_tlg = input("Install TLG for UI translations? [y]es, [n]o: ")
    if get_tlg.startswith("n"):
        return
    
    TMP_STORE.mkdir(exist_ok=True)
    try:
        download_tlg()
    except:
        print(
            "\nNot everything went right, check the steps on GitHub "
            "or ask in the Discord if you need help."
        )
    else:
        shutil.rmtree(str(TMP_STORE))


if __name__ == "__main__":
    main()
