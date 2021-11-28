from os import path
import common
import csv

args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-n <db-translate uma-name.csv> [-src <file to process>]")
NAMES_FILE = args.getArg("-n", False)
TARGET_FILE = args.getArg("-src", False)
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
    names['モノローグ'] = "Monologue"
    names['記者A'] = "Reporter A"
    names['記者B'] = "Reporter B"
    names['後輩のウマ娘A'] = "Junior UmaMusu A"
    names['後輩のウマ娘B'] = "Junior UmaMusu B"
    names['同期のウマ娘'] = "Contemporary UmaMusu"
    return names

def translate(namesDict):
    if TARGET_FILE: files = [TARGET_FILE]
    else: files = common.searchFiles(TARGET_GROUP, TARGET_ID)

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