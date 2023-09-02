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


