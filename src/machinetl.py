import asyncio
import websockets
from websockets import server
import json
import common
import textprocess
from importlib import import_module
from pathlib import Path

# Globals & Parameter parsing
args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-g <group> [-id <id>] [-src <file>] [-ll <line length>] [-O(verwrite existing tl)]",
                 "-src overwrites other options")
TARGET_TYPE = args.getArg("-t", "story").lower()
TARGET_GROUP = args.getArg("-g", False)
TARGET_ID = args.getArg("-id", False)
TARGET_IDX = args.getArg("-idx", False)
TARGET_FILE = args.getArg("-src", False)
TARGET_MODEL = args.getArg("-model", "deepl")
LINE_LENGTH = int(args.getArg("-ll", False))
OVERWRITE_TEXT = args.getArg("-O", False)

SUGOI_ROOT = "src/data/sugoi-model"

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
        print("Server started, awaiting connection to deepl script. See README for info.")
        await STOP  # run until stopped
class Translator:
    def __init__(self, client: server.WebSocketServerProtocol = None):
        if TARGET_FILE: self.files = [TARGET_FILE]
        else: self.files = common.searchFiles(TARGET_TYPE, TARGET_GROUP, TARGET_ID, TARGET_IDX)
        if USING_SERVER:
            self.client = client
            
        if TARGET_MODEL == "deepl":
            self.loop = asyncio.get_running_loop()
        elif TARGET_MODEL == "sugoi":
            try:
                self.model = getattr(import_module("fairseq.models.transformer"), "TransformerModel")
            except ModuleNotFoundError:
                print("Error importing fairseq. See sugoi-readme.txt.")
                raise SystemExit
            self.sugoi = self.model.from_pretrained(
                f'{SUGOI_ROOT}/japaneseModel',
                checkpoint_file='big.pretrain.pt',
                source_lang='ja',
                target_lang='en',
                bpe='sentencepiece',
                sentencepiece_model=f'{SUGOI_ROOT}/spmModels/spm.ja.nopretok.model',
                #playing with params
                unkpen=10,
                no_repeat_ngram_size=4,
                iter_decode_max_iter=15,
                lenpen=0.1
                )

    def _fileGenerator(self):
        for file in self.files:
            print(f"Translating {file}...")
            yield common.TranslationFile(file)

    async def translate(self):
        for file in self._fileGenerator():
            if TARGET_MODEL == "deepl":
                for entry in file.genTextContainers():
                    # Skip already translated text
                    if OVERWRITE_TEXT or not entry['enText']:
                        text = textprocess.process(file, entry['jpText'], {"noNewlines": True})
                        entry['enText'] = textprocess.process(file, await self.requestTl(text), {"lineLen": LINE_LENGTH, "replace": True}) # defer to default
            elif TARGET_MODEL == "sugoi":
                entries = list(file.genTextContainers())
                textArray = [textprocess.process(file, entry['jpText'], {"noNewlines": True}) for entry in entries]
                resultArray = self.sugoi.translate(textArray)
                for idx, entry in enumerate(entries):
                    if OVERWRITE_TEXT or not entry['enText']:
                        entry['enText'] = textprocess.process(file, resultArray[idx], {"lineLen": LINE_LENGTH, "replace": True})
            file.save()
        if USING_SERVER:
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

async def sugoiTranslate():
    if not Path(SUGOI_ROOT).joinpath("japaneseModel", "big.pretrain.pt").is_file():
        print("Translation model not found. See sugoi-readme.txt")
        raise SystemExit
    tl = Translator()
    print("\n")
    await tl.translate()

def main():
    global USING_SERVER
    if TARGET_MODEL == "deepl":
        USING_SERVER = True
        asyncio.run(startServer())
        # #todo: start headless browser
    elif TARGET_MODEL == "sugoi":
        USING_SERVER = False
        asyncio.run(sugoiTranslate())

main()