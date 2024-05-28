from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Union

from common import patch
from common.constants import NAMES_BLACKLIST
from common.types import StoryId, TranslationFile

from . import display, text

if TYPE_CHECKING:
    from .app import Editor
    from .navigator import Navigator


class SaveState:
    lastEnText: str
    lastTitle: str = ""
    unsavedChanges = set()

    def markBlockLoaded(self, block: dict):
        self.lastEnText = block.get("enText")

    def markBlockSaved(self, chapter: int, block: dict):
        text = block.get("enText")
        # short the str comp when changes already known
        if chapter not in self.unsavedChanges and text != self.lastEnText:
            self.unsavedChanges.add(chapter)

    def markFileLoaded(self, file: TranslationFile):
        self.lastTitle = file.data.get("enTitle", "")

    def markTitleChanged(self, ch, newTitle):
        """Sets save state as needed, returns whether title changed"""
        if newTitle == self.lastTitle:
            return False
        self.lastTitle = newTitle
        self.unsavedChanges.add(ch)
        return True
    
    def onFileSaved(self, ch: int, block: dict):
        # Little hack to prevent false unsaved files on chapter change without block change
        # Essentially pretend the block was reloaded. Could be done in markBlockSaved but
        # would usually be useless and immediately replaced by the actual block load
        self.markBlockLoaded(block)
        self.unsavedChanges.discard(ch)


class FileManager:
    def __init__(self, master: "Editor") -> None:
        self.master = master
        self.saveState = SaveState()
        self.formattedFiles = None

    def importFiles(self, src: Union[StoryId, Path, list[Union[TranslationFile, Path]]]):
        if isinstance(src, StoryId):
            # todo: make search accept storyid
            files = patch.searchFiles(
                src.type, src.group, src.id, src.idx, targetSet=src.set, changed=src.changed
            )
            if not files:
                raise FileNotFoundError("No files match given criteria")
        elif isinstance(src, Path):
            files = [src]
        elif isinstance(src, list):
            if not isinstance(src[0], (Path, TranslationFile)):
                raise ValueError
            files = src
        else:
            raise NotImplementedError
        files.sort()
        # todo: Was chapter_dropdown.formattedList
        self.files = files
        # f.name happens to work on both types
        self.formattedFiles = [f.name for f in files]
        #! sigh
        self.master.nav.chapterPicker["values"] = self.formattedFiles
        self.master.nav.change_chapter(0)
        #? reset savestate and others?

    def loadFile(self, chapter: int) -> TranslationFile:
        file = self.files[chapter]
        if isinstance(file, Path):
            file = TranslationFile(file)
            self.files[chapter] = file
        return file

    def saveFile(self, nav: "Navigator", saveAll=None):
        self.save_block(nav)
        targets = self.files if saveAll else (nav.cur_file,)

        for ch, file in enumerate(targets):
            if saveAll and not isinstance(file, TranslationFile):
                continue
            if self.master.options.markHuman.get():
                file.data["humanTl"] = True
            file.save()
            # Prevent message spam
            if not self.master.options.saveOnBlockChange.get() and not saveAll:
                self.master.status.setSaved()
            self.saveState.onFileSaved(ch if saveAll else nav.cur_chapter, nav.cur_data)
        if saveAll:
            self.master.status.log("Saved all files")

    def load_block(self, file: TranslationFile, idx: int):
        """Loads a block by index. Note block data may not be available before this."""
        block = file.textBlocks[idx]

        # Fill in the text boxes
        display.setActive(self.master.speakerJp, True)
        text.setText(self.master.speakerJp, block.get("jpName", ""))
        self.master.speakerJp.config(state="readonly")
        if block.get("jpName") in NAMES_BLACKLIST:
            text.clearText(self.master.speakerEn)
            display.setActive(self.master.speakerEn, False)
        else:
            display.setActive(self.master.speakerEn, True)
            en_name = block.get("enName", "")
            text.setText(self.master.speakerEn, en_name)
            if en_name:
                self.master.speakerEn.config(bg=self.master.COLOR_WIN)
            else:
                self.master.speakerEn.config(bg="red")

        # Spinbox for text block duration
        origClipLen = block.get("origClipLength")
        if origClipLen is None:
            self.master.blockDuration.set(-1)
            display.setActive(self.master.blockDuration, False)
        else:
            display.setActive(self.master.blockDuration, True)
            text.setText(self.master.blockDurationLabel, f"Duration ({origClipLen})")
            self.master.blockDuration.set(block.get("newClipLength", 0))

        self.master.textBoxJp.loadRichText(text.for_display(file, block["jpText"]))
        displayText = text.for_display(file, block["enText"])
        self.master.textBoxEn.loadRichText(displayText)

        # Update choices button
        cur_choices = block.get("choices")
        if cur_choices:
            self.master.choices.setChoices(cur_choices)
            self.master.choices.widget.grid()
        else:
            # self.master.choices.clearChoices()
            self.master.choices.widget.grid_remove()

        # Update colored button
        cur_colored = block.get("coloredText")
        if cur_colored:
            self.master.extraText.cur_colored = cur_colored
            display.setActive(self.master.btnColored, True)
            self.master.btnColored.config(bg="#00ff00")
            self.master.extraText.toggle(allowShow=False, target=cur_colored)
        else:
            display.setActive(self.master.btnColored, False)
            self.master.btnColored.config(bg=self.master.COLOR_BTN)

        self.saveState.markBlockLoaded(block)
        self.master.preview.setText(displayText)
        return block

    def save_block(self, nav: "Navigator"):
        cur_file = nav.cur_file
        cur_data = nav.cur_data

        if "enName" in cur_data:
            cur_data["enName"] = text.normalize(self.master.speakerEn.get())
        cur_data["enText"] = text.for_storage(cur_file, self.master.textBoxEn.toRichText())
        if "choices" in cur_data:
            self.master.choices.saveChoices()

        # Get the new clip length from spinbox
        try:
            new_clip_length = int(self.master.blockDuration.get())
        except ValueError:
            messagebox.showwarning(
                master=self.master.blockDuration,
                title="Invalid clip length",
                message="Clip length must be an integer."
            )
            new_clip_length = -1
        origClipLen = cur_data.get("origClipLength", 9999)
        if new_clip_length == origClipLen:
            cur_data.pop("newClipLength", None)
        elif origClipLen < new_clip_length < 1001:
            cur_data["newClipLength"] = new_clip_length

        self.saveState.markBlockSaved(nav.cur_chapter, cur_data)
        self.master.root.event_generate("<<BlockSaved>>", data=cur_data)

    # Event handler
    def save_title(self, *_):
        title = self.master.titleEn.get()
        if self.saveState.markTitleChanged(self.master.nav.cur_chapter, title):
            self.master.nav.cur_file.data["enTitle"] = title
            self.master.status.setUnsaved()
