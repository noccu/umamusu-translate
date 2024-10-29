import re
import tkinter as tk
from functools import partial
from tkinter import colorchooser
from typing import Union, TYPE_CHECKING

from . import fonts
from .spellcheck import SpellCheck

if TYPE_CHECKING:
    from common.types import TranslationFile

TkDisplaysText = Union[tk.Text, tk.Entry, tk.Label]


class ColorManager:
    ACTIVE: str = None

    def __init__(self, master: tk.Text) -> None:
        self.colors: set[str] = set()
        self.master = master

    def pick(self, useActive=True):
        if not useActive or not ColorManager.ACTIVE:
            # 0 = rgb tuple, 1=hex str
            ColorManager.ACTIVE = self.define(colorchooser.askcolor()[1])
        elif ColorManager.ACTIVE not in self.colors:
            self.define(ColorManager.ACTIVE)
        return ColorManager.ACTIVE

    def setActive(self, event, color: str):
        self.master.event_generate("<<Log>>", data=f"Setting color: {color}")
        ColorManager.ACTIVE = color

    def define(self, color: str):
        tagname = f"color={color}"
        if color.startswith("#{"):
            self.master.tag_config(tagname, background="#ff00ff")
        else:
            self.master.tag_config(tagname, foreground=color)
        self.master.tag_bind(tagname, "<Button-3>", partial(self.setActive, color=color))
        self.colors.add(color)
        return color


class TextBox(tk.Text):
    """A tk Text widget with extra features"""

    DEFAULT_WIDTH = 54
    DEFAULT_HEIGHT = 4
    SUPPORTED_TAGS = ("color", "b", "i", "size")
    TAG_RE = r"<(/?)((" f"(?:{'|'.join(SUPPORTED_TAGS)})" r"+)=?([#a-z\d{}]+)?)>"

    # todo: maybe move color to post_init and pass through init itself to tk
    def __init__(self, parent, size: tuple[int] = (None, None), editable:bool = False, font: fonts.Font = None, **kwargs) -> None:
        if not font:
            font = fonts.DEFAULT
        super().__init__(
            parent,
            width=size[0] or TextBox.DEFAULT_WIDTH,
            height=size[1] or TextBox.DEFAULT_HEIGHT,
            font=font,
            state="normal" if editable else "disabled",
            **kwargs
        )
        self.tkRoot = None
        self._editable = self._enabled = editable
        self.font = font
        self.font_italic = fonts.createFrom(self, font, italic=True, suffix="i")
        self.font_bold = fonts.createFrom(self, font, bold=True, suffix="b")
        self.tag_config("b", font=self.font_bold)
        self.tag_config("i", font=self.font_italic)
        self.color = ColorManager(self)
        self.bind("<Alt-Right>", self.copy_block)

    def fontConfig(self, **kwargs):
        self.font.config(**kwargs)
        self.font_bold.config(**kwargs)
        self.font_italic.config(**kwargs)

    def loadRichText(self, text: str = None, tag=None, append=False):
        """Load text into widget, converting unity RT markup to tk tags.
        If no text is given it converts all existing text"""
        if not self._editable:
            self.setActive(True)
        if text is None:
            text = self.get(1.0, tk.END)
        elif text == "":  # shortcut
            clearText(self)
            return
        tagList = list()
        offset = 0
        openedTags = dict()
        for m in re.finditer(TextBox.TAG_RE, text, flags=re.IGNORECASE):
            isClose, fullTag, tagName, tagVal = m.groups()
            if isClose:
                openedTags[tagName]["end"] = m.start() - offset
            else:
                tagList.append({"name": fullTag, "value": tagVal, "start": m.start() - offset})
                openedTags[tagName] = tagList[-1]
                if tagName == "color":
                    self.color.define(tagVal)
                elif tagName == "size" and fullTag not in self.tag_names():
                    ratio = int(tagVal) / 40 #todo: story content, need to generalize
                    newSize = round(self.font.cget("size") * ratio)
                    newSizeFont = fonts.createFrom(self, self.font, newSize)
                    self.tag_config(fullTag, font=newSizeFont)
            offset += len(m[0])
        tagBase = self.index(f"{tk.END}-1c") if append else "1.0"
        # Add the cleaned text
        setText(self, re.sub(TextBox.TAG_RE, "", text, flags=re.IGNORECASE), append, tag)
        # Apply tags
        for toTag in tagList:
            self.tag_add(toTag["name"], f"{tagBase}+{toTag['start']}c", f"{tagBase}+{toTag['end']}c")
        if not self._editable:
            self.setActive(False)

    def toRichText(self, start=1.0, end=tk.END):
        text = list(self.get(start, end))
        end = self.index(end)
        offset = 0
        tagList = list()
        for tag in self.tag_names():
            tagBaseName = tag.split("=")[0]
            if tagBaseName not in ("i", "b", "color", "size"):
                continue
            # ranges = self.tag_ranges(tag)
            for tagStart, tagEnd in TextBox.deinterleaveTagRange(self.tag_ranges(tag)):
                if self.compare(tagStart, "<", start) or self.compare(tagEnd, ">", end):
                    continue
                tagList.append((text_count(self, start, tagStart, "-chars"), f"<{tag}>"))
                tagList.append((text_count(self, start, tagEnd, "-chars"), f"</{tagBaseName}>"))
        tagList.sort(key=lambda x: x[0])  # sort by start idx
        for idx, tag in tagList:
            text.insert(idx + offset, tag)
            offset += 1
        return "".join(text)

    @staticmethod
    def deinterleaveTagRange(tagRange):
        for i in range(0, len(tagRange), 2):
            yield tagRange[i], tagRange[i + 1]

    def clear(self):
        wasEnabled = self._enabled
        if not wasEnabled:
            self.setActive(True)
        clearText(self)
        if not wasEnabled:
            self.setActive(False)

    def setActive(self, state:bool):
        if self._enabled == state:
            return
        self._enabled = state  # keep a simple bool, gdi tk
        self.config(state="normal" if state else "disabled")

    def copy_block(self, event=None):
        """Copies the text of this block or its parent to the clipboard"""
        if self.tkRoot is None:
            return
        self.tkRoot.clipboard_clear()
        self.tkRoot.clipboard_append(
            getText(getattr(self, "linkedTextBox", self)).replace("\r", "")
        )

    def linkTo(self, target:"TextBox", root: tk.Tk):
        self.linkedTextBox = target
        self.tkRoot = root


class TextBoxEditable(TextBox):
    def __init__(self, parent, size: tuple[int] = (None, None), font: fonts.Font = None, **kwargs) -> None:
        super().__init__(parent, size, True, font, **kwargs)
        self.config(undo=True)
        self.spellChecker = SpellCheck(self)
        self.rawMode = False
        # Move default class binds last to allow overwriting
        this, cls, toplevel, all = self.bindtags()
        self.bindtags((this, toplevel, all, cls))
        # Keybinds
        self.bind("<Alt-x>", self.char_convert)
        self.bind("<Control-BackSpace>", self.del_word)
        self.bind("<Control-Shift-BackSpace>", self.del_word)
        self.bind("<Control-Delete>", self.del_word)
        self.bind("<Control-Shift-Delete>", self.del_word)
        self.bind("<Control-i>", self.format_text)
        self.bind("<Control-b>", self.format_text)
        self.bind("<Control-C>", self.format_text)
        self.bind("<Control-d>", self.format_text)
        self.bind("<Control-Shift-Up>", lambda e: self.moveLine(e, -1))
        self.bind("<Control-Shift-Down>", lambda e: self.moveLine(e, 1))

    def loadRichText(self, text: str = None, tag=None, append=False):
        if self.rawMode:
            setText(self, text)
        else:
            super().loadRichText(text, tag, append)
        self.spellChecker.check_spelling()
        self.edit_modified(False)

    def format_text(self, event):
        if event.keysym == "d":
            self.rawMode = not self.rawMode
            self.loadRichText(normalize(self.toRichText()))
            return
        if not self.tag_ranges("sel"):
            self.master.event_generate("<<Log>>", data="No selection to format.")
            return
        if event.keysym == "i":
            self.toggleSelectionTag("i")
        elif event.keysym == "b":
            self.toggleSelectionTag("b")
        elif event.keysym == "C":
            color = f"color={self.color.pick(not (event.state & 131072))}"  # alt
            if color is None:
                return
            self.toggleSelectionTag(color)
        else:
            return
        self.edit_modified(True)
        return "break"  # prevent control char entry

    def toggleSelectionTag(self, tag):
        currentTags = self.tag_names(tk.SEL_FIRST)
        if tag in currentTags:
            self.tag_remove(tag, tk.SEL_FIRST, tk.SEL_LAST)
        else:
            self.tag_add(tag, tk.SEL_FIRST, tk.SEL_LAST)

    def del_word(self, event):
        shift = event.state & 0x0001
        if event.keycode == 8:  # backspace
            ptn = r"^" if shift else r"[^ …—\.?!]+|^"
            sIdx = self.search(ptn, index=tk.INSERT, backwards=True, regexp=True, nocase=True)
            self.delete(sIdx, tk.INSERT)  #
        elif event.keycode == 46:  # delete
            ptn = r".$" if shift else r" ?.(?=[ …—\.?!]|$)"
            sIdx = self.search(ptn, index=tk.INSERT, backwards=False, regexp=True, nocase=True)
            self.delete(tk.INSERT, sIdx + "+1c")
        return "break"

    def char_convert(self, event=None):
        pos = self.index(tk.INSERT)
        start = pos + "-6c"
        txt = self.get(start, pos)
        m = re.search(r"[A-Z0-9]+", txt)
        if m:
            try:
                res = chr(int(m.group(0), 16))
            except ValueError:
                return
            self.replace(f"{start}+{str(m.start())}c", pos, res)
        return "break"

    def moveLine(self, event, dir: int):
        text = getText(self).split("\n")[:-1]  # tk newline
        curIdx = int(self.index(tk.INSERT).split(".")[0]) - 1
        newIdx = (curIdx + dir) % len(text)
        curLine = text[curIdx]
        text[curIdx] = text[newIdx]
        text[newIdx] = curLine
        setText(self, "\n".join(text))
        self.mark_set(tk.INSERT, f"{newIdx + 1}.0")
        return "break"

    def toggleSpellCheck(self, active:bool=None):
        """Toggle spellcheck state or set on/off explicitly."""
        if active is None:
            self.spellChecker.enabled = not self.spellChecker.enabled
        else:
            self.spellChecker.enabled = active


def process_text(file: "TranslationFile", text: str = None, redoNewlines: bool = False):
    """Process given text or whole file when no text given.
    When whole file, assumes line lengths are correct and skips adjustment."""
    import textprocess

    opts = {"redoNewlines": redoNewlines, "replaceMode": "limit", "lineLength": -1, "targetLines": 99}
    if text:
        return textprocess.processText(file, text, opts)
    else:
        opts["lineLength"] = 0
        for block in file.genTextContainers():
            if len(block["enText"]) == 0 or "skip" in block:
                continue
            block["enText"] = textprocess.processText(file, block["enText"], opts)


# https://github.com/python/cpython/issues/97928
def text_count(widget, index1, index2, *options):
    return widget.tk.call((widget._w, "count") + options + (index1, index2))


def for_display(file, text):
    if file.escapeNewline:
        return re.sub(r"(?:\\[rn])+", "\n", text)
    else:
        return text.replace("\r", "")


def for_storage(file, text):
    return normalize(text, "\\n" if file.escapeNewline else "\n")


def normalize(text: str, newline: str = "\n"):
    return f" {newline}".join([line.strip() for line in text.strip().split("\n")])


def getText(widget: TkDisplaysText):
    """Return the full text of supported widgets."""
    if isinstance(widget, tk.Label):
        return widget.cget("text")
    elif isinstance(widget, tk.Entry):
        return widget.get()
    elif isinstance(widget, tk.Text):
        return widget.get(1.0, tk.END)


def setText(widget: TkDisplaysText, text: str, append=False, tag=None):
    """Sets full text of supported widgets."""
    if isinstance(widget, tk.Label):
        widget.config(text=text)
    else:
        if not append:
            clearText(widget)
        if isinstance(widget, tk.Entry):
            widget.insert(0, text)
        elif isinstance(widget, tk.Text):
            widget.insert(tk.END if append else 1.0, text, tag)
        else:
            raise ValueError


def clearText(widget: TkDisplaysText):
    """Clears all text from widget"""
    if isinstance(widget, tk.Label):
        widget.config(text="")
    elif isinstance(widget, tk.Entry):
        widget.delete(0, tk.END)
    elif isinstance(widget, tk.Text):
        widget.delete(1.0, tk.END)
    else:
        raise ValueError
