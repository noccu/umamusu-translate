import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

import textprocess
from common.constants import NAMES_BLACKLIST
from common.utils import isEnglish
from . import display

if TYPE_CHECKING:
    from common.types import TranslationFile
    from .app import Editor


class Navigator:
    def __init__(self, master: "Editor") -> None:
        # todo: turn this class into a frame that can be composited in
        chapter_label = tk.Label(master.root, text="Chapter")
        chapter_label.grid(row=0, column=0)
        chapter_dropdown = ttk.Combobox(master.root, width=35)
        chapter_dropdown.bind("<<ComboboxSelected>>", self.change_chapter)
        chapter_dropdown.bind("<KeyRelease>", self.searchChapters)
        chapter_dropdown.config(values=("No files loaded",))
        chapter_dropdown.current(0)
        chapter_dropdown.search = None
        chapter_dropdown.grid(row=0, column=1, sticky=tk.NSEW)

        textblock_label = tk.Label(master.root, text="Block")
        textblock_label.grid(row=0, column=2)
        block_dropdown = ttk.Combobox(master.root, width=35)
        block_dropdown.bind("<<ComboboxSelected>>", self.change_block)
        block_dropdown.config(values=("No file loaded",))
        block_dropdown.current(0)
        block_dropdown.grid(row=0, column=3, sticky=tk.NSEW)

        self.cur_chapter: int = None
        self.cur_block: int = 0
        self.cur_data: dict = None
        self.cur_file: "TranslationFile" = None
        self.chapterPicker = chapter_dropdown
        self.blockPicker = block_dropdown
        self.master = master
        self.fileMan = master.fileMan

    def change_chapter(self, chapter):
        if chapter == self.cur_chapter:
            return
        if not isinstance(chapter, int):
            chapter = self.chapterPicker.current()
        else:
            self.chapterPicker.current(chapter)  # Update the ui

        if self.cur_file:
            self.fileMan.save_block(self)
            self.cur_file.lastBlock = self.cur_block
        if self.chapterPicker.search:
            chapter = self.chapterPicker.search[chapter]
            self.resetChapterSearch()

        cur_file = self.fileMan.loadFile(chapter)
        self.cur_file = cur_file
        self.cur_chapter = chapter
        self.cur_block = getattr(self.cur_file, "lastBlock", 0)
        self.blockPicker["values"] = [
            f"{i+1} - {block['jpText'][:16]}" for i, block in enumerate(cur_file.textBlocks)
        ]
        self.change_block(self.cur_block, newFile=True)  # Takes care of loading

        ll = textprocess.calcLineLen(cur_file, False) or self.master.textBoxEn.DEFAULT_WIDTH
        self.master.textBoxEn.config(width=ll)
        self.master.textBoxJp.config(width=ll)

    def reload_chapter(self, event=None):
        self.cur_file.reload()
        self.cur_data = self.fileMan.load_block(self.cur_file, self.cur_block)

    def prev_ch(self, event=None):
        if self.cur_chapter - 1 > -1:
            self.change_chapter(self.cur_chapter - 1)
        else:
            print("Reached first chapter")

    def next_ch(self, event=None):
        #! ugh
        if self.cur_chapter + 1 < len(self.fileMan.files):
            self.change_chapter(self.cur_chapter + 1)
        else:
            print("Reached last chapter")

    def change_block(self, idx, dir=0, newFile=False):
        if not isinstance(idx, int):  # UI event (setting picker directly)
            idx = self.blockPicker.current()
        
        if not newFile:
            self.fileMan.save_block(self)
            if self.master.options.saveOnBlockChange.get():
                self.fileMan.saveFile()

        fileLen = len(self.cur_file.textBlocks)
        if dir != 0 and self.master.options.skip_translated.get():
            while 0 < idx < fileLen:
                data = self.cur_file.textBlocks[idx]
                if data["enText"] or isEnglish(data["jpText"]):
                    idx += dir
                else:
                    break
            idx = min(idx, fileLen - 1)

        self.blockPicker.current(idx)
        self.cur_block = idx
        self.cur_data = self.fileMan.load_block(self.cur_file, idx)

        # UI updates
        nextIdx = self.cur_data.get("nextBlock", idx + 2) - 1
        if idx == 0:
            display.setActive(self.btnPrev, False)
            self.btnPrev["text"] = "Start"
        else:
            display.setActive(self.btnPrev, True)
            self.btnPrev["text"] = "Prev"
        if nextIdx < 1 or nextIdx > fileLen:
            display.setActive(self.btnNext, False)
            self.btnNext["text"] = "End"
        else:
            display.setActive(self.btnNext, True)
            self.btnNext["text"] = f"Next ({idx} -> {nextIdx}!)" if nextIdx - idx > 1 else "Next"
        
        #  todo: events?
        if self.master.merging:
            self.master.mergeWWindow.evBlockUpdated(self.cur_data, idx)

    def prev_block(self, event=None):
        idx = self.cur_block - 1
        if idx < 0:
            print("Reached start of file")
            return
        self.change_block(idx, dir=-1)

    def next_block(self, event=None):
        idx = self.cur_data.get("nextBlock", self.cur_block + 2) - 1
        if idx < 1 or idx >= len(self.cur_file.textBlocks):
            print("Reached end of file")
            return
        self.change_block(idx, dir=1)

    def searchChapters(self, event=None):
        if event.keysym in ("Up", "Down", "Left", "Right", "Return"):
            return
        search = self.chapterPicker.get()
        if search == "":
            self.chapterPicker["values"] = self.fileMan.formattedFiles
            self.chapterPicker.search = None
        else:
            searchList = {
                item: i
                for i, item in enumerate(self.fileMan.formattedFiles)
                if search in item
            }
            self.chapterPicker["values"] = (
                list(searchList.keys()) if searchList else ["No matches found"]
            )
            self.chapterPicker.search = list(searchList.values()) if searchList else None

    def resetChapterSearch(self):
        self.chapterPicker["values"] = self.fileMan.formattedFiles
        self.chapterPicker.search = None

    def nextMissingName(self):
        for idx, block in enumerate(self.cur_file.textBlocks):
            if not block.get("enName") and block.get("jpName") not in NAMES_BLACKLIST:
                self.change_block(idx)
