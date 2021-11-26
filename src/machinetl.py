import asyncio
import websockets
from websockets import server
import json
import common
import textprocess

# Globals & Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-g <group> [-id <id>] [-src <file>]",
                 "-src overwrites other options")
TARGET_TYPE = args.getArg("-t", "story").lower()
TARGET_GROUP = args.getArg("-g", False)
TARGET_ID = args.getArg("-id", False)
TARGET_FILE = args.getArg("-src", False)

async def handler(client: server.WebSocketServerProtocol, path):
    print("New client connected")
    tl = Translator(client)
    async for message in client:
        msgData = json.loads(message)
        if msgData['action'] == "connect":
            asyncio.create_task(tl.translate())
        elif msgData['action'] == "tl-res":
            tl.recvTl(msgData)
        else:
            print(f"Unknown message: {message}")
            continue

async def startServer():
    async with websockets.serve(handler, "localhost", 61017):
        global STOP
        STOP = asyncio.Future()
        await STOP  # run until stopped
class Translator:
    def __init__(self, client: server.WebSocketServerProtocol):
        if TARGET_FILE: self.files = [TARGET_FILE]
        else: self.files = common.searchFiles(TARGET_TYPE, TARGET_GROUP, TARGET_ID)
        self.client = client
        self.loop = asyncio.get_running_loop()

    def _entryGenerator(self, file: common.TranslationFile):
        for block in file.getTextBlocks():
            if block['jpText']:
                yield block
            if 'coloredText' in block:
                for entry in block['coloredText']:
                    yield entry
            if 'choices' in block:
                for entry in block['choices']:
                    yield entry

    def _fileGenerator(self):
        for file in self.files:
            yield common.TranslationFile(file)

    async def translate(self):
        for file in self._fileGenerator():
            for entry in self._entryGenerator(file):
                # Skip already translated text
                if not entry['enText']:
                    text = textprocess.process(entry['jpText'], {"noNewlines": True})
                    entry['enText'] = textprocess.process(await self.requestTl(text), {"lineLen": False, "replace": True}) # defer to default
            file.save()
        await self.client.close()
        STOP.set_result(True)

    async def requestTl(self, text: str):
        await self.client.send(json.dumps({
            'action': "tl",
            'text': text,
            }, ensure_ascii=False))
        self.currentTl = self.loop.create_future()
        return await self.currentTl

    def recvTl(self, tl):
        self.currentTl.set_result(tl['text'])


def main():
    asyncio.run(startServer())
    # #todo: start headless browser

main()