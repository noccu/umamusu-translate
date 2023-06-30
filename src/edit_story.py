from argparse import SUPPRESS
import re
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from tkinter.font import Font
from types import SimpleNamespace
from itertools import zip_longest
from dataclasses import dataclass, field as datafield
from functools import partial

import symspellpy

from common import patch
from common.constants import IS_WIN, GAME_META_FILE, NAMES_BLACKLIST, SUPPORTED_TYPES
from common.utils import isEnglish
from common.files import GameBundle, TranslationFile
import textprocess

if IS_WIN:
    from ctypes import windll, byref, create_unicode_buffer, create_string_buffer
    import pyaudio, sqlite3, wave, restore  # noqa: E401
    from PyCriCodecs import AWB, HCA

TEXTBOX_WIDTH = 54
COLOR_WIN = "systemWindow" if IS_WIN else "white"
COLOR_BTN = "SystemButtonFace" if IS_WIN else "gray"
AUDIO_PLAYER = None
LAST_COLOR = None


@dataclass
class PlaySegment:
    idx: int
    startTime: int
    endTime: int
    timeBased: bool = datafield(init=False, compare=False)

    def __post_init__(self):
        self.timeBased = False if self.startTime is None else True
        self._rateApplied = False

    def applyRateOnce(self, rate):
        """Applies the given rate if time-based, does nothing past first call"""
        if self._rateApplied or not self.timeBased:
            return
        self.startTime *= int(rate / 1000)
        if self.endTime:
            self.endTime *= int(rate / 1000)
        self._rateApplied = True

    @classmethod
    def fromBlock(cls, block):
        idx = block.get("voiceIdx")
        start = block.get("time")
        end = None
        if start:
            start = int(start)
            nextBlock = cur_file.textBlocks[cur_block + 1]
            if nextBlock:
                end = int(nextBlock.get("time"))
        elif idx is not None:
            idx = int(idx)
        else:
            return None
        return cls(idx, start, end)


class AudioPlayer:
    # Intended as singleton
    curPlaying = (None, 0)
    subkey = None
    outStreams: list[pyaudio.PyAudio.Stream] = list()
    wavFiles: list[wave.Wave_read] = list()
    subFiles = None

    def __init__(self) -> None:
        self.pyaud = pyaudio.PyAudio()
        self._db = sqlite3.connect(GAME_META_FILE)
        self._restoreArgs = restore.parseArgs([])

    def dealloc(self):
        self._db.close()
        for stream, wavFile in zip(self.outStreams, self.wavFiles):
            if isinstance(stream, pyaudio.PyAudio.Stream):
                stream.stop_stream()
                stream.close()
            self._closeWavStream(wavFile)
        self.pyaud.terminate()

    def play(self, storyId: str, voice: PlaySegment, sType="story"):
        """Plays audio for a specific text block"""
        storyId: patch.StoryId = patch.StoryId.parse(sType, storyId)
        qStoryId = patch.StoryId.queryfy(storyId)
        if not voice.timeBased and voice.idx < 0:
            print("Text block is not voiced.")
            return
        # New assets
        if reloaded := self.curPlaying[0] != storyId:
            if sType == "home":
                # sound/c/snd_voi_story_00001_02_1054001.acb
                stmt = rf"SELECT h FROM a WHERE n LIKE 'sound%{qStoryId.set}\_{qStoryId.group}\_{qStoryId.id}{qStoryId.idx}\.awb' ESCAPE '\'"
            elif sType == "lyrics":
                stmt = f"SELECT h FROM a WHERE n LIKE 'sound/l/{qStoryId.id}/snd_bgm_live_{qStoryId.id}_chara%.awb'"
            else:
                stmt = f"SELECT h FROM a WHERE n LIKE 'sound%{qStoryId}.awb'"
            h = self._db.execute(stmt).fetchone()
            if h is None:
                print("Couldn't find audio asset.")
                return
            asset = GameBundle.fromName(h[0], load=False)
            asset.bundleType = "sound"
            if not asset.exists:
                restore.save(asset, self._restoreArgs)
            self.wavFiles.clear()
            self.load(str(asset.bundlePath))
        # New subfile/time
        if voice.timeBased and reloaded:  # lyrics, add all tracks
            for file in self.subFiles:
                self.wavFiles.append(self.decodeAudio(file))
        elif not voice.timeBased and (
            reloaded or self.curPlaying[1] != voice.idx
        ):  # most things, add requested track
            if voice.idx > len(self.subFiles):
                print("Index out of range")
                return
            audData = self.decodeAudio(self.subFiles[voice.idx])
            if self.wavFiles:
                self.wavFiles[0] = audData
            else:
                self.wavFiles.append(audData)
        self.curPlaying = (storyId, voice)
        self._playAudio(voice)

    def load(self, path: str):
        """Loads the main audio container at path"""
        awbFile = AWB(path)
        # get by idx method seems to corrupt half the files??
        self.subFiles = [f for f in awbFile.getfiles()]
        self.subkey = awbFile.subkey
        awbFile.stream.close()

    def decodeAudio(self, hcaFile: bytes):
        """Decodes a new audio stream, called only when such is requested"""
        hcaFile: HCA = HCA(hcaFile, key=75923756697503, subkey=self.subkey)
        hcaFile.decode()  # leaves a wav ByteIOStream in stream attr
        return wave.open(hcaFile.stream, "rb")

    def _getAudioData(self, data, frames, time, status, wavIdx=0):
        """Data retrieval method called by async pyAudio play"""
        wavFile = self.wavFiles[wavIdx]
        voice = self.curPlaying[1]
        if voice.timeBased and voice.endTime:
            pos = wavFile.tell()
            if pos + frames > voice.endTime:
                frames = voice.endTime - pos
        data = wavFile.readframes(frames)
        # auto-stop on EOF seems to override Flag and only affects is_active()
        # stream still needs to be stopped
        return (data, pyaudio.paContinue)

    def _playAudio(self, voice: PlaySegment):
        """Deals with the technical side of playing audio"""
        if not self.wavFiles:
            print("No WAV loaded.")
            return
        for i, (stream, wavFile) in enumerate(zip_longest(self.outStreams, self.wavFiles)):
            if wavFile.getfp().closed:
                print("WAV unexpectedly closed")
                return
            channels = wavFile.getnchannels() or 1
            rate = wavFile.getframerate() or 48000
            bpc = wavFile.getsampwidth() or 2
            voice.applyRateOnce(rate)

            if streamExists := isinstance(stream, pyaudio.PyAudio.Stream):
                stream.stop_stream()  # New play is requested, always stop any current
            if voice.timeBased:
                wavFile.setpos(voice.startTime)
            else:
                wavFile.rewind()

            if streamExists:
                if stream._channels == channels and stream._rate == rate:
                    stream.start_stream()
                    continue
                else:
                    stream.close()
            newStream = self.pyaud.open(
                format=self.pyaud.get_format_from_width(width=bpc),
                channels=channels,
                rate=rate,
                output=True,
                stream_callback=partial(self._getAudioData, wavIdx=i),
            )
            if len(self.outStreams) > i:
                self.outStreams[i] = newStream
            else:
                self.outStreams.append(newStream)

    def _closeWavStream(self, wavFile):
        wavFile.getfp().close()
        wavFile.close()

    @staticmethod
    def listen(event=None):
        if not IS_WIN:
            print("Audio currently only supported on Windows")
            return
        voice = PlaySegment.fromBlock(cur_file.textBlocks[cur_block])
        if not voice:
            print("Old file version, does not have voice info.")
            return "break"
        storyId = cur_file.data.get("storyId")
        if not storyId:
            print("File has an invalid storyid.")
            return "break"
        elif len(storyId) < 9 and cur_file.type != "lyrics":
            # Preview type would work but I don't understand
            # the format/where it gets info unless it's really just awbTracks[15:-1]
            print("Unsupported type.")
            return "break"
        elif voice is None:
            print("No voice info found for this block.")
            return "break"

        global AUDIO_PLAYER
        if not AUDIO_PLAYER:
            AUDIO_PLAYER = AudioPlayer()
        AUDIO_PLAYER.play(storyId, voice, sType=cur_file.type)
        return "break"


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

    def markChapterSaved(self, chapter: int):
        # Little hack to prevent false unsaved files on chapter change without block change
        # Essentially pretend the block was reloaded. Could be done in markBlockSaved but
        # would usually be useless and immediately replaced by the actual block load
        self.markBlockLoaded(cur_file.textBlocks[cur_block])
        self.unsavedChanges.discard(chapter)


class PopupMenu(tk.Menu):
    def clear(self):
        self.delete(0, tk.END)

    def show(self, event: tk.Event, atInsert=False):
        if atInsert:
            x1, y1 = event.widget.bbox(tk.INSERT)[:2]
            x = event.widget.winfo_rootx() + x1
            y = event.widget.winfo_rooty() + y1
        else:
            x = event.x_root
            y = event.y_root
        try:
            self.tk_popup(x, y)
        finally:
            self.grab_release()


class SpellCheck:
    dictPath = "src/data/frequency_dictionary_en_82_765.txt"
    customDictPath = "src/data/umatl_spell_dict.txt"
    dictionary: symspellpy.SymSpell = None
    nameFreq = 30000000000
    defaultFreq = 30000

    def __init__(self, widget: tk.Text) -> None:
        widget.tag_config("spellError", underline=True, underlinefg="red")
        widget.tag_bind("spellError", "<Button-3>", self.show_suggestions)
        widget.bind("<KeyRelease>", self.check_spelling)
        widget.bind("<Control-space>", self.autocomplete)
        # widget.word_suggestions = {}
        self.menu = PopupMenu(widget, tearoff=0)
        self.widget = widget
        self.newDict = list()
        if not SpellCheck.dictionary:
            SpellCheck.dictionary = symspellpy.SymSpell()
            SpellCheck.dictionary.load_dictionary(SpellCheck.dictPath, 0, 1)
            if not SpellCheck.dictionary.create_dictionary(self.customDictPath, "utf8"):
                print("No custom dict loaded.")
            self._loadNames()

    def add_word(self, word: str, fixRange: tuple, isName=False):
        lcword = word.lower()
        # Max importance of names
        # freq = 30000000000 if word[0].isupper() else 30000
        freq = SpellCheck.nameFreq if isName else SpellCheck.defaultFreq
        self.newDict.append(f"{lcword} {freq}\n")
        SpellCheck.dictionary.create_dictionary_entry(lcword, freq)
        # Remove UI marking
        del self.widget.word_suggestions[word]
        self.widget.tag_remove("spellError", *fixRange)

    def _loadNames(self):
        namesFile = TranslationFile("translations/mdb/char-name.json")
        for entry in namesFile.textBlocks:
            name = entry.get("enText").lower().split()
            for n in name:
                if len(n) < 3:
                    continue
                self.dictionary.create_dictionary_entry(n, SpellCheck.nameFreq)

    def check_spelling(self, event=None):
        if event and event.keysym not in ("space", "BackSpace", "Delete"):
            return
        text = self.widget.get("1.0", tk.END)
        words = re.split(r"[^A-Za-z\-']", text)
        # Reset state
        self.widget.tag_remove("spellError", "1.0", tk.END)
        self.widget.word_suggestions = {}
        # Iterate over each word and check for spelling errors
        searchIdx = 0
        for word in words:
            if word == "" or len(word) == 1 or word.lower() in SpellCheck.dictionary.words:
                searchIdx += len(word)
                continue
            # print(f"Looking up {word}")
            suggestions = SpellCheck.dictionary.lookup(
                word, symspellpy.Verbosity.CLOSEST, transfer_casing=True
            )
            startIdx = text.index(word, searchIdx)
            endIdx = startIdx + len(word)
            searchIdx += len(word)
            self.widget.tag_add("spellError", f"1.0+{startIdx}c", f"1.0+{endIdx}c")
            self.widget.word_suggestions[word] = suggestions

    def autocomplete(self, event: tk.Event = None):
        # \M = word boundary (end only) -> TCL, reverse search
        wordstart = self.widget.search(
            r"\M", index=tk.INSERT, backwards=True, regexp=True, nocase=True
        )
        # The index returned from the 0-length match is 1 too early.
        # Special-case first word on first line because \M matches possible $ and not ^
        if not wordstart:
            wordstart = "1.0"
        else:
            wordstart += "+1c"
        # Remove extraneous newlines that happen with empty lines for some reason.
        partialWord, n = re.subn(r"\n", "", self.widget.get(wordstart, tk.INSERT))
        wordstart += f"+{n}c"  # And adjust the index accordingly.
        # Keep capitalization
        isCapitalized = partialWord[0].isupper()
        partialWord = partialWord.lower()
        self.menu.clear()
        suggestions = 0
        for word in self.dictionary.words:
            if word.startswith(partialWord):
                if isCapitalized:
                    word = word.title()
                self.menu.add_command(
                    label=word, command=partial(self.autoReplace, wordstart, word)
                )
                suggestions += 1
            if suggestions == 25:
                break
        self.menu.show(event, atInsert=True)

    def autoReplace(self, wordstart, word):
        self.widget.delete(wordstart, tk.INSERT)
        self.widget.insert(wordstart, word)

    def show_suggestions(self, event):
        currentSpellFix = self.widget.tag_prevrange(
            "spellError", tk.CURRENT
        ) or self.widget.tag_nextrange("spellError", tk.CURRENT)
        clicked_word = self.widget.get(*currentSpellFix)
        # print(f"Clicked {clicked_word}")
        suggestions = self.widget.word_suggestions.get(clicked_word)
        # Set up context menu handling
        self.menu.clear()
        for suggestion in suggestions:
            self.menu.add_command(
                label=suggestion.term,
                command=partial(self.replace_word, currentSpellFix, clicked_word, suggestion.term),
            )
        self.menu.add_separator()
        self.menu.add_command(
            label="Add to dictionary", command=lambda: self.add_word(clicked_word, currentSpellFix)
        )
        self.menu.add_command(
            label="Add as name", command=lambda: self.add_word(clicked_word, currentSpellFix, True)
        )
        self.menu.show(event)

    def replace_word(self, fixRange, oldWord, replacement):
        del self.widget.word_suggestions[oldWord]
        self.widget.tag_remove("spellError", *fixRange)
        self.widget.delete(*fixRange)
        self.widget.insert(fixRange[0], replacement)
        # print(f"Replaced {oldWord} with {replacement}")

    def saveNewDict(self):
        if len(self.newDict) == 0:
            return
        with open(self.customDictPath, "a", encoding="utf8", newline="\n") as f:
            f.writelines(self.newDict)
        print("New words added to umatl dict.")


def change_chapter(event=None, initialLoad=False):
    global cur_chapter
    global cur_block
    global cur_file

    if not initialLoad:
        save_block()
    if chapter_dropdown.search:
        cur_chapter = chapter_dropdown.search[chapter_dropdown.current()]
        resetChapterSearch()
    else:
        cur_chapter = chapter_dropdown.current()
    cur_block = 0

    loadFile()
    cur_file = files[cur_chapter]

    block_dropdown["values"] = [
        f"{i+1} - {block['jpText'][:16]}" for i, block in enumerate(cur_file.textBlocks)
    ]
    ll = textprocess.calcLineLen(cur_file, False) or TEXTBOX_WIDTH
    text_box_en.config(width=ll)
    text_box_jp.config(width=ll)

    load_block()


def reload_chapter(event=None):
    cur_file.reload()
    load_block()


def prev_ch(event=None):
    if cur_chapter - 1 > -1:
        chapter_dropdown.current(cur_chapter - 1)
        change_chapter()
    else:
        print("Reached first chapter")


def next_ch(event=None):
    if cur_chapter + 1 < len(files):
        chapter_dropdown.current(cur_chapter + 1)
        change_chapter()
    else:
        print("Reached last chapter")


def change_block(event=None, dir=1):
    global cur_block

    save_block()
    if save_on_next.get() == 1:
        saveFile()

    cur_block = block_dropdown.current()
    load_block(dir=dir)


def load_block(event=None, dir=1):
    global cur_block
    global next_index
    global cur_choices
    global cur_colored

    blocks = cur_file.textBlocks
    cur_block_data = blocks[cur_block]

    if skip_translated.get() == 1:
        while 0 < cur_block < len(blocks) - 1 and (
            cur_block_data["enText"] or isEnglish(cur_block_data["jpText"])
        ):
            cur_block += dir
            cur_block_data = blocks[cur_block]
        block_dropdown.current(cur_block)

    next_index = cur_block_data.get("nextBlock", cur_block + 2) - 1
    if next_index < 1 or next_index >= len(blocks):
        next_index = -1
    if next_index > 0:
        btn_next["state"] = "normal"
        btn_next["text"] = f"Next ({next_index + 1})"
    else:
        btn_next["state"] = "disabled"
        btn_next["text"] = "Next"

    # Fill in the text boxes
    speaker_jp_entry.delete(0, tk.END)
    speaker_jp_entry.insert(0, cur_block_data.get("jpName", ""))
    if cur_block_data.get("jpName") in NAMES_BLACKLIST:
        speaker_en_entry.delete(0, tk.END)
        speaker_en_entry["state"] = "disabled"
    else:
        speaker_en_entry["state"] = "normal"
        speaker_en_entry.delete(0, tk.END)
        en_name = cur_block_data.get("enName", "")
        if en_name:
            speaker_en_entry.insert(0, en_name)
            speaker_en_entry.config(bg=COLOR_WIN)
        else:
            speaker_en_entry.config(bg="red")

    # Spinbox for text block duration
    block_duration_spinbox.delete(0, tk.END)
    if "origClipLength" in cur_block_data:
        block_duration_label.config(text=f"Text Duration ({cur_block_data['origClipLength']})")
    if "newClipLength" in cur_block_data:
        block_duration_spinbox.insert(0, cur_block_data["newClipLength"])
    else:
        if "origClipLength" in cur_block_data:
            block_duration_spinbox.insert(0, cur_block_data["origClipLength"])
        else:
            block_duration_spinbox.insert(0, "-1")

    text_box_jp.configure(state="normal")
    text_box_jp.delete(1.0, tk.END)
    text_box_jp.insert(tk.END, txt_for_display(cur_block_data["jpText"]))
    text_box_jp.configure(state="disabled")
    displayText = txt_for_display(cur_block_data["enText"])
    insertTaggedTextFromMarkup(text_box_en, displayText)
    # text_box_en.delete(1.0, tk.END)
    # text_box_en.insert(tk.END, txt_for_display(cur_block_data['enText']))

    # Update choices button
    cur_choices = cur_block_data.get("choices")
    if cur_choices:
        btn_choices["state"] = "normal"
        btn_choices.config(bg="#00ff00")
        toggleTextListPopup(allowShow=False, target=cur_choices)
    else:
        btn_choices["state"] = "disabled"
        btn_choices.config(bg=COLOR_BTN)

    # Update colored button
    cur_colored = cur_block_data.get("coloredText")
    if cur_colored:
        btn_colored["state"] = "normal"
        btn_colored.config(bg="#00ff00")
        toggleTextListPopup(allowShow=False, target=cur_colored)
    else:
        btn_colored["state"] = "disabled"
        btn_colored.config(bg=COLOR_BTN)
    SAVE_STATE.markBlockLoaded(cur_block_data)
    root.spell_checker.check_spelling()
    previewText.config(text=displayText)


def save_block():
    if "enName" in cur_file.textBlocks[cur_block]:
        cur_file.textBlocks[cur_block]["enName"] = normalizeEditorText(speaker_en_entry.get())
    cur_file.textBlocks[cur_block]["enText"] = txt_for_storage(tagsToMarkup(text_box_en))

    # Get the new clip length from spinbox
    new_clip_length = block_duration_spinbox.get()
    if new_clip_length.isnumeric():
        new_clip_length = int(new_clip_length)
        if (
            "origClipLength" in cur_file.textBlocks[cur_block]
            and new_clip_length != cur_file.textBlocks[cur_block]["origClipLength"]
        ):
            cur_file.textBlocks[cur_block]["newClipLength"] = new_clip_length
        else:
            cur_file.textBlocks[cur_block].pop("newClipLength", None)
            if "origClipLength" not in cur_file.textBlocks[cur_block]:
                messagebox.showwarning(
                    master=block_duration_spinbox,
                    title="Cannot save clip length",
                    message="This text block does not have an original clip length defined"
                    " and thus cannot save a custom clip length. Resetting to -1.",
                )
                block_duration_spinbox.delete(0, tk.END)
                block_duration_spinbox.insert(0, "-1")
    elif new_clip_length != "-1":
        cur_file.textBlocks[cur_block].pop("newClipLength", None)
    SAVE_STATE.markBlockSaved(cur_chapter, cur_file.textBlocks[cur_block])


def prev_block(event=None):
    if cur_block - 1 > -1:
        block_dropdown.current(cur_block - 1)
        change_block(dir=-1)


def next_block(event=None):
    if next_index != -1:
        block_dropdown.current(next_index)
        change_block()
    else:
        print("Reached end of chapter")


def copy_block(event=None):
    root.clipboard_clear()
    root.clipboard_append(txt_for_display(cur_file.textBlocks[cur_block]["jpText"]))


def loadFile(chapter=None):
    ch = chapter or cur_chapter
    if isinstance(files[ch], str):
        files[ch] = TranslationFile(files[ch])


def saveFile(event=None):
    save_block()
    saveAll = event and (event.state & 0x0001)
    targets = files if saveAll else (cur_file,)

    for ch, file in enumerate(targets):
        if saveAll and isinstance(file, str):
            continue
        if set_humanTl.get() == 1:
            file.data["humanTl"] = True
        file.save()
        if save_on_next.get() == 0 and not saveAll:
            print("Saved")
        SAVE_STATE.markChapterSaved(ch if saveAll else cur_chapter)
    if saveAll:
        print("Saved all files")


def show_text_list():
    global cur_text_list

    if cur_text_list:
        cur_text_list = cur_text_list
        for i, t in enumerate(extra_text_list_textboxes):
            if i < len(cur_text_list):
                jpBox, enBox = t
                jpBox["state"] = "normal"  # enable insertion...
                enBox["state"] = "normal"
                jpBox.insert(tk.END, cur_text_list[i]["jpText"])
                enBox.insert(tk.END, cur_text_list[i]["enText"])
                jpBox["state"] = "disabled"
        text_list_window.deiconify()
        text_list_window.firstText.focus()


def close_text_list():
    for i, t in enumerate(extra_text_list_textboxes):
        jpBox, enBox = t
        if cur_text_list and i < len(cur_text_list):
            cur_text_list[i]["enText"] = normalizeEditorText(
                enBox.get(1.0, tk.END)
            )  # choice don't really need special handling
        jpBox["state"] = "normal"  # enable deletion...
        jpBox.delete(1.0, tk.END)
        enBox.delete(1.0, tk.END)
        jpBox["state"] = "disabled"
        enBox["state"] = "disabled"
    text_list_window.withdraw()


def create_text_list_popup():
    global extra_text_list_textboxes
    global text_list_window
    global cur_choices
    global cur_colored
    global cur_text_list
    global text_list_popup_scrollable

    extra_text_list_textboxes = list()
    text_list_popup_scrollable = False
    cur_choices = None
    cur_colored = None
    cur_text_list = None

    text_list_window = tk.Toplevel()
    text_list_window.protocol("WM_DELETE_WINDOW", close_text_list)
    text_list_window.title("Additional Text Lists")
    text_list_window.geometry("580x450")  # 800 for full

    scroll_frame = ttk.Frame(text_list_window)
    scroll_frame.pack(fill="both", expand=True)

    scroll_canvas = tk.Canvas(scroll_frame)
    scroll_canvas.pack(side="left", fill="both", expand=True)

    scroll_bar = ttk.Scrollbar(scroll_frame, orient="vertical", command=scroll_canvas.yview)
    scroll_bar.pack(side="right", fill="y")

    scroll_canvas.configure(yscrollcommand=scroll_bar.set)
    scroll_canvas.bind(
        "<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
    )

    window_frame = ttk.Frame(scroll_canvas)
    scroll_canvas.create_window((0, 0), window=window_frame, anchor="nw")

    def toggle_scroll(e):
        global text_list_popup_scrollable
        text_list_popup_scrollable = not text_list_popup_scrollable

    def scroll(e):
        if text_list_popup_scrollable:
            scroll_canvas.yview_scroll(-1 * int(e.delta / 35), "units")

    scroll_canvas.bind_all("<MouseWheel>", scroll)
    window_frame.bind("<Enter>", toggle_scroll)
    window_frame.bind("<Leave>", toggle_scroll)

    for i in range(0, 5):
        cur_jp_text = tk.Text(window_frame, takefocus=0, width=42, height=2, font=large_font)
        cur_jp_text.pack(anchor="w")
        cur_en_text = tk.Text(window_frame, height=2, width=42, undo=True, font=large_font)
        cur_en_text.pack(anchor="w")
        extra_text_list_textboxes.append((cur_jp_text, cur_en_text))
        cur_en_text.bind("<Tab>", _switchWidgetFocusForced)
        if i == 0:
            text_list_window.firstText = cur_en_text
        if i < 4:
            ttk.Separator(window_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
    close_text_list()


def toggleTextListPopup(event=None, allowShow=True, target=None):
    global cur_text_list
    if text_list_window.state() == "normal":
        close_text_list()
        # Actually open other type if old window closed by opening another type,
        if target is not cur_text_list:
            toggleTextListPopup(allowShow=allowShow, target=target)
    elif allowShow:
        cur_text_list = target
        show_text_list()


def create_search_popup():
    global search_window
    global search_filter
    global search_chapters
    global search_orig_state

    # set it here so it exists when window closed without searching
    search_orig_state = cur_block, cur_chapter, save_on_next.get(), skip_translated.get()
    reset_search()  # sets cur state

    search_window = tk.Toplevel()
    search_window.title("Search")
    search_window.protocol("WM_DELETE_WINDOW", close_search)
    search_window.bind("<Control-f>", toggleSearchPopup)

    s_var_field = tk.StringVar(search_window, value="enText")
    s_var_re = tk.StringVar(search_window)
    lb_field = tk.Label(search_window, text="Field:")
    lb_re = tk.Label(search_window, text="Search (supports regex):")
    search_field = tk.Entry(search_window, width=20, font=large_font, textvariable=s_var_field)
    search_re = tk.Entry(
        search_window, name="filter", width=40, font=large_font, textvariable=s_var_re
    )
    lb_field.grid(column=0, sticky=tk.E)
    lb_re.grid(column=0, sticky=tk.E)
    search_field.grid(row=0, column=1, columnspan=2, sticky=tk.W)
    search_re.grid(row=1, column=1, columnspan=2, sticky=tk.W)
    search_re.bind("<Return>", search_text)

    search_chapters = tk.IntVar()
    search_chapters.set(0)
    chk_search_chapters = tk.Checkbutton(
        search_window, text="Search all loaded chapters", variable=search_chapters
    )
    chk_search_chapters.grid(column=2, pady=5, sticky=tk.E)

    btn_search = tk.Button(search_window, text="Search / Next", name="search", command=search_text)
    btn_return = tk.Button(
        search_window, text="Return to original block", command=restore_search_state, padx=5
    )
    btn_return.grid(row=2, column=0, padx=5)
    btn_search.grid(row=2, column=1)

    search_filter = s_var_field, s_var_re
    for v in (s_var_field, s_var_re, search_chapters):
        v.trace_add("write", reset_search)
    search_window.withdraw()


def search_text(*_):
    min_ch = search_cur_state[0]
    if search_chapters.get():
        for ch in range(min_ch, len(files)):
            loadFile(ch)
            if _search_text_blocks(ch):
                return
    else:
        _search_text_blocks(cur_chapter)


def _search_text_blocks(chapter):
    global search_cur_state

    start_block = search_cur_state[1]
    s_field, s_re = (x.get() for x in search_filter)

    # print(f"searching in {cur_file.name}, from {search_cur_state}, on {s_field} = {s_re}")
    file = files[chapter]
    for i in range(start_block, len(file.textBlocks)):
        block = file.textBlocks[i]
        # Ignore blacklisted names when searching for empties
        if (
            s_field.startswith("enN")
            and s_re == "^$"
            and block.get("jpName") in NAMES_BLACKLIST
        ):
            continue
        if re.search(s_re, block.get(s_field, ""), flags=re.IGNORECASE):
            # print(f"Found {s_re} at ch{chapter}:b{i}")
            if chapter != cur_chapter:
                chapter_dropdown.current(chapter)
                change_chapter()
            block_dropdown.current(i)
            change_block()
            search_cur_state = cur_chapter, i + 1
            return True
    search_cur_state = cur_chapter + 1, 0
    return False


def reset_search(event=None, *args):
    # event = the Var itself
    global search_cur_state
    search_cur_state = 0, 0


def restore_search_state():
    ch, b, *_ = search_orig_state
    chapter_dropdown.current(ch)
    change_chapter()
    block_dropdown.current(b)
    change_block()


def show_search():
    global search_orig_state
    search_orig_state = cur_chapter, cur_block, save_on_next.get(), skip_translated.get()
    save_on_next.set(0)
    skip_translated.set(0)
    search_window.deiconify()
    search_window.nametowidget("filter").focus()


def close_search():
    save_on_next.set(search_orig_state[2])
    skip_translated.set(search_orig_state[3])
    search_window.withdraw()


def toggleSearchPopup(event=None):
    global cur_text_list
    if search_window.state() == "normal":
        close_search()
    else:
        show_search()


def searchChapters(event=None):
    if event.keysym in ("Up", "Down", "Left", "Right", "Return"):
        return
    search = chapter_dropdown.get()
    if search == "":
        chapter_dropdown["values"] = chapter_dropdown.formattedList
        chapter_dropdown.search = None
    else:
        searchList = {
            item: i for i, item in enumerate(chapter_dropdown.formattedList) if search in item
        }
        chapter_dropdown["values"] = list(searchList.keys()) if searchList else ["No matches found"]
        chapter_dropdown.search = list(searchList.values()) if searchList else None


def resetChapterSearch():
    chapter_dropdown["values"] = chapter_dropdown.formattedList
    chapter_dropdown.search = None


def createPreviewWindow():
    global previewWindow
    global previewText

    previewWindow = tk.Toplevel()
    previewWindow.title("Preview")
    previewWindow.resizable(True, True)
    previewWindow.attributes("-alpha", 0.7, "-topmost", True)
    # previewWindow.overrideredirect(True)
    previewWindow.protocol("WM_DELETE_WINDOW", previewWindow.withdraw)
    previewWindow.bind("<Control-p>", togglePreview)

    fontSize = tk.IntVar(value=16)  # common UI size
    fontSizeCfg = ttk.Spinbox(previewWindow, from_=2, to=75, increment=1, textvariable=fontSize)
    previewFont = large_font.copy()
    previewFont.config(size=fontSize.get())
    fontSizeCfg.pack(expand=True, fill="x")

    def changeFontSize(*_args):  # Name, ???, action
        # Excepts on del or first number because it triggers on emptied input first
        try:
            newsize = fontSize.get()
        except tk.TclError:
            return
        previewFont.config(size=newsize)

    fontSize.trace("w", changeFontSize)
    # def moveWindow(event):
    #     previewWindow.geometry(f'+{event.x_root}+{event.y_root}')
    # previewWindow.bind('<B1-Motion>',moveWindow)

    previewText = tk.Label(previewWindow, font=previewFont, justify="left", anchor="w")
    previewText.pack(expand=True, fill="both")
    previewWindow.withdraw()


def togglePreview(event=None):
    if previewWindow.state() == "normal":
        previewWindow.withdraw()
    else:
        previewWindow.deiconify()


def char_convert(event=None):
    pos = text_box_en.index(tk.INSERT)
    start = pos + "-6c"
    txt = text_box_en.get(start, pos)
    m = re.search(r"[A-Z0-9]+", txt)
    if m:
        try:
            res = chr(int(m.group(0), 16))
        except ValueError:
            return
        text_box_en.replace(f"{start}+{str(m.start())}c", pos, res)


def del_word(event):
    pos = text_box_en.index(tk.INSERT)
    start = "linestart" if event.state & 0x0001 else "wordstart"
    end = "lineend" if event.state & 0x0001 else "wordend"
    if event.keycode == 8:
        text_box_en.delete(f"{pos} -1c {start}", pos)
    elif event.keycode == 46:
        text_box_en.delete(pos, f"{pos} {end}")


def pickColor(useLast=True):
    global LAST_COLOR
    if not useLast or not LAST_COLOR:
        LAST_COLOR = colorchooser.askcolor()[1]  # 0 = rgb tuple, 1=hex str
        defineColor(LAST_COLOR)
    return LAST_COLOR


def defineColor(color: str):
    text_box_en.tag_config(f"color={color}", foreground=color)


def format_text(event):
    if not text_box_en.tag_ranges("sel"):
        print("No selection to format.")
        return
    currentTags = text_box_en.tag_names(tk.SEL_FIRST)
    if event.keysym == "i":
        if "i" in currentTags:
            text_box_en.tag_remove("i", tk.SEL_FIRST, tk.SEL_LAST)
        else:
            text_box_en.tag_add("i", tk.SEL_FIRST, tk.SEL_LAST)
    elif event.keysym == "b":
        if "b" in currentTags:
            text_box_en.tag_remove("b", tk.SEL_FIRST, tk.SEL_LAST)
        else:
            text_box_en.tag_add("b", tk.SEL_FIRST, tk.SEL_LAST)
    elif event.keysym == "C":
        color = f"color={pickColor(not (event.state & 131072))}"  # alt
        if color is None:
            return
        if color in currentTags:
            text_box_en.tag_remove(color, tk.SEL_FIRST, tk.SEL_LAST)
        else:
            text_box_en.tag_add(color, tk.SEL_FIRST, tk.SEL_LAST)
    else:
        return
    return "break"  # prevent control char entry


# https://github.com/python/cpython/issues/97928
def text_count(widget, index1, index2, *options):
    return widget.tk.call((widget._w, "count") + options + (index1, index2))


def tagsToMarkup(widget: tk.Text):
    text = list(widget.get(1.0, tk.END))
    offset = 0
    tagList = list()
    for tag in widget.tag_names():
        tagBaseName = tag.split("=")[0]
        if tagBaseName not in ("i", "b", "color", "size"):
            continue
        ranges = widget.tag_ranges(tag)
        tagList.extend((text_count(widget, "1.0", x, "-chars"), f"<{tag}>") for x in ranges[0::2])
        tagList.extend(
            (text_count(widget, "1.0", x, "-chars"), f"</{tagBaseName}>") for x in ranges[1::2]
        )
    tagList.sort(key=lambda x: x[0])
    for idx, tag in tagList:
        text.insert(idx + offset, tag)
        offset += 1
    return "".join(text)


def insertTaggedTextFromMarkup(widget: tk.Text, text: str = None):
    """Apply unity RT markup in text. This writes the text to the given widget itself for efficiency."""
    if text is None:
        text = widget.get(1.0, tk.END)
    tagList = list()
    offset = 0
    openedTags = dict()
    tagRe = r"<(/?)(([a-z]+)(?:[=#a-z\d]+)?)>"
    for m in re.finditer(tagRe, text, flags=re.IGNORECASE):
        isClose, fullTag, tagName = m.groups()
        if tagName not in ("color", "b", "i", "size"):
            continue
        if isClose:
            openedTags[tagName]["end"] = m.start() - offset
        else:
            tagList.append({"name": fullTag, "start": m.start() - offset})
            openedTags[tagName] = tagList[-1]
            if tagName == "color":
                defineColor(fullTag.split("=")[-1])
        offset += len(m[0])
    # Add the cleaned text
    widget.delete(1.0, tk.END)
    widget.insert(tk.END, re.sub(tagRe, "", text, flags=re.IGNORECASE))
    # Apply tags
    for toTag in tagList:
        widget.tag_add(toTag["name"], f"1.0+{toTag['start']}c", f"1.0+{toTag['end']}c")


def process_text(event):
    opts = {"redoNewlines": False, "replaceMode": "limit", "lineLength": -1, "targetLines": 99}
    if getattr(event, "all", None):
        opts["lineLength"] = 0
        for block in cur_file.textBlocks:
            block["enText"] = textprocess.processText(cur_file, block["enText"], opts)
        proc_text = cur_file.textBlocks[cur_block].get("enText")
    else:
        opts["redoNewlines"] = True if event.state & 0x0001 else False
        proc_text = textprocess.processText(
            cur_file, normalizeEditorText(text_box_en.get(1.0, tk.END)), opts
        )
    text_box_en.delete(1.0, tk.END)
    text_box_en.insert(tk.END, proc_text)
    return "break"


def txt_for_display(text):
    if cur_file.escapeNewline:
        return re.sub(r"(?:\\[rn])+", "\n", text)
    else:
        return text.replace("\r", "")


def txt_for_storage(text):
    return normalizeEditorText(text, "\\n" if cur_file.escapeNewline else "\n")


def normalizeEditorText(text: str, newline: str = "\n"):
    return f" {newline}".join([line.strip() for line in text.strip().split("\n")])


def loadFont(fontPath):
    # code modified from https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
    # origFontList = list(tk.font.families())
    if isinstance(fontPath, bytes):
        pathbuf = create_string_buffer(fontPath)
        AddFontResourceEx = windll.gdi32.AddFontResourceExA
    elif isinstance(fontPath, str):
        pathbuf = create_unicode_buffer(fontPath)
        AddFontResourceEx = windll.gdi32.AddFontResourceExW
    else:
        raise TypeError("fontPath must be bytes or str")

    flags = 0x10 | 0x20  # private and not enumerable
    # flags = 0x10 | 0 # private and enumerable

    numFontsAdded = AddFontResourceEx(byref(pathbuf), flags, 0)
    # print(
    #   f"added {numFontsAdded} fonts:",
    #   [name for name in tk.font.families() if name not in origFontList]
    # )
    # print(tk.font.families()[-3:])

    return numFontsAdded


def tlNames():
    import names

    names.translate(cur_file, forceReload=True)
    load_block()


def nextMissingName():
    for idx, block in enumerate(cur_file.textBlocks):
        if not block.get("enName") and block.get("jpName") not in NAMES_BLACKLIST:
            block_dropdown.current(idx)
            change_block()


def _switchWidgetFocusForced(e):
    e.widget.tk_focusNext().focus()
    return "break"


def onClose(event=None):
    if SAVE_STATE.unsavedChanges:
        unsavedFiles = "\n".join(files[x].name for x in SAVE_STATE.unsavedChanges)
        answer = messagebox.askyesno(
            title="Quit",
            message=f"Unsaved files:\n{unsavedFiles}\nDo you want to quit without saving?",
        )
        if not answer:
            return
    if AUDIO_PLAYER:
        AUDIO_PLAYER.dealloc()
    root.spell_checker.saveNewDict()
    root.quit()


def main():
    global files
    global root
    global cur_chapter
    global cur_block
    global chapter_dropdown
    global block_dropdown
    global btn_next
    global speaker_jp_entry
    global speaker_en_entry
    global block_duration_label
    global block_duration_spinbox
    global text_box_jp
    global text_box_en
    global btn_choices
    global btn_colored
    global save_on_next
    global skip_translated
    global set_humanTl
    global large_font
    global SAVE_STATE

    cur_chapter = 0
    cur_block = 0

    ap = patch.Args("Story editor", types=SUPPORTED_TYPES)
    ap.add_argument("-src")
    ap.add_argument("-dst", help=SUPPRESS)
    args = ap.parse_args()
    if args.src:
        files = [args.src]
    else:
        files = patch.searchFiles(
            args.type, args.group, args.id, args.idx, targetSet=args.set, changed=args.changed
        )
        if not files:
            print("No files match given criteria")
            raise SystemExit

    files.sort()

    SAVE_STATE = SaveState()

    root = tk.Tk()
    root.title("Edit Story")
    root.resizable(False, False)
    if IS_WIN:
        loadFont(r"src/data/RodinWanpakuPro-UmaTl.otf")
    else:
        print(
            "Non-Windows system: To load custom game font install 'src/data/RodinWanpakuPro-B-ex.otf' to system fonts."
        )
    large_font = Font(root, family="RodinWanpakuPro UmaTl B", size=18, weight="normal")
    boldFont = large_font.copy()
    boldFont.config(weight="bold")
    italicFont = large_font.copy()
    italicFont.config(slant="italic")

    chapter_label = tk.Label(root, text="Chapter")
    chapter_label.grid(row=0, column=0)
    textblock_label = tk.Label(root, text="Block")
    textblock_label.grid(row=0, column=2)

    chapter_dropdown = ttk.Combobox(root, width=35)
    chapter_dropdown.formattedList = [f.split("\\")[-1] for f in files]
    chapter_dropdown["values"] = chapter_dropdown.formattedList
    chapter_dropdown.bind("<<ComboboxSelected>>", change_chapter)
    chapter_dropdown.bind("<KeyRelease>", searchChapters)
    chapter_dropdown.search = None
    chapter_dropdown.grid(row=0, column=1, sticky=tk.NSEW)
    block_dropdown = ttk.Combobox(root, width=35)
    block_dropdown.bind("<<ComboboxSelected>>", change_block)
    block_dropdown.grid(row=0, column=3, sticky=tk.NSEW)

    speaker_jp_label = tk.Label(root, text="Speaker (JP)")
    speaker_jp_label.grid(row=1, column=0)
    speaker_jp_entry = tk.Entry(root)
    speaker_jp_entry.grid(row=1, column=1, sticky=tk.NSEW)

    speaker_en_label = tk.Label(root, text="Speaker (EN)")
    speaker_en_label.grid(row=1, column=2)
    speaker_en_entry = tk.Entry(root)
    speaker_en_entry.grid(row=1, column=3, sticky=tk.NSEW)

    block_duration_label = tk.Label(root, text="Text Duration")
    block_duration_label.grid(row=2, column=2)
    block_duration_spinbox = ttk.Spinbox(root, from_=0, to=9999, increment=1, width=5)
    block_duration_spinbox.grid(row=2, column=3, sticky=tk.W)

    text_box_jp = tk.Text(root, width=TEXTBOX_WIDTH, height=4, state="disabled", font=large_font)
    text_box_jp.grid(row=3, column=0, columnspan=4)

    text_box_en = tk.Text(root, width=TEXTBOX_WIDTH, height=6, undo=True, font=large_font)
    text_box_en.grid(row=4, column=0, columnspan=4)
    text_box_en.tag_config("b", font=boldFont)
    text_box_en.tag_config("i", font=italicFont)
    root.spell_checker = SpellCheck(text_box_en)

    frm_btns_bot = tk.Frame(root)
    btn_choices = tk.Button(
        frm_btns_bot,
        text="Choices",
        command=lambda: toggleTextListPopup(target=cur_choices),
        state="disabled",
        width=10,
    )
    btn_choices.grid(row=0, column=0)
    btn_colored = tk.Button(
        frm_btns_bot,
        text="Colored",
        command=lambda: toggleTextListPopup(target=cur_colored),
        state="disabled",
        width=10,
    )
    btn_colored.grid(row=1, column=0)
    btn_listen = tk.Button(frm_btns_bot, text="Listen", command=AudioPlayer.listen, width=10)
    btn_listen.grid(row=0, column=1)
    btn_search = tk.Button(frm_btns_bot, text="Search", command=toggleSearchPopup, width=10)
    btn_search.grid(row=1, column=1)
    btn_reload = tk.Button(frm_btns_bot, text="Reload", command=reload_chapter, width=10)
    btn_reload.grid(row=0, column=2)
    btn_save = tk.Button(frm_btns_bot, text="Save", command=saveFile, width=10)
    btn_save.grid(row=1, column=2)
    btn_prev = tk.Button(frm_btns_bot, text="Prev", command=prev_block, width=10)
    btn_prev.grid(row=0, column=3)
    btn_next = tk.Button(frm_btns_bot, text="Next", command=next_block, width=10)
    btn_next.grid(row=1, column=3)
    frm_btns_bot.grid(row=5, columnspan=4, sticky=tk.NSEW)
    for idx in range(frm_btns_bot.grid_size()[0]):
        frm_btns_bot.columnconfigure(idx, weight=1)

    frm_btns_side = tk.Frame(root)
    side_buttons = (
        tk.Button(
            frm_btns_side, text="Italic", command=lambda: format_text(SimpleNamespace(keysym="i"))
        ),
        tk.Button(
            frm_btns_side, text="Bold", command=lambda: format_text(SimpleNamespace(keysym="b"))
        ),
        tk.Button(frm_btns_side, text="Convert\nunicode codepoint", command=char_convert),
        tk.Button(
            frm_btns_side,
            text="Process text",
            command=lambda: process_text(SimpleNamespace(state=0)),
        ),
        tk.Button(
            frm_btns_side,
            text="Process text\n(clean newlines)",
            command=lambda: process_text(SimpleNamespace(state=1)),
        ),
        tk.Button(
            frm_btns_side,
            text="Process text\n(whole chapter)",
            command=lambda: process_text(SimpleNamespace(all=True)),
        ),
        tk.Button(frm_btns_side, text="Translate speakers", command=tlNames),
        tk.Button(frm_btns_side, text="Find missing speakers", command=nextMissingName),
    )
    for btn in side_buttons:
        btn.pack(pady=3, fill=tk.X)
    frm_btns_side.grid(column=5, row=0, rowspan=5, sticky=tk.NE)

    save_on_next = tk.IntVar()
    save_on_next.set(0)
    save_checkbox = tk.Checkbutton(root, text="Save chapter on block change", variable=save_on_next)
    save_checkbox.grid(row=6, column=1)
    skip_translated = tk.IntVar()
    skip_translated.set(0)
    skip_checkbox = tk.Checkbutton(root, text="Skip translated blocks", variable=skip_translated)
    skip_checkbox.grid(row=6, column=0)
    set_humanTl = tk.IntVar()
    set_humanTl.set(0)
    set_humanTl_checkbox = tk.Checkbutton(root, text="Mark as human TL", variable=set_humanTl)
    set_humanTl_checkbox.grid(row=6, column=2)
    for f in (root, frm_btns_bot, frm_btns_side):
        for w in f.children.values():
            w.configure(takefocus=0)
    text_box_en.configure(takefocus=1)
    speaker_en_entry.configure(takefocus=1)
    text_box_en.bind("<Tab>", _switchWidgetFocusForced)
    speaker_en_entry.bind("<Tab>", _switchWidgetFocusForced)
    text_box_en.focus()

    create_text_list_popup()
    create_search_popup()
    createPreviewWindow()
    chapter_dropdown.current(cur_chapter)
    change_chapter(initialLoad=True)
    block_dropdown.current(cur_block)

    root.bind("<Control-Return>", next_block)
    root.bind("<Control-s>", saveFile)
    root.bind("<Control-S>", saveFile)
    root.bind("<Alt-Up>", prev_block)
    root.bind("<Alt-Down>", next_block)
    root.bind("<Control-Alt-Up>", prev_ch)
    root.bind("<Control-Alt-Down>", next_ch)
    root.bind("<Alt-Right>", copy_block)
    root.bind("<Alt-c>", lambda _: toggleTextListPopup(target=cur_choices))
    text_list_window.bind("<Alt-c>", lambda _: toggleTextListPopup(target=cur_choices))
    root.bind("<Control-Alt-c>", lambda _: toggleTextListPopup(target=cur_colored))
    text_list_window.bind("<Control-Alt-c>", lambda _: toggleTextListPopup(target=cur_colored))
    root.bind("<Alt-x>", char_convert)
    root.bind("<Control-BackSpace>", del_word)
    root.bind("<Control-Shift-BackSpace>", del_word)
    root.bind("<Control-Delete>", del_word)
    root.bind("<Control-Shift-Delete>", del_word)
    text_box_en.bind("<Control-i>", format_text)
    text_box_en.bind("<Control-b>", format_text)
    text_box_en.bind("<Control-C>", format_text)
    text_box_en.bind("<Alt-f>", process_text)
    text_box_en.bind("<Alt-F>", process_text)
    root.bind("<Control-f>", toggleSearchPopup)
    text_box_en.bind("<Control-h>", AudioPlayer.listen)
    root.bind("<Control-p>", togglePreview)

    root.protocol("WM_DELETE_WINDOW", onClose)

    root.mainloop()


if __name__ == "__main__":
    main()
