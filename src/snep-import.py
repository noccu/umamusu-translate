import common
import helpers
from pathlib import Path
from os import system as run

snep = Path("translations/snep").glob("story_*")

for file in snep:
    g, id, idx = common.parseStoryIdFromPath("story", file.stem)

    extract = common.searchFiles("story", g, id, idx)
    if not extract:
        print("Can't find own file")
        raise SystemExit
    extract = common.TranslationFile(extract[0])
    sneptl = helpers.readJson(file)
    sneptl:dict = sneptl.get("map")
    if not sneptl:
        print("Can't find snep text")
        raise SystemExit

    for k, v in sneptl.items():
        if k.startswith("*"): continue
        try:
            idx, dunno, type, subidx = k.split(".")
            subidx = int(subidx)
        except:
            idx, dunno, type = k.split(".")
        idx = int(idx) - 1

        ourblock = extract.textBlocks[idx]
        if type == "text":
            ourblock["enText"] = v
        elif type == "choice":
            if not "choices" in ourblock:
                print("Snep disagrees about choices")
                raise SystemExit
            ourblock["choices"][subidx]["enText"]= v
    extract.save()
