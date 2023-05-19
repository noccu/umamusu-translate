import common
import helpers
from pathlib import Path

snep = Path("translations/snep").glob("story_*")

for file in snep:
    if "_H" == file.stem[5:7]:
        storyType = "home"
        storyId = f"{file.stem[:7]}{file.stem[7].zfill(5)}_{file.stem[9].zfill(2)}{file.stem[10:]}"
        sid = common.StoryId.parseFromPath(storyType, storyId)
    else:
        storyType = "story"
        sid = common.StoryId.parseFromPath(storyType, file.stem)

    extract = common.searchFiles(storyType, sid.group, sid.id, sid.idx, sid.set)
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
