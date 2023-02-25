import sys
from os.path import realpath
import re
# import sqlite3

sys.path.append(realpath("src"))
from common import TranslationFile, searchFiles
import helpers

TL_FILES = {
    "skillEvo": TranslationFile("translations/mdb/skill-evolve-cond.json")
}
LOOKUP_FILES = {
    "common": TranslationFile("translations/mdb/common.json"),
    "misc": TranslationFile("translations/mdb/miscellaneous.json"),
    "stats": TranslationFile("translations/mdb/training-actions.json"),
    "races": TranslationFile("translations/mdb/race-name.json"),
    "skills": TranslationFile("translations/mdb/skill-name.json"),
    "conditions": TranslationFile("translations/mdb/conditions-name.json")
}
COMMON_LOOKUPS = helpers.readJson("src/data/mdb_static_tl.json")
    
def translate(tlFile:TranslationFile, data:list[tuple[str, str, dict[str, TranslationFile]]]):
    for jp, en in tlFile.textBlocks._nativeData.items():
        if en: 
            continue
        for reSearch, repl, lookups in data:
            m = re.fullmatch(reSearch, jp)
            if not m:
                continue
            # tl the groups
            groups:dict[str, str] = m.groupdict("")
            for gName, jpTerm in groups.items():
                # special case
                if gName == "cond":
                    jpTerm = jpTerm.replace("〇", "○")
                if lookups:
                    file = lookups.get(gName)
                    if isinstance(file, TranslationFile):
                        lookupData = file.textBlocks 
                    elif isinstance(file, (tuple, list)):
                        lookupData = dict()
                        for x in file:
                            lookupData.update(x.textBlocks._nativeData)
                else:
                    lookupData = None
                enTerms = list()
                for term in jpTerm.split("、"):
                    if lookups:
                        enTerms.append(lookupData.get(term, COMMON_LOOKUPS.get(term, term)))
                    else:
                        enTerms.append(COMMON_LOOKUPS.get(term, term))
                    groups[gName] = ", ".join(enTerms)
            tlFile.textBlocks[jp] = re.sub(r"\$([a-z]+)", lambda m: groups.get(m.group(1)), repl)
            break
    tlFile.save()

def main():
    translate(
        TL_FILES["skillEvo"],
        [
            (r"基礎能力\[(?P<stat>.+?)\]が(?P<n>\d+)以上になる", r"Reach ≥$n $stat", {"stat": LOOKUP_FILES["stats"]}),
            (r"＜?(?P<stat>[^＜＞]+?)＞?の?スキルを(?P<n>\d+)個以上所持する", r"Learn $n $stat skills", {"stat": (LOOKUP_FILES["stats"], LOOKUP_FILES["common"])}),
            (r"(?P<type>.+?)で(?P<pos>\d+)着以内を(?P<n>\d+)回以上とる", r"Finish top $pos in $n $type races", {"type": None}),
            (r"(?P<race>.+?)で(?P<pos>\d+)着以内になる", r"Finish top $pos in $race", {"race": LOOKUP_FILES["races"]}),
            (r"作戦「(?P<strat>.+?)」かつ(?P<fav>\d+)番人気で(?P<type>.+?)を(?P<n>\d+)勝以上する", r"Win $n $type races as $strat, being favorite #$fav", {"strat": LOOKUP_FILES["common"], "type": LOOKUP_FILES["common"]}),
            (r"作戦「(?P<strat>.+?)」で(?P<type>.+?)を(?P<n>\d+)勝以上する", r"Win $n $type races as $strat", {"strat": LOOKUP_FILES["common"]}),
            (r"(?P<type>[^「]+?)の(?P<grade>.+?)を(?P<n>\d+)勝以上する", r"Win $n $type $grade races", {"type": LOOKUP_FILES["common"]}),
            (r"(?P<grade>G[Ⅰ123]+)を(?P<n>\d+)勝以上する", r"Win $n $grade races", None),
            (r"(?P<race>.+?)を二連覇する", r"Win $race twice consecutively", {"race": LOOKUP_FILES["races"]}),
            (r"(?P<type>.+?)(?:レース)?を(?P<n>\d+)勝以上する", r"Win $n $type races", {"type": LOOKUP_FILES["common"]}),
            (r"(?P<type>.+?)レースを勝利する", r"Win a $type race", {"type": LOOKUP_FILES["common"]}),
            (r"(?P<race>.+?)を勝利する", r"Win $race", {"race": LOOKUP_FILES["races"]}),
            (r"(?P<race>.+?)に出走する", r"Race in $race", {"race": LOOKUP_FILES["races"]}),
            (r"ファン数が(?P<n>\d+)人以上になる", r"Gain $n fans", None),
            (r"スキル「(?P<skill>.+?)」を所持する", r"Learn the skill '$skill'", {"skill": LOOKUP_FILES["skills"]}),
            (r"育成イベント「(?P<event>.+)」を発生させる", r"Trigger the '$event' event", None),
            (r"育成イベント「(?P<event>.+)」を(?P<mood>.+)以上の状態で発生させる", r"Trigger the '$event' event with ≥$mood motivation", None),
            (r"育成中に1回以上「(?P<condition>.+?)」になる", r"Become '$condition' once", {"condition": LOOKUP_FILES["conditions"]}),
            (r"(?P<loc>.+?レース場)で(?P<n>\d+)勝以上する", r"Win $n races at $loc", {"loc": LOOKUP_FILES["misc"]}),
            (r"「(?P<cond>.+?[〇○]?)」を持つ状態で育成を完了する", r"Finish training with the $cond condition", {"cond": LOOKUP_FILES["conditions"]})
        ]
    )

main()