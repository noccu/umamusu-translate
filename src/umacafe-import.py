import json
import common
import requests

DATA_URL = "https://uma.cafe/characters/__data.json"

tlFiles = [(common.TranslationFile(f), k) for (f, k) in [
    ("translations/mdb/load-screens.json", "secrets"),
    ("translations/mdb/seiyuu.json", "seiyuuName"),
    ("translations/mdb/uma-profile-ears.json", "commentEars"),
    ("translations/mdb/uma-profile-tail.json", "commentTail"),
    ("translations/mdb/uma-profile-intro.json", "introduction"),
    ("translations/mdb/uma-profile-strengths.json", "strengths"),
    ("translations/mdb/uma-profile-weaknesses.json", "weaknesses"),
    ("translations/mdb/uma-profile-family.json", "commentFamily")
    ]]

print("Retrieving data...")
data = requests.get(DATA_URL)
if data.status_code == 200:
            data = data.json().get("characterJsonList")
            for i, char in enumerate(data):
                data[i] = json.loads(char)
else: print("Failed to get data. Error: ", data.status_code)

def extractValue(o, k):
    v = o.get(k)
    if v is None: return [(None, None)]
    elif isinstance(v, list):
        return [(x.get("jp"), x.get("en")) for x in v]
    else: return [(v.get("jp"), v.get("en"))]

print("Extracting...")
maps = dict()
for file, key in tlFiles:
    maps[key] = {k.replace("\\n", ""): k for k in file.textBlocks.map.keys()}

for char in data:
    for file, key in tlFiles:
        for jp, en in extractValue(char, key):
            if jp is None or en is None: continue
            internalKey = maps[key].get(jp)
            x = file.textBlocks.get(internalKey)
            if x == "": # exists and not translated
                file.textBlocks.set(internalKey, en)

print("Saving")
for file,_ in tlFiles:
    file.save()

print("Done")
