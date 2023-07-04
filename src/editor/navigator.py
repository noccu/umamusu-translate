import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

import textprocess
from common.constants import NAMES_BLACKLIST
from common.utils import isEnglish

if TYPE_CHECKING:
    from common.types import TranslationFile

    from .main import Editor


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

        self.cur_chapter = 0
        self.cur_block = 0
        self.cur_data = None
        self.cur_file: "TranslationFile" = None
        self.chapterPicker = chapter_dropdown
        self.blockPicker = block_dropdown
        self.master = master

    def change_chapter(self, event=None):
        if self.cur_file:
            self.master.fileMan.save_block(self)
        if self.chapterPicker.search:
            cur_chapter = self.chapterPicker.search[self.chapterPicker.current()]
            self.resetChapterSearch()
        else:
            cur_chapter = self.chapterPicker.current()

        cur_file = self.master.fileMan.loadFile(cur_chapter)
        self.cur_file = cur_file
        self.cur_chapter = cur_chapter
        self.cur_block = 0
        self.blockPicker["values"] = [
            f"{i+1} - {block['jpText'][:16]}" for i, block in enumerate(cur_file.textBlocks)
        ]
        self.blockPicker.current(0)
        self.cur_data = self.master.fileMan.load_block(self.cur_file, self.cur_block)

        ll = textprocess.calcLineLen(cur_file, False) or self.master.textBoxEn.DEFAULT_WIDTH
        self.master.textBoxEn.config(width=ll)
        self.master.textBoxJp.config(width=ll)

    def reload_chapter(self, event=None):
        self.cur_file.reload()
        self.cur_data = self.master.fileMan.load_block(self.cur_file, self.cur_block)

    def prev_ch(self, event=None):
        if self.cur_chapter - 1 > -1:
            self.chapterPicker.current(self.cur_chapter - 1)
            self.change_chapter()
        else:
            print("Reached first chapter")

    def next_ch(self, event=None):
        #! ugh
        if self.cur_chapter + 1 < len(self.master.fileMan.files):
            self.chapterPicker.current(self.cur_chapter + 1)
            self.change_chapter()
        else:
            print("Reached last chapter")

    def change_block(self, event=None, dir=1):
        self.master.fileMan.save_block(self)

        # ? Hope this doesn't loop but it didn't before so...?
        if self.master.options.skip_translated.get():
            blocks = self.cur_file.textBlocks
            targetBlock = self.cur_block
            data = blocks[self.cur_block]
            while 0 < targetBlock < len(blocks) - 1 and (
                data["enText"] or isEnglish(data["jpText"])
            ):
                targetBlock += dir
                data = self.cur_file.textBlocks[targetBlock]
            self.cur_block = targetBlock
            self.blockPicker.current(targetBlock)

        if self.master.options.saveOnBlockChange.get():
            self.master.fileMan.saveFile()

        self.cur_block = self.blockPicker.current()
        self.cur_data = self.master.fileMan.load_block(self.cur_file, self.cur_block)

    def prev_block(self, event=None):
        if self.cur_block - 1 > -1:
            self.blockPicker.current(self.cur_block - 1)
            self.change_block(dir=-1)

    def next_block(self, event=None):
        next_index = self.cur_data.get("nextBlock", self.cur_block + 2) - 1
        if next_index < 1 or next_index >= len(self.cur_file.textBlocks):
            next_index = -1
        # todo: following buttons are defined on self by Editor
        if next_index > 0:
            self.btnNext["state"] = "normal"
            self.btnNext["text"] = f"Next ({next_index + 1})"
        else:
            self.btnNext["state"] = "disabled"
            self.btnNext["text"] = "Next"
        if next_index != -1:
            self.blockPicker.current(next_index)
            self.change_block()
        else:
            print("Reached end of chapter")

    def searchChapters(self, event=None):
        if event.keysym in ("Up", "Down", "Left", "Right", "Return"):
            return
        self.chapterPicker = 5  #! ???
        search = self.chapterPicker.get()
        if search == "":
            self.chapterPicker["values"] = self.master.fileMan.formattedFiles
            self.chapterPicker.search = None
        else:
            searchList = {
                item: i
                for i, item in enumerate(self.master.fileMan.formattedFiles)
                if search in item
            }
            self.chapterPicker["values"] = (
                list(searchList.keys()) if searchList else ["No matches found"]
            )
            self.chapterPicker.search = list(searchList.values()) if searchList else None

    def resetChapterSearch(self):
        self.chapterPicker["values"] = self.master.fileMan.formattedFiles
        self.chapterPicker.search = None

    def nextMissingName(self):
        for idx, block in enumerate(self.cur_file.textBlocks):
            if not block.get("enName") and block.get("jpName") not in NAMES_BLACKLIST:
                self.blockPicker.current(idx)
                self.change_block()
