from os import path
import common
import csv

args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-n <db-translate uma-name.csv> [-src <file to process>]")
NAMES_FILE = args.getArg("-n", False)
TARGET_FILE = args.getArg("-src", False)
TARGET_TYPE = args.getArg("-t", "story").lower()
TARGET_GROUP = args.getArg("-g", False)
TARGET_ID = args.getArg("-id", False)


def createDict():
    global NAMES_FILE
    if not NAMES_FILE: 
        NAMES_FILE = "../umamusume-db-translate/src/data/uma-name.csv"
        if not path.exists(NAMES_FILE):
            raise FileNotFoundError("You must specify the uma-name.csv file.")
        print(f"Using auto-found names file {path.realpath(NAMES_FILE)}")
    names = dict()
    with open(NAMES_FILE, "r", newline='', encoding="utf8") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in reader:
            names[row[0]] = row[1]

    # a few extras. misc.csv doesn't provide everything
    # todo: probably use an external file?
    names['駿川たづな'] = "Hayakawa Tazuna"
    names['秋川理事長'] = "Chairwoman Akikawa"
    names['樫本代理'] = "Acting Chair Kashimoto"
    # names['モノローグ'] = "Monologue"
    names['記者A'] = "Reporter A"
    names['記者B'] = "Reporter B"
    names['記者たち'] = "Reporters"
    names['インタビューアーA'] = "Interviewer A"
    names['インタビューアーB'] = "Interviewer B"
    names['ウマ娘'] = "Uma Musume"
    names['ウマ娘A'] = "Uma Musume A"
    names['ウマ娘B'] = "Uma Musume B"
    names['後輩のウマ娘A'] = "Junior UmaMusu A"
    names['後輩のウマ娘B'] = "Junior UmaMusu B"
    names['同期のウマ娘'] = "Contemporary UmaMusu"
    names['そばかす顔のウマ娘'] = "Freckled UmaMusu"
    names['地元ウマ娘'] = "Local Uma Musume"
    names['どこか上品なウマ娘'] = "Somewhat Refined Uma Musume"
    names['スーツのウマ娘'] = "Suited Uma Musume"
    names['ウマ娘たち'] = "Uma Musumes"
    names['？？？'] = "???"
    names['ニュースキャスター'] = "Newscaster"
    names['ウマ娘ファンA'] = "UmaMusu Fan A"
    names['ウマ娘ファンB'] = "UmaMusu Fan B"
    names['教師'] = "Teacher"
    names['先生'] = "Teacher"
    names['スタッフA'] = "Staff A"
    names['スタッフＡ'] = "Staff A"
    names['スタッフB'] = "Staff B"
    names['スタッフＢ'] = "Staff B"
    names['スタッフC'] = "Staff C"
    names['スタッフＣ'] = "Staff C"
    names['観客A'] = "Spectator A"
    names['観客B'] = "Spectator B"
    names['観客C'] = "Spectator C"
    names['観客たち'] = "Crowd"
    names['観客'] = "Crowd"
    names['歓声'] = "Cheers"
    names['実況'] = "Coverage"
    names['イベント実況'] = "Event Coverage"
    names['テレビ'] = "TV"
    names['テレビの音'] = "TV Report"
    names['新人トレーナーA'] = "Rookie Trainer A"
    names['新人トレーナーＡ'] = "Rookie Trainer A"
    names['新人トレーナーB'] = "Rookie Trainer B"
    names['新人トレーナーＢ'] = "Rookie Trainer B"
    names['中堅トレーナーA'] = "Average Trainer A"
    names['中堅トレーナーＡ'] = "Average Trainer A"
    names['中堅トレーナーB'] = "Average Trainer B"
    names['中堅トレーナーＢ'] = "Average Trainer B"
    names['ベテラントレーナーA'] = "Veteran Trainer A"
    names['ベテラントレーナーＡ'] = "Veteran Trainer A"
    names['ベテラントレーナーB'] = "Veteran Trainer B"
    names['ベテラントレーナーＢ'] = "Veteran Trainer B"
    names['トレーナーたち'] = "Trainers"
    names['男性'] = "Man"
    names['女性'] = "Woman"
    names['男の子A'] = "Boy A"
    names['女の子A'] = "Girl A"
    names['ファンの男性'] = "Male Fan"
    names['ファンの女性'] = "Female Fan"
    names['司会者'] = "Host"
    names['テレビ番組の司会'] = "TV Host"
    names['クラスメイトA'] = "Classmate A"
    names['クラスメイトＡ'] = "Classmate A"
    names['クラスメイトB'] = "Classmate B"
    names['クラスメイトＢ'] = "Classmate B"
    names['クラスメイトC'] = "Classmate C"
    names['クラスメイトＣ'] = "Classmate C"
    names['クラスメイトD'] = "Classmate D"
    names['クラスメイトＤ'] = "Classmate D"
    names['クラスメイトたち'] = "Classmates"
    names['陽気なクラスメイト'] = "Cheerful Classmate"
    names['優しいクラスメイト'] = "Gentle Classmate"
    names['商店街の人'] = "Market Person"
    names['商店街の人たち'] = "Market People"
    names['遊園地のスタッフ'] = "Amusement Park Staff"
    names['カフェ店員'] = "Cafe Employee"
    names['子ども'] = "Child"
    names['子どもたち'] = "Children"
    names['ファンの子ども'] = "Fan's Child"
    names['ファンの子どもたち'] = "Fan's Children"
    names['広報委員長'] = "PR Committee Chair"
    names['広報委員'] = "PR Committee Member"
    names['風紀委員たち'] = "PM Committee Member"
    names['宇宙人'] = "Alien"
    names['2人'] = "Both"
    names['3人'] = "All 3"
    names['みんな'] = "Everyone"
    names['通行人A'] = "Passerby A"
    names['通行人B'] = "Passerby B"
    names['カメラマンA'] = "Cameraman A"
    names['カメラマンB'] = "Cameraman B"
    names['SP隊長'] = "SP Commander"
    names['ネコ'] = "Cat"
    names['ドラゴン'] = "Dragon"
    return names

def translate(namesDict):
    if TARGET_FILE: files = [TARGET_FILE]
    else: files = common.searchFiles(TARGET_TYPE, TARGET_GROUP, TARGET_ID)

    for file in files:
        file = common.TranslationFile(file)
        for block in file.getTextBlocks():
            name = block['jpName']
            if name and name in namesDict:
                block['enName'] = namesDict[name]
        file.save()

def main():
    dict = createDict()
    translate(dict)
    # print(file.data)
    # file.save()

main()