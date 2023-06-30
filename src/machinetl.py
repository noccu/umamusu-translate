import asyncio
import json
import textprocess
from importlib import import_module
from pathlib import Path
from argparse import SUPPRESS

import websockets
from websockets import server

from common import patch
from common.files import TranslationFile
from common.constants import SUPPORTED_TYPES

SUGOI_ROOT = "src/data/sugoi-model"


async def handler(client: server.WebSocketServerProtocol, path):
    print("New client connected")
    tl = Translator(client)
    async for message in client:
        msgData = json.loads(message)
        if msgData["action"] == "connect":
            asyncio.create_task(tl.translate())
        elif msgData["action"] == "tl-res":
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
        self.files = (
            [args.src]
            if args.src
            else patch.searchFiles(
                args.type, args.group, args.id, args.idx, targetSet=args.set, changed=args.changed
            )
        )

        if USING_SERVER:
            self.client = client

        if args.model == "deepl":
            self.loop = asyncio.get_running_loop()
        elif args.model == "sugoi":
            try:
                self.model = import_module("fairseq.models.transformer").TransformerModel
            except ModuleNotFoundError:
                print("Error importing fairseq. See sugoi-readme.txt.")
                raise SystemExit
            self.sugoi = self.model.from_pretrained(
                f"{SUGOI_ROOT}/japaneseModel",
                checkpoint_file="big.pretrain.pt",
                source_lang="ja",
                target_lang="en",
                bpe="sentencepiece",
                sentencepiece_model=f"{SUGOI_ROOT}/spmModels/spm.ja.nopretok.model",
                # playing with params
                unkpen=10,
                no_repeat_ngram_size=4,
                iter_decode_max_iter=15,
                lenpen=0.1,
            )

    def _fileGenerator(self):
        for file in self.files:
            print(f"Translating {file}...")
            yield TranslationFile(file)

    async def translate(self):
        for file in self._fileGenerator():
            if args.model == "deepl":
                for entry in file.genTextContainers():
                    # Skip already translated text
                    if args.overwrite or not entry["enText"]:
                        text = textprocess.processText(
                            file, entry["jpText"], {"redoNewlines": True}
                        )
                        entry["enText"] = textprocess.processText(
                            file,
                            await self.requestTl(text),
                            {"lineLength": args.lineLength, "replaceMode": "all"},
                        )
            elif args.model == "sugoi":
                for entry in file.genTextContainers():
                    if args.overwrite or not entry["enText"]:
                        text = textprocess.processText(
                            file, entry["jpText"], {"redoNewlines": True}
                        )
                        result = self.sugoi.translate(text)
                        entry["enText"] = textprocess.processText(
                            file, result, {"lineLength": args.lineLength, "replaceMode": "all"}
                        )
            file.save()
        if USING_SERVER:
            await self.client.close()
            STOP.set_result(True)

    async def requestTl(self, text: str):
        await self.client.send(
            json.dumps(
                {
                    "action": "tl",
                    "text": text,
                },
                ensure_ascii=False,
            )
        )
        self.currentTl = self.loop.create_future()
        return await self.currentTl

    def recvTl(self, tl):
        self.currentTl.set_result(tl["text"])


async def sugoiTranslate():
    if not Path(SUGOI_ROOT).joinpath("japaneseModel", "big.pretrain.pt").is_file():
        print("Translation model not found. See sugoi-readme.txt")
        raise SystemExit
    tl = Translator()
    print("\n")
    await tl.translate()


def main():
    global args
    ap = patch.Args(
        "Machine translate files. Requires sugoi model or deepl userscript",
        types=SUPPORTED_TYPES,
    )
    ap.add_argument("-src", help="Target Translation File")
    ap.add_argument("-dst", help=SUPPRESS)
    ap.add_argument(
        "-m", "--model", choices=["deepl", "sugoi"], default="deepl", help="Translation model"
    )
    ap.add_argument(
        "-ll",
        type=int,
        default=-1,
        dest="lineLength",
        help="Line length for wrapping/newlines. 0: disable, -1: auto. Default auto.",
    )
    ap.add_argument("-O", "--overwrite", action="store_true", help="Overwrite existing tl")
    args = ap.parse_args()
    args.replaceMode = "all"

    global USING_SERVER
    if args.model == "deepl":
        USING_SERVER = True
        asyncio.run(startServer())
        # #todo: start headless browser
    elif args.model == "sugoi":
        USING_SERVER = False
        asyncio.run(sugoiTranslate())


main()
