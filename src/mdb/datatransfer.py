# todo: incorporate this functionality properly across the patch
from Levenshtein import ratio as similarity
from common import logger

class DataTransfer:
    def __init__(self, file = None):
        self.file = file
        self.offset = 0
        self.simRatio = 0.9

    def __call__(self, textData):
        if self.file is None:
            return

        textSearch = True
        targetBlock = None
        textBlocks = self.file.textBlocks
        txtIdx = 0
        if "blockIdx" in textData:
            txtIdx = max(textData["blockIdx"] - 1 - self.offset, 0)
            if txtIdx < len(textBlocks):
                targetBlock = textBlocks[txtIdx]
                if similarity(targetBlock["jpText"], textData["jpText"]) < self.simRatio:
                    targetBlock = None
                else:
                    textSearch = False

        if textSearch:
            logger.debug("Searching by text")
            for i, block in enumerate(textBlocks):
                if similarity(block["jpText"], textData["jpText"]) > self.simRatio:
                    logger.debug(f"Found text at block {i}")
                    self.offset = txtIdx - i
                    targetBlock = block
                    break
            if not targetBlock:
                logger.info(f"At bIdx/time {textData.get('blockIdx', textData.get('time', 'no_idx'))}: jpText not found in file.")

        if targetBlock:
            textData["enText"] = targetBlock["enText"]
            if "enName" in targetBlock:
                textData["enName"] = targetBlock["enName"]
