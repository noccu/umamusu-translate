import re
import tkinter as tk
from functools import partial
from tkinter.font import Font

import symspellpy

from common.types import TranslationFile

from .display import PopupMenu

'''
#! DEV DISABLE
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
        self._db = sqlite3.connect(const.GAME_META_FILE)
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
        if not const.IS_WIN:
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

'''


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
