import asyncio
import websockets
from websockets import server
import json
import common

TARGET_GROUP = "08"
TARGET_ID = "0000"
#todo: argument parsing

async def handler(client: server.WebSocketServerProtocol, path):
    print(f"New client connected")
    async for message in client:
        msgData = json.loads(message)
        if msgData['action'] == "connect":
            fileData = startTranslation(client, TARGET_GROUP, TARGET_ID)
        elif msgData['action'] == "tl-res":
            recvTl(dataBlock, msgData)
        else:
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

def readJsonFile(file) -> dict:
    with open(file, "r", encoding="utf8") as f:
        return json.load(f)

def writeJsonFile(file, data):
    with open(file, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def startTranslation(client, group, id):
    files = common.searchFiles(group, id)
    for file in files:
        parsedFile = readJsonFile(file)
        fileData = getFileData(parsedFile)
        for dataBlock in fileData:
            yield dataBlock
        # parsedFile is updated
        writeJsonFile(file, parsedFile)


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
    # startTranslation("08", "0000")

main()