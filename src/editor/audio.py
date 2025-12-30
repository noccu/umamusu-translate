from functools import partial
from dataclasses import dataclass, field as datafield
from itertools import zip_longest
from typing import TYPE_CHECKING

from common import patch, constants as const
from common.types import GameBundle

if const.IS_WIN:
    import apsw
    import wave

    import pyaudio
    from PyCriCodecs import AWB, HCA, ACB

    import restore

if TYPE_CHECKING:
    from .app import Editor


@dataclass
class PlaySegment:
    idx: int
    startTime: int
    endTime: int
    timeBased: bool = datafield(init=False, compare=False)

    def __post_init__(self):
        self.timeBased = self.startTime is not None
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
    def fromBlock(cls, block: dict, nextBlock: dict):
        idx = block.get("voiceIdx")
        start = block.get("time")
        end = None
        if start:  # Time-based (lyrics)
            start = int(start)
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
    subFiles: dict[int, bytes] | None = None

    def __init__(self, master: "Editor") -> None:
        self.pyaud = pyaudio.PyAudio()
        self._db = apsw.Connection(f"file:{str(const.GAME_META_FILE)}?hexkey={const.DB_KEY}", apsw.SQLITE_OPEN_URI | apsw.SQLITE_OPEN_READONLY)
        self._mdb = apsw.Connection(str(const.GAME_MASTER_FILE), apsw.SQLITE_OPEN_READONLY)
        self._restoreArgs = restore.parseArgs([])
        self.master = master

    def dealloc(self):
        self._db.close()
        for stream, wavFile in zip(self.outStreams, self.wavFiles):
            if isinstance(stream, pyaudio.PyAudio.Stream):
                stream.stop_stream()
                stream.close()
            self._closeWavStream(wavFile)
        self.pyaud.terminate()

    def play(self, storyId: patch.StoryId, voice: PlaySegment, sType):
        """Plays audio for a specific text block"""
        qStoryId = patch.StoryId.queryfy(storyId)
        if not voice.timeBased and voice.idx < 0:
            self.master.status.log("Text block is not voiced.")
            return
        # New assets
        if reloaded := self.curPlaying[0] != storyId:
            if sType == "home":
                # sound/c/snd_voi_story_00001_02_1054001.acb
                stmt = rf"SELECT h FROM a WHERE n LIKE 'sound%{qStoryId.set}\_{qStoryId.group}\_{qStoryId.id}{qStoryId.idx}\.a_b' ORDER BY n ESCAPE '\'"
            elif sType == "lyrics":
                stmt = f"SELECT h FROM a WHERE n LIKE 'sound/l/{qStoryId.id}/snd_bgm_live_{qStoryId.id}_chara%.a_b' ORDER BY n"
            else:
                stmt = f"SELECT h FROM a WHERE n LIKE 'sound%{qStoryId}.a_b' ORDER BY n"
            hashes = self._db.execute(stmt).fetchall()
            if hashes is None:
                if sType == "story":
                    idx = int(storyId.idx)
                    if idx > 4 and storyId.group != "06":
                        storyId.group = "06"
                        storyId.idx = f"{idx-4:03}"
                        self.play(storyId, voice, sType)
                        return
                self.master.status.log(f"Couldn't find audio asset for {storyId} -> {qStoryId}.")
                return

            (acb_hash,), (awb_hash,) = hashes
            acb_asset = GameBundle.fromName(acb_hash, load=False)
            acb_asset.bundleType = "sound"
            if not acb_asset.exists:
                restore.save(acb_asset, self._restoreArgs)
            awb_asset = GameBundle.fromName(awb_hash, load=False)
            awb_asset.bundleType = "sound"
            if not awb_asset.exists:
                restore.save(awb_asset, self._restoreArgs)
            self.wavFiles.clear()
            self.load(str(acb_asset.bundlePath), str(awb_asset.bundlePath))
        # New subfile/time
        if voice.timeBased and reloaded:  # lyrics, add all tracks
            for file in self.subFiles.values():
                self.wavFiles.append(self.decodeAudio(file))
        elif not voice.timeBased and (
            reloaded or self.curPlaying[1].idx != voice.idx
        ):  # most things, add requested track
            try:
                audData = self.decodeAudio(self.subFiles[voice.idx])
            except KeyError:
                self.master.status.log("Index out of range")
                return
            if self.wavFiles:
                self.wavFiles[0] = audData
            else:
                self.wavFiles.append(audData)
        self.curPlaying = (storyId, voice)
        self._playAudio(voice)

    def load(self, acb_path:str, awb_path: str):
        """Loads the main audio container at path"""
        # Game uses cue sheets, matched to ACB data. This doesn't always map linearly to AWB tracks.
        # We assume ACBs map to a single AWB.
        acb_file = ACB(acb_path)
        awbFile = AWB(awb_path)
        # getfile_atindex seems to corrupt half the files. The method works differently
        # and returns different data (likely broken), so we work around that.
        sub_files = list(awbFile.getfiles())
        #* Int-indexed dict
        self.subFiles = {
            cue_entry["CueId"][1]: sub_files[cue_entry["ReferenceIndex"][1]]
            for cue_entry in acb_file.payload[0]["CueTable"]
        }
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
            self.master.status.log("No WAV loaded.")
            return
        for i, (stream, wavFile) in enumerate(zip_longest(self.outStreams, self.wavFiles)):
            if wavFile.getfp().closed:
                self.master.status.log("WAV unexpectedly closed")
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

    def listen(self, event=None):
        file = self.master.nav.cur_file
        block = self.master.nav.cur_block
        if not const.IS_WIN:
            self.master.status.log("Audio currently only supported on Windows")
            return
        voice = PlaySegment.fromBlock(file.textBlocks[block], file.textBlocks[block + 1])
        if not voice:
            self.master.status.log("Old file version, does not have voice info.")
            return "break"
        storyId = file.data.get("storyId")
        if not storyId:
            self.master.status.log("File has an invalid storyid.")
            return "break"
        elif len(storyId) < 9 and file.type != "lyrics":
            # Preview type would work but I don't understand
            # the format/where it gets info unless it's really just awbTracks[15:-1]
            self.master.status.log("Unsupported type.")
            return "break"
        elif voice is None:
            self.master.status.log("No voice info found for this block.")
            return "break"
        sType = file.type or "story"
        self.play(patch.StoryId.parse(sType, storyId), voice, sType)
        return "break"

# ACB tries to load the linked or embedded AWB and fails. Turn it off.
ACB.load_awb = lambda *_: None