from pathlib import Path
from zipfile import ZipFile
# from os import startfile
import shutil
from common import utils, patch, logger, constants
from manage import CONFIG_FILE as TLG_CFG
import requests

TLG_TARGETS = (
    "dxgi.dll",
    "umpdc.dll",
    "xinput1_3.dll"
)
TMP_STORE = Path("temp")


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
        logger.info(f"Using existing temp file: {name}")
        return file_path
    data = requests.get(url)
    if data.status_code == 200:
        with open(file_path, "wb") as f:
            f.write(data.content)
    else:
        logger.error(f"Error downloading file: {name}")
        logger.debug(f"Status: {data.status_code}\nContent:{data.text}")
        raise requests.HTTPError
    return file_path


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
            f"\nTLG and other mods can share these filenames:\n{file_choice}\n"
            "Input the number corresponding to your existing TLG file to overwrite: "
        ).strip()[0])
    # Find latest release
    logger.info("Finding latest TLG release...")
    info = call_api("https://api.github.com/repos/MinamiChiwa/Trainers-Legend-G/releases/latest").json()
    try:
        archive = info["assets"][0]["browser_download_url"]
        size = info["assets"][0]["size"]
        size_MB = int(size *10**-6)
    except KeyError:
        logger.error("Aborted: Couldn't locate TLG archive, please install manually.")
        raise
    # Download release
    logger.info(f"Downloading TLG ({size_MB} MB)...")
    tlg_arch = download_file(archive, "tlg.zip")
    arch_size = tlg_arch.stat().st_size
    if arch_size < size - 1000:
        logger.error(
            f"The downloaded TLG archive's size ({arch_size}) does not match that provided by GitHub ({size}).\n"
            "This is a common issue unrelated to UmaTL. Try running this installer again or install TLG manually.\n"
            f"If needed, you can download TLG yourself and put it in {TMP_STORE} as 'tlg.zip' before running the installer again."
        )
        raise Exception("Size mismatch")
    logger.info("Download finished, installing...")
    install_tlg(tlg_idx)


def install_tlg(tlg_idx):
    # Delete old file when not a new install
    if tlg_idx != -1:
        try:
            utils.getUmaInstallDir().joinpath(TLG_TARGETS[tlg_idx]).unlink()
            utils.getUmaInstallDir().joinpath("tlg.dll").unlink()
        except PermissionError:
            pass # Defer to message later.
        except FileNotFoundError:
            pass # continue install
    # Extract zip
    with ZipFile(TMP_STORE.joinpath("tlg.zip")) as zip:
        # Extract overwrites existing files
        loader_dll = Path(zip.extract("dxgi.dll", TMP_STORE))
        tlg_dll = Path(zip.extract("tlg.dll", TMP_STORE))
    # Copy config
    try:
        shutil.copyfile(TLG_CFG, utils.getUmaInstallDir().joinpath(TLG_CFG.name))
    except PermissionError:
        logger.error(
            "No permission to write to the Uma Musume install dir.\n"
            "Please copy temp/dxgi.dll & localify/config.json there yourself.\n"
            f"Install dir: {utils.getUmaInstallDir()}"
        )
        raise
    except FileExistsError:
        pass # Overwrite requested, copy dll
    # Copy DLLs
    shutil.copyfile(tlg_dll, utils.getUmaInstallDir().joinpath("tlg.dll"))
    for name in (TLG_TARGETS if tlg_idx == -1 else (TLG_TARGETS[tlg_idx],)):
        try:
            shutil.copyfile(loader_dll, utils.getUmaInstallDir().joinpath(name))
        except FileExistsError:
            # New install (no config) but dll exists. idx == -1
            logger.info(
                f"File {name} already exists, renaming...\n"
                "You may need to adjust configs if you use other mods."
            )
            continue
        logger.info(f"TLG successfully installed as {name}")
        break


def main():
    if not constants.IS_WIN:
        return
    logger.setFile("install.log")
    logger.info("Creating UmaTL config file.")
    patch.UmaTlConfig.createDefault()
    get_tlg = input("Install TLG for UI translations? [y]es, [n]o: ")
    if get_tlg.startswith("n"):
        return

    TMP_STORE.mkdir(exist_ok=True)
    try:
        download_tlg()
    except Exception:
        logger.debug("Error info", exc_info=True)
        logger.warning(
            "Not everything went right, check the steps on GitHub or ask in the Discord if you need help.\n"
            "Details are in logs/install.log, please include it when asking."
        )
    else:
        shutil.rmtree(str(TMP_STORE))


if __name__ == "__main__":
    main()
