import common
import csv

args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-n <db-translate uma-name.csv> [-src <file to process>]")
NAMES_FILE = args.getArg("-n", False)
TARGET_FILE = args.getArg("-src", False)


def createDict():
    if not NAMES_FILE: raise FileNotFoundError
    names = dict()
    with open(NAMES_FILE, "r", newline='', encoding="utf8") as csvfile:
     reader = csv.reader(csvfile, delimiter=',', quotechar='"')
     for row in reader:
         names[row[0]] = row[1]

    # a few extras. misc.csv doesn't provide everything
    # todo: probably use an external file?
    names['駿川たづな'] = "Hayakawa Tazuna"
    names['秋川理事長'] = "President Akikawa"
    names['樫本代理'] = "Acting Pres. Kashimoto"
    names['モノローグ'] = "Monologue"
    return names

def translate(namesDict):
    file = common.TranslationFile(TARGET_FILE)
    for block in file.getTextBlocks():
        name = block['jpName']
        if name and name in namesDict:
            block['enName'] = namesDict[name]
    return file

def main():
    dict = createDict()
    file = translate(dict)
    # print(file.data)
    file.save()

main()