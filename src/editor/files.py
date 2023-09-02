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
    unsavedChanges = set()

    def markBlockLoaded(self, block: dict):
        self.lastEnText = block.get("enText")

    def markBlockSaved(self, chapter: int, block: dict):
        text = block.get("enText")
        # short the str comp when changes already known
        if chapter not in self.unsavedChanges and text != self.lastEnText:
            self.unsavedChanges.add(chapter)

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

    def importFiles(self, src: Union[StoryId, str, list[Union[TranslationFile, str]]]):
        if isinstance(src, StoryId):
            # todo: make search accept storyid
            files = patch.searchFiles(
                src.type, src.group, src.id, src.idx, targetSet=src.set, changed=src.changed
            )
            if not files:
                raise FileNotFoundError("No files match given criteria")
        elif isinstance(src, str):
            files = [src]
        elif isinstance(src, list):
            if not isinstance(src[0], (str, TranslationFile)):
                raise ValueError
            files = src
        else:
            raise NotImplementedError
        files.sort()
        # todo: Was chapter_dropdown.formattedList
        self.files = files
        self.formattedFiles = [f.split("\\")[-1] for f in files]
        #! sigh
        self.master.nav.chapterPicker["values"] = self.formattedFiles
        self.master.nav.chapterPicker.current(0)
        self.master.nav.change_chapter()
        # reset savestate and others?

    def loadFile(self, chapter: int) -> TranslationFile:
        file = self.files[chapter]
        if isinstance(file, str):
            file = TranslationFile(file)
            self.files[chapter] = file
        return file

    def saveFile(self, nav: "Navigator", saveAll=None):
        self.save_block(nav)
        targets = self.files if saveAll else (nav.cur_file,)

        for ch, file in enumerate(targets):
            if saveAll and isinstance(file, str):
                continue
            if self.master.options.markHuman.get():
                file.data["humanTl"] = True
            file.save()
            # Prevent message spam
            if not self.master.options.saveOnBlockChange.get() and not saveAll:
                print("Saved")
            self.saveState.onFileSaved(ch if saveAll else nav.cur_chapter, nav.cur_data)
        if saveAll:
            print("Saved all files")

    def load_block(self, file: TranslationFile, idx: int):
        """Loads a block by index. Note block data may not be available before this."""
        block = file.textBlocks[idx]

        # Fill in the text boxes
        text.setText(self.master.speakerJp, block.get("jpName", ""))
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
        text.clearText(self.master.blockDuration)
        if "origClipLength" in block:
            text.setText(self.master.blockDurationLabel, f"Text Duration ({block['origClipLength']})")
        if "newClipLength" in block:
            text.setText(self.master.blockDuration, block["newClipLength"])
        else:
            if "origClipLength" in block:
                text.setText(self.master.blockDuration, block["origClipLength"])
            else:
                text.setText(self.master.blockDuration, "-1")

        display.setActive(self.master.textBoxJp, True)
        self.master.textBoxJp.loadRichText(text.for_display(file, block["jpText"]))
        display.setActive(self.master.textBoxJp, False)
        displayText = text.for_display(file, block["enText"])
        self.master.textBoxEn.loadRichText(displayText)

        # Update choices button
        cur_choices = block.get("choices")
        if cur_choices:
            self.master.extraText.cur_choices = cur_choices
            display.setActive(self.master.btnChoices, True)
            self.master.btnChoices.config(bg="#00ff00")
            self.master.extraText.toggle(allowShow=False, target=cur_choices)
        else:
            display.setActive(self.master.btnChoices, False)
            self.master.btnChoices.config(bg=self.master.COLOR_BTN)

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
        self.master.spell_checker.check_spelling()
        self.master.preview.setText(displayText)
        return block

    def save_block(self, nav: "Navigator"):
        cur_file = nav.cur_file
        cur_data = nav.cur_data

        if "enName" in cur_data:
            cur_data["enName"] = text.normalize(self.master.speakerEn.get())
        cur_data["enText"] = text.for_storage(cur_file, self.master.textBoxEn.toRichText())

        # Get the new clip length from spinbox
        new_clip_length = self.master.blockDuration.get()
        if new_clip_length.isnumeric():
            new_clip_length = int(new_clip_length)
            if "origClipLength" in cur_data and new_clip_length != cur_data["origClipLength"]:
                cur_data["newClipLength"] = new_clip_length
            else:
                cur_data.pop("newClipLength", None)
                if "origClipLength" not in cur_data:
                    messagebox.showwarning(
                        master=self.master.blockDuration,
                        title="Cannot save clip length",
                        message="This text block does not have an original clip length defined"
                        " and thus cannot save a custom clip length. Resetting to -1.",
                    )
                    text.setText(self.master.blockDuration, "-1")
        elif new_clip_length != "-1":
            cur_data.pop("newClipLength", None)
        self.saveState.markBlockSaved(nav.cur_chapter, cur_data)
