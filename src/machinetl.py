import asyncio
import websockets
from websockets import server
import json
import common

# Globals & Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-g <group> [-id <id>] [-src <file>]",
                 "-src overwrites other options")
TARGET_GROUP = args.getArg("-g", False)
TARGET_ID = args.getArg("-id", False)
TARGET_FILE = args.getArg("-src", False)

async def handler(client: server.WebSocketServerProtocol, path):
    print(f"New client connected")
    async for message in client:
        msgData = json.loads(message)
        if msgData['action'] == "connect":
            fileData = startTranslation(client, TARGET_GROUP, TARGET_ID)
        elif msgData['action'] == "tl-res":
            recvTl(dataBlock, msgData)
        else:
            print(f"Unknown message: {message}")
            continue

        try:
            dataBlock = next(fileData)
            # translate(client, dataBlock)
            await requestTl(client, dataBlock)
        except StopIteration:
            await client.close()
            STOP.set_result(True)

# async def translate(client, dataBlock):
        
async def startServer():
    async with websockets.serve(handler, "localhost", 61017):
        global STOP 
        STOP = asyncio.Future()
        await STOP  # run until stopped

def startTranslation(client, group, id):
    if TARGET_FILE: files = [TARGET_FILE]
    else: files = common.searchFiles(group, id)

    for file in files:
        parsedFile = common.readJsonFile(file)
        fileData = getFileData(parsedFile)
        for dataBlock in fileData:
            yield dataBlock
        # parsedFile is updated
        common.writeJsonFile(file, parsedFile)


def getFileData(fileData):
    for _, content in fileData.items():
        return (dataBlock for dataBlock in content if not dataBlock['enText'])

async def requestTl(client: server.WebSocketServerProtocol, dataBlock: dict):
    await client.send(json.dumps({
        'action': "tl",
        'text': dataBlock['jpText']
        }, ensure_ascii=False))

def recvTl(data, tl):
    data['enText'] = tl['text']

def main():
    asyncio.run(startServer())
    # #todo: start headless browser

if not TARGET_GROUP:
    print("Group is required. Pass arg -h for usage.")
    raise SystemExit
main()