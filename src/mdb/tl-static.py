import sys
from os.path import realpath
import re
# import sqlite3

sys.path.append(realpath("src"))
from common import TranslationFile, searchFiles
import helpers

TL_FILES = {
    "skillEvo": TranslationFile("translations/mdb/skill-evolve-cond.json"),
    "transferReqs": TranslationFile("translations/mdb/special-transfer-requirements.json"),
    "missions": TranslationFile("translations/mdb/missions.json")
}
LOOKUP_FILES = {
    "common": TranslationFile("translations/mdb/common.json"),
    "misc": TranslationFile("translations/mdb/miscellaneous.json"),
    "stats": TranslationFile("translations/mdb/training-actions.json"),
    "races": TranslationFile("translations/mdb/race-name.json"),
    "skills": TranslationFile("translations/mdb/skill-name.json"),
    "conditions": TranslationFile("translations/mdb/conditions-name.json"),
    "epithets": TranslationFile("translations/mdb/uma-epithet.json"),
    "training": TranslationFile("translations/mdb/training-actions.json"),
}
COMMON_LOOKUPS = helpers.readJson("src/data/mdb_static_tl.json")
    
def translate(tlFile:TranslationFile, data:list[tuple[str, str, dict[str, TranslationFile]]], multi=False):
    for jp, en in tlFile.textBlocks._nativeData.items():
        if en: 
            continue
        matchText = jp
        for reSearch, repl, lookups in data:
            m = re.fullmatch(reSearch, matchText, re.MULTILINE)
            if not m:
                continue
            # tl the groups
            groups:dict[str, str] = m.groupdict("")
            for gName, jpTerm in groups.items():
                # special case
                if gName == "cond":
                    jpTerm = jpTerm.replace("〇", "○")
                if gName in ("prefix", "suffix"):
                    continue
                lookupData = None
                if lookups:
                    file = lookups.get(gName)
                    if isinstance(file, TranslationFile):
                        lookupData = file.textBlocks 
                    elif isinstance(file, (tuple, list)):
                        lookupData = dict()
                        for x in file:
                            lookupData.update(x.textBlocks._nativeData)
                enTerms = list()
                for term in re.split(r"、|, ", jpTerm):
                    if lookupData:
                        enTerms.append(lookupData.get(term, COMMON_LOOKUPS.get(term, term)))
                    else:
                        enTerms.append(COMMON_LOOKUPS.get(term, term))
                    groups[gName] = ", ".join(enTerms)
            tlFile.textBlocks[jp] = re.sub(r"\$([a-z]+)", lambda m: groups.get(m.group(1)), repl, flags=re.IGNORECASE)
            if multi:
                matchText = tlFile.textBlocks[jp]
                continue
            else:
                break # Limit to 1 replacement; safer and faster
    tlFile.save()

def partialTl(a, b, c):
    return (fr"(?P<prefix>.*?){a}(?P<suffix>.*?)", f"$prefix{b}$suffix", c)

def main():
    translate(TL_FILES["skillEvo"],
        [
            (r"基礎能力\[(?P<stat>.+?)\]が(?P<n>\d+)以上になる", "Reach ≥$n $stat", {"stat": LOOKUP_FILES["stats"]}),
            (r"＜?(?P<stat>[^＜＞]+?)＞?の?スキルを(?P<n>\d+)個以上所持する", "Learn $n $stat skills", {"stat": (LOOKUP_FILES["stats"], LOOKUP_FILES["common"])}),
            (r"(?P<type>.+?)で(?P<pos>\d+)着以内を(?P<n>\d+)回以上とる", "Finish top $pos in $n $type races", {"type": None}),
            (r"(?P<race>.+?)で(?P<pos>\d+)着以内になる", "Finish top $pos in $race", {"race": LOOKUP_FILES["races"]}),
            (r"作戦「(?P<strat>.+?)」かつ(?P<fav>\d+)番人気で(?P<type>.+?)を(?P<n>\d+)勝以上する", "Win $n $type races as $strat, being favorite #$fav", {"strat": LOOKUP_FILES["common"], "type": LOOKUP_FILES["common"]}),
            (r"作戦「(?P<strat>.+?)」で(?P<type>.+?)を(?P<n>\d+)勝以上する", "Win $n $type races as $strat", {"strat": LOOKUP_FILES["common"]}),
            (r"(?P<type>[^「]+?)の(?P<grade>.+?)を(?P<n>\d+)勝以上する", "Win $n $type $grade races", {"type": LOOKUP_FILES["common"]}),
            (r"(?P<grade>G[Ⅰ123]+)を(?P<n>\d+)勝以上する", "Win $n $grade races", None),
            (r"(?P<race>.+?)を二連覇する", "Win $race twice consecutively", {"race": LOOKUP_FILES["races"]}),
            (r"(?P<type>.+?)(?:レース)?を(?P<n>\d+)勝以上する", "Win $n $type races", {"type": LOOKUP_FILES["common"]}),
            (r"(?P<type>.+?)レースを勝利する", "Win a $type race", {"type": LOOKUP_FILES["common"]}),
            (r"(?P<race>.+?)を勝利する", "Win $race", {"race": LOOKUP_FILES["races"]}),
            (r"(?P<race>.+?)に出走する", "Race in $race", {"race": LOOKUP_FILES["races"]}),
            (r"ファン数が(?P<n>\d+)人以上になる", "Gain $n fans", None),
            (r"スキル「(?P<skill>.+?)」を所持する", "Learn the skill '$skill'", {"skill": LOOKUP_FILES["skills"]}),
            (r"育成イベント「(?P<event>.+)」を発生させる", "Trigger the '$event' event", None),
            (r"育成イベント「(?P<event>.+)」を(?P<mood>.+)以上の状態で発生させる", "Trigger the '$event' event with ≥$mood motivation", None),
            (r"育成中に1回以上「(?P<condition>.+?)」になる", "Become '$condition' once", {"condition": LOOKUP_FILES["conditions"]}),
            (r"(?P<loc>.+?レース場)で(?P<n>\d+)勝以上する", "Win $n races at $loc", {"loc": LOOKUP_FILES["misc"]}),
            (r"「(?P<cond>.+?[〇○]?)」を持つ状態で育成を完了する", "Finish training with the $cond condition", {"cond": LOOKUP_FILES["conditions"]})
        ]
    )
    translate(TL_FILES["missions"],
        [
            (r"チーム競技場で(?P<dist>.{3,3})代表に(?P<n>\d+)回勝利しよう", "Win the $dist race in stadium $n times", {"dist": LOOKUP_FILES["common"]})
        ]
    )
    translate(TL_FILES["transferReqs"],
        [
            partialTl(r"・脚質適[性正]：(?P<strat>.+?)<color=#(?P<color>[A-Z0-9]+)>「(?P<rank>[A-Z+]+)」</color>以上", "・Strategy: $strat <color=#$color>$rank</color> or higher", {"strat": LOOKUP_FILES["common"]}),
            partialTl(r"・距離適[性正]：(?P<dist>.+?)<color=#(?P<color>[A-Z0-9]+)>「(?P<rank>[A-Z+]+)」</color>以上", "・Distance: $dist <color=#$color>$rank</color> or higher", {"dist": LOOKUP_FILES["common"]}),
            partialTl(r"・バ場適[性正]：(?P<field>.+?)<color=#(?P<color>[A-Z0-9]+)>「(?P<rank>[A-Z+]+)」</color>以上", "・Field: $field <color=#$color>$rank</color> or higher", {"field": LOOKUP_FILES["common"]}),
            partialTl(r"・(?P<stat>.+?)<color=#(?P<color>[A-Z0-9]+)>「(?P<rank>[A-Z+]+)」</color>以上", "・$stat <color=#$color>$rank</color> or higher", {"stat": LOOKUP_FILES["training"]}),
            partialTl(r"・<color=#(?P<color>[A-Z0-9]+)>(?P<races>.+?)</color>のいずれかで<color=#FF911C>(?P<n>\d+)勝</color>する", "・Won <color=#$color>$n</color> of <color=#$color>$races</color>", {"races": LOOKUP_FILES["races"]}),
            partialTl(r"・<color=#(?P<color>[A-Z0-9]+)>(?P<raceA>.+?)</color>と<color=#FF911C>(?P<raceB>.+?)</color>を勝利する", "・Won <color=#$color>$raceA</color> and <color=#$color>$raceB</color>", {"raceA": LOOKUP_FILES["races"], "raceB": LOOKUP_FILES["races"]}),
            partialTl(r"・<color=#(?P<color>[A-Z0-9]+)>(?P<num>\d+)回?</color>以上レースに出走し、勝率が<color=#[A-Z0-9]+>(?P<rate>\d+)[％%]</color>以上になる", "・Entered <color=#$color>$num</color> races, with <color=#$color>$rate%</color>win rate", None),
            partialTl(r"・<color=#(?P<color>[A-Z0-9]+)>(?P<num>\d+)回</color>以上レースに出走し、全レースで<color=#[A-Z0-9]+>(?P<pos>\d+)着</color>以内で(?:\\n　)?育成を完了する", "・Entered <color=#$color>$num</color> races, finishing no lower than pos <color=#$color>$pos</color>", None),
            partialTl(r"・育成中に<color=#(?P<color>[A-Z0-9]+)>(?P<num>\d+)回</color>以上出走し、かつ出走レースが全て<color=#FF911C>(?P<field>.+?)</color>のまま(?:\\n　)?育成を完了する", "・Entered <color=#$color>$num</color> races, all of which on <color=#$color>$field</color>", {"field": LOOKUP_FILES["common"]}),
            partialTl(r"・<color=#FF911C>オープン</color>以下で負けずに、<color=#FF911C>重賞</color>を<color=#FF911C>5連勝</color>する", "・Entered <color=#$color>$num</color> races, all of which on <color=#$color>$field</color>", {"field": LOOKUP_FILES["common"]}),
            partialTl(r"・<color=#(?P<color>[A-Z0-9]+)>(?P<type>重賞|G[ⅠⅡⅢ])</color>を<color=#FF911C>(?P<n>\d+)勝</color>する", "・Won <color=#$color>$n $type</color> races", None),
            partialTl(r"・ ?<color=#(?P<color>[A-Z0-9]+)>(?P<type>重賞|G[ⅠⅡⅢ])</color>を勝利する", "・Won a <color=#$color>$type</color> race", None),
            partialTl(r"・<color=#(?P<color>[A-Z0-9]+)>(?P<races>.+?)</color>を勝利する", "・Won <color=#$color>$races</color>", {"races": LOOKUP_FILES["races"]}),
            partialTl(r"（二つ名<color=#(?P<color>[A-Z0-9]+)>「(?P<nick>.+?)」</color>所持）", "(Has epithet <color=#$color>$nick</color>)", {"nick": LOOKUP_FILES["epithets"]}),
        ], multi=True
    )

main()