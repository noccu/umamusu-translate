
import sys
from os.path import realpath
import re

sys.path.append(realpath("src"))
import helpers


gTarget = "translations/mdb/race-name.json"
gMatches = (
    (re.compile(r"(.+?)[ （]([A-Z ]{4,})）?"), r"{0} (\2)"),
    (re.compile(r"ルームマッチ (.+) 条件"), r"Room Match: {0} (Custom)"),
    (re.compile(r"ルームマッチ (.+)"), r"Room Match: {0}"),
    (re.compile(r"練習 (.+)"), r"Practice: {0}"),
    (re.compile(r"チーム対抗戦　短距離代表(.)?$"), r"Team Stadium: Short \1"),
    (re.compile(r"チーム対抗戦　マイル代表(.)?$"), r"Team Stadium: Mile \1"),
    (re.compile(r"チーム対抗戦　中距離代表(.)?$"), r"Team Stadium: Medium \1"),
    (re.compile(r"チーム対抗戦　長距離代表(.)?$"), r"Team Stadium: Long \1"),
    (re.compile(r"チーム対抗戦　ダート代表(.)?$"), r"Team Stadium: Dirt \1"),
    (re.compile(r"^(.+?) 決勝"), r"{0} Final"),
    (re.compile(r"チャンピオンズミーティング (.+?) 決勝"), r"Champion's Meet: {0} Final"),
    (re.compile(r"チャンピオンズミーティング (.+?)"), r"Champion's Meet: {0}")
)

# gCM = {
#     "カプリコーン杯": "Capricorn Cup",
#     "アクエリアス杯": "Aquarius Cup",
#     "ピスケス杯": "Pisces Cup",
#     "アリエス杯": "Aries Cup",
#     "タウラス杯": "Taurus Cup",
#     "ジェミニ杯": "Gemini Cup",
#     "キャンサー杯": "Cancer Cup",
#     "レオ杯": "Leo Cup",
#     "ヴァルゴ杯": "Virgo Cup",
#     "ライブラ杯": "Libra Cup",
#     "スコーピオ杯": "Scorpio Cup",
#     "サジタリウス杯": "Sagittarius Cup"
# }


def main():
    data = helpers.readJson(gTarget)
    t = data.get("text")
    for k, v in t.items():
        if v: continue
        for r, s in gMatches:
            m = r.match(k)
            if m:
                l = t.get(m[1])
                if l:
                    t[k] = m.expand(s.format(l))
                else:
                    t[k] = m.expand(s).strip()
                break
    helpers.writeJson(gTarget, data)

if __name__ == '__main__':
    main()