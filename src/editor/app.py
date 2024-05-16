from pathlib import Path
import re
import tkinter as tk
from tkinter import messagebox, ttk
from types import SimpleNamespace
from functools import partial
from subprocess import run
import ast

from common import constants as const, utils
from common.constants import NAMES_BLACKLIST, TRANSLATION_FOLDER
from common.types import TranslationFile, StoryId
from textprocess import calcLineLen

from . import display, files, navigator, text, fonts
from .spellcheck import SpellCheck
from .audio import AudioPlayer

# Monkey patch tk event userdata because 5 lines of code too hard for tk maintainers
class tuplehack(tuple):
    def __len__(self):
        return super().__len__() - 1
tk.Misc._subst_format = tuplehack(('%#', '%b', '%d', '%f', '%h', '%k',
             '%s', '%t', '%w', '%x', '%y',
             '%A', '%E', '%K', '%N', '%W', '%T', '%X', '%Y', '%D'))
tk.Misc._subst_format_str = " ".join(tk.Misc._subst_format)
_o_sub = tk.Misc._substitute
def _sub(self, *args):
    args = list(args)
    data = args.pop(2)
    try:
        if data[0] == "{":
            data = ast.literal_eval(data)
    except:
        pass
    ev_data = _o_sub(self, *args)
    if isinstance(ev_data[0], tk.Event):
        ev_data[0].user_data = data
    return ev_data
tk.Misc._substitute = _sub

class Options:
    def __init__(self) -> None:
        self.markHuman = tk.BooleanVar()
        self.saveOnBlockChange = tk.BooleanVar()
        self.skip_translated = tk.BooleanVar()
        self.alwaysOnTop = tk.BooleanVar()


class Editor:
    COLOR_WIN = "systemWindow" if const.IS_WIN else "white"
    COLOR_BTN = "SystemButtonFace" if const.IS_WIN else "gray"

    def __init__(self) -> None:
        root = tk.Tk()
        root.title("File Editor")
        root.resizable(False, False)
        self.root = root
        fonts.init(root)

        # Freeeedom!
        global copyToClipboard
        def copyToClipboard(text:str):
            root.clipboard_clear()
            root.clipboard_append(text)

        # Managers
        self.options = Options()
        self.fileMan = files.FileManager(self)
        self.nav = navigator.Navigator(self)
        self.audio = AudioPlayer(self)
        self.status = Status(self)
        # Windows
        self.extraText = AdditionalTextWindow(self)
        self.search = SearchWindow(self)
        self.preview = PreviewWindow(self)
        self.notes = SpeakerNotes(self)
        self.textLog = TextLog(self)
        self.merging = False

        # Nav
        frm_filenav = tk.Frame(root)
        chapters = ttk.Combobox(frm_filenav, width=40, font=fonts.UI_JP)
        chapters.bind("<<ComboboxSelected>>", self.nav.change_chapter)
        chapters.bind("<KeyRelease>", self.nav.searchChapters)
        blocks = ttk.Combobox(frm_filenav, width=40, font=fonts.UI_JP, state="readonly")
        blocks.bind("<<ComboboxSelected>>", self.nav.change_block)

        frm_filenav.rowconfigure((0,1), weight=1)
        tk.Label(frm_filenav, text="Chapter").grid(row=0, column=0, sticky=tk.E)
        tk.Label(frm_filenav, text="Block").grid(row=1, column=0, sticky=tk.E)
        chapters.grid(row=0, column=1)
        blocks.grid(row=1, column=1)

        # Speakers
        frm_speakers = tk.Frame(root)
        fnt_speakers_en = fonts.create(root, size=9)
        self.speakerJp = speaker_jp_entry = tk.Entry(frm_speakers, state="readonly", font=fonts.UI_JP)
        self.speakerEn = speaker_en_entry = tk.Entry(frm_speakers, width=26, font=fnt_speakers_en)
        tk.Label(frm_speakers, text="Speaker (JP)").grid()
        tk.Label(frm_speakers, text="Speaker (EN)").grid(row=1)
        speaker_jp_entry.grid(row=0, column=1, sticky=tk.EW)
        speaker_en_entry.grid(row=1, column=1)
        tk.Button(frm_speakers, text="Translate all", command=self.tlNames).grid(row=0, column=2)
        tk.Button(frm_speakers, text="Find missing", command=self.nav.nextMissingName).grid(row=1, column=2)

        # Text editing
        frm_text_edit = tk.Frame(root)
        self.textBoxJp = text.TextBox(frm_text_edit, size=(None,5))
        self.textBoxEn = text_box_en = text.TextBoxEditable(frm_text_edit, size=(None, 6))
        text_box_en.linkTo(self.textBoxJp, root)
        self.textBoxJp.pack()
        text_box_en.pack()

        self.choices = Choices(self)

        # Metadata
        frm_meta = tk.Frame(root)
        self.blockDurationLabel = block_duration_label = tk.Label(frm_meta, text="Duration")
        self.blockDuration = block_duration_spinbox = ttk.Spinbox(frm_meta, from_=0, to=1000, increment=1, width=5)
        self.titleEn = txt_title = tk.StringVar(frm_meta)
        txt_title.trace_add("write", self.fileMan.save_title)
        titleLabel = tk.Label(frm_meta, text="Title (EN)")
        titleEn = tk.Entry(frm_meta, width=27, font=fnt_speakers_en, textvariable=txt_title)
        block_duration_label.pack(side=tk.LEFT)
        block_duration_spinbox.pack(side=tk.LEFT)
        titleLabel.pack(side=tk.LEFT)
        titleEn.pack(side=tk.LEFT)

        # Bottom bar
        frm_btns_bot = tk.Frame(root)
        def open_folder():
            sid = StoryId.parse(self.nav.cur_file.type, self.nav.cur_file.getStoryId())
            run(("explorer", TRANSLATION_FOLDER.joinpath(sid.type, sid.asPath()).resolve()))
        tk.Button(frm_btns_bot, text="Open folder", width=10, command=open_folder).grid(row=0, column=0)
        self.btnColored = btn_colored = tk.Button(
            frm_btns_bot,
            text="Colored",
            command=lambda: self.extraText.toggle(target=self.extraText.cur_colored),
            state="disabled",
            width=10,
        )
        tk.Button(frm_btns_bot, text="Text log", command=self.textLog.toggle, width=10).grid(row=1, column=1)
        btn_colored.grid(row=0, column=1)
        tk.Button(frm_btns_bot, text="Listen", command=self.audio.listen, width=10).grid(row=0, column=2)
        tk.Button(frm_btns_bot, text="Search", command=self.search.toggle, width=10).grid(row=1, column=2)
        tk.Button(frm_btns_bot, text="Reload", command=self.nav.reload_chapter, width=10).grid(row=0, column=3)
        tk.Button(frm_btns_bot, text="Save", command=self.saveFile, width=10).grid(row=1, column=3)
        btn_prev = tk.Button(frm_btns_bot, text="Prev", command=self.nav.prev_block, width=10)
        btn_next = tk.Button(frm_btns_bot, text="Next", command=self.nav.next_block, width=10)
        btn_prev.grid(row=0, column=4)
        btn_next.grid(row=1, column=4)
        for idx in range(frm_btns_bot.grid_size()[0]):
            frm_btns_bot.columnconfigure(idx, weight=1)

        # Side bar
        # Todo: split off?
        frm_editing_actions = tk.Frame(root)
        editing_actions = (
            ("i", lambda: text_box_en.format_text(SimpleNamespace(keysym="i"))),
            ("b", lambda: text_box_en.format_text(SimpleNamespace(keysym="b"))),
            ("fmt", self._evProcessText),
            ("fmt hard", lambda: self._evProcessText(redoNewlines=True)),
            ("fmt file", lambda: self._evProcessText(wholeFile=True)),
        )
        for txt, cmd in editing_actions:
            tk.Button(frm_editing_actions, text=txt, command=cmd).pack(side=tk.LEFT, padx=2)

        ## Options
        opts = (
            ("Save chapter on block change", self.options.saveOnBlockChange),
            ("Skip translated blocks", self.options.skip_translated),
            ("Mark as human TL", self.options.markHuman),
            ("Keep editor on top", self.options.alwaysOnTop),
        )
        f_options = tk.Frame(root)
        for txt, var in opts:
            tk.Checkbutton(f_options, text=txt, variable=var).pack(side=tk.LEFT, ipadx=3)

        # Init required parts
        self.nav.uiInit(chapters, blocks, btn_next, btn_prev)
        self.options.alwaysOnTop.trace_add("write", self._evhSetOnTop)

        # Build UI
        frm_filenav.grid(row=0, column=0, sticky=tk.NSEW, pady=5)
        frm_speakers.grid(row=0, column=1, sticky=tk.NSEW, pady=5)
        frm_text_edit.grid(row=1, columnspan=2)
        self.choices.widget.grid_configure(row=1, column=2, sticky=tk.NSEW)
        frm_editing_actions.grid(row=3, column=0, sticky=tk.W, pady=5)
        self.notes.widget.grid(row=0, column=3, rowspan=2, sticky=tk.NSEW)
        frm_meta.grid(row=3, column=1, sticky=tk.W)
        frm_btns_bot.grid(row=4, columnspan=2, sticky=tk.NSEW)
        f_options.grid(row=5, columnspan=2, sticky=tk.EW)
        self.status.widget.grid(row=6, columnspan=2, sticky=tk.EW)

        ## Focus management
        for f in (root, frm_btns_bot, frm_editing_actions):
            for w in f.children.values():
                w.configure(takefocus=0)
        text_box_en.configure(takefocus=1)
        speaker_en_entry.configure(takefocus=1)
        text_box_en.bind("<Tab>", display._switchWidgetFocusForced)
        speaker_en_entry.bind("<Tab>", display._switchWidgetFocusForced)
        text_box_en.focus()

        ## Keybinds
        root.bind("<Control-Return>", self.nav.next_block)
        root.bind_all("<Control-s>", self.saveFile)
        root.bind("<Alt-Up>", self.nav.prev_block)
        root.bind("<Alt-Down>", self.nav.next_block)
        root.bind("<Control-Alt-Up>", self.nav.prev_ch)
        root.bind("<Control-Alt-Down>", self.nav.next_ch)
        root.bind(
            "<Alt-c>", lambda _: self.extraText.toggle(target=self.extraText.cur_colored)
        )
        text_box_en.bind("<Alt-f>", self._evProcessText)
        text_box_en.bind("<Alt-F>", lambda e: self._evProcessText(e, redoNewlines=True))
        root.bind("<Control-f>", self.search.toggle)
        root.bind_all("<Control-h>", self.audio.listen)
        root.bind("<Control-p>", self.preview.toggle)
        root.bind("<Alt-s>", lambda _: self.options.skip_translated.set(not self.options.skip_translated.get()))

        # Event handlers
        root.bind_all("<<Log>>", lambda e: self.status.log(e.user_data))
        root.bind_all("<<BlockChangeStart>>", self.notes.save)
        root.bind_all("<<BlockChangeEnd>>", self.notes.load)
        root.protocol("WM_DELETE_WINDOW", self.onClose)

    def start(self):
        self.root.mainloop()

    def saveFile(self, event=None):
        self.fileMan.saveFile(self.nav, saveAll=event and (event.state & 0x0001))

    def onClose(self, event=None):
        if self.fileMan.saveState.unsavedChanges:
            unsavedFiles = "\n".join(
                self.fileMan.files[x].name for x in self.fileMan.saveState.unsavedChanges
            )
            answer = messagebox.askyesno(
                title="Quit",
                message=f"Unsaved files:\n{unsavedFiles}\nDo you want to quit without saving?",
            )
            if not answer:
                return
        if self.audio:
            self.audio.dealloc()
        SpellCheck.saveNewDict()
        self.notes.onExit()
        self.root.quit()

    def _evhSetOnTop(self, *_):
        if self.options.alwaysOnTop.get():
            self.root.attributes("-topmost", True)
            self.root.lift()
        else:
            self.root.attributes("-topmost", False)
        self.root.update()

    def _evProcessText(self, event=None, wholeFile=False, redoNewlines=False):
        """Event handler for external text process calls."""
        if wholeFile:
            self.fileMan.save_block(self.nav)
            text.process_text(self.nav.cur_file, redoNewlines=False)
            self.fileMan.load_block(self.nav.cur_file, self.nav.cur_block)
        else:
            txt = text.getText(self.textBoxEn)
            txt = text.process_text(self.nav.cur_file, text.normalize(txt), redoNewlines=redoNewlines)
            self.textBoxEn.loadRichText(txt)
        return "break"

    def tlNames(self):
        import names

        names.translate(self.nav.cur_file, forceReload=True)
        self.fileMan.load_block(self.nav.cur_file, self.nav.cur_block)

    def merge(self, files):
        self.mergeWWindow = MergeWindow(self)
        self.mergeWWindow.setFiles(files)


class Choices:
    def __init__(self, editor: Editor):
        self.editor = editor
        self.textBoxes:list[tuple[text.TextBox, text.TextBoxEditable]] = list()
        self.curChoices = None
        scrollFrame = display.ScrollableFrame(editor.root)
        self.widget = scrollFrame  # Use this to add to UI
        font = fonts.create(scrollFrame, size=14, id="choices")

        idx = 0
        for i in range(0, 5):
            cur_jp_text = text.TextBox(scrollFrame.content, size=(31,1), font=font, takefocus=0)
            cur_jp_text.grid(row=idx, column=0, sticky=tk.W)
            cur_en_text = text.TextBoxEditable(scrollFrame.content, size=(31, 2), font=font)
            cur_en_text.linkTo(cur_jp_text, editor.root)
            cur_en_text.grid(row=idx+1, column=0, sticky=tk.W)
            follow_btn = tk.Button(
                scrollFrame.content,
                text="≫",
                relief="groove",
                takefocus=0,
                command=partial(self._evFollowBlock, i))
            follow_btn.grid(row=idx, column=1, rowspan=2, sticky=tk.NSEW)
            self.textBoxes.append((cur_jp_text, cur_en_text))
            cur_en_text.bind("<Tab>", display._switchWidgetFocusForced)
            if i < 4:
                ttk.Separator(scrollFrame.content, orient=tk.HORIZONTAL).grid(row=idx+2, column=0, columnspan=2, pady=8)
            idx += 3

    def _evFollowBlock(self, choiceId):
        if choiceId >= len(self.curChoices):
            self.editor.status.log("This choice is not active!")
            return
        blockId = self.curChoices[choiceId].get("nextBlock")
        if blockId and blockId != -1:
            self.editor.nav.change_block(blockId - 1)

    def setChoices(self, choices:list):
        self.curChoices = choices
        for i, (jpBox, enBox) in enumerate(self.textBoxes):
            if i >= len(choices):
                jpBox.clear()
                enBox.clear()
                enBox.setActive(False)
                continue
            jpBox.loadRichText(choices[i]["jpText"])
            enBox.setActive(True)
            enBox.loadRichText(choices[i]["enText"])

    def saveChoices(self):
        if not self.curChoices:
            return
        for i, (jpBox, enBox) in enumerate(self.textBoxes):
            if i == len(self.curChoices):
                break
            self.curChoices[i]["enText"] = text.normalize(enBox.toRichText())
        self.curChoices = None

    # def clearChoices(self, boxes: list = None):
    #     for jpBox, enBox in (boxes or self.textBoxes):
    #         jpBox.clear()
    #         enBox.clear()


class AdditionalTextWindow:
    def __init__(self, master: Editor) -> None:
        self.master = master
        self.textBoxes = list()
        self.cur_text_list = None
        self.cur_choices = None
        self.cur_colored = None

        root = tk.Toplevel(master.root)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.title("Additional Texts")
        # root.geometry("580x450")  # 800 for full
        self.root = root

        root.bind("<Alt-c>", lambda _: self.toggle(target=self.cur_colored))

        scrollFrame = display.ScrollableFrame(root, scrollbar=True)
        for i in range(0, 5):
            cur_jp_text = text.TextBox(scrollFrame.content, size=(30,2), takefocus=0)
            cur_jp_text.pack(anchor="w")
            cur_en_text = text.TextBoxEditable(scrollFrame.content, size=(30, 2))
            cur_en_text.linkTo(cur_jp_text, master.root)
            cur_en_text.pack(anchor="w")
            self.textBoxes.append((cur_jp_text, cur_en_text))
            cur_en_text.bind("<Tab>", display._switchWidgetFocusForced)
            if i == 0:
                self.firstText = cur_en_text
            if i < 4:
                ttk.Separator(scrollFrame.content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        scrollFrame.pack(fill="both", expand=True)

        self.close()

    def close(self):
        for i, t in enumerate(self.textBoxes):
            jpBox, enBox = t
            if self.cur_text_list and i < len(self.cur_text_list):
                # Choice don't really need special handling
                self.cur_text_list[i]["enText"] = text.normalize(enBox.get(1.0, tk.END))
            jpBox["state"] = "normal"  # Enable deletion...
            jpBox.delete(1.0, tk.END)
            enBox.delete(1.0, tk.END)
            jpBox["state"] = "disabled"  # Disable again... tk things
            enBox["state"] = "disabled"
        self.root.withdraw()

    def show(self):
        if self.cur_text_list:
            self.cur_text_list = self.cur_text_list
            for i, t in enumerate(self.textBoxes):
                if i < len(self.cur_text_list):
                    jpBox, enBox = t
                    jpBox["state"] = "normal"  # enable insertion...
                    enBox["state"] = "normal"
                    jpBox.insert(tk.END, self.cur_text_list[i]["jpText"])
                    enBox.insert(tk.END, self.cur_text_list[i]["enText"])
                    jpBox["state"] = "disabled"
            self.root.deiconify()
            self.firstText.focus()

    def toggle(self, event=None, allowShow=True, target=None):
        if self.root.state() == "normal":
            self.close()
            # Actually open other type if old window closed by opening another type,
            if target is not self.cur_text_list:
                self.toggle(allowShow=allowShow, target=target)
        elif allowShow:
            self.cur_text_list = target
            self.show()


class SearchWindow:
    class State:
        def __init__(self, master: Editor):
            self.master = master
        def save(self):
            self.chapter = self.master.nav.cur_chapter
            self.block = self.master.nav.cur_block
            self.save_per_block = self.master.options.saveOnBlockChange.get()
            self.skip_translated = self.master.options.skip_translated.get()
        def setPos(self, chapter, block):
            self.chapter = chapter
            self.block = block

    def __init__(self, master: Editor) -> None:
        root = tk.Toplevel(master.root)
        root.title("Search")
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<Control-f>", self.toggle)

        s_var_field = tk.StringVar(root, value="enText")
        s_var_re = tk.StringVar(root)
        lb_field = tk.Label(root, text="Field:")
        lb_re = tk.Label(root, text="Search (supports regex):")
        search_field = tk.Entry(root, width=20, textvariable=s_var_field)
        search_re = tk.Entry(root, name="filter", width=40, textvariable=s_var_re)
        lb_field.grid(column=0, sticky=tk.E)
        lb_re.grid(column=0, sticky=tk.E)
        search_field.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        search_re.grid(row=1, column=1, columnspan=2, sticky=tk.W)
        search_re.bind("<Return>", self.search)

        search_chapters = tk.BooleanVar(root, False)
        chk_search_chapters = tk.Checkbutton(
            root, text="Search all loaded chapters", variable=search_chapters
        )
        chk_search_chapters.grid(column=2, pady=5, sticky=tk.E)

        btn_search = tk.Button(root, text="Search / Next", name="search", command=self.search)
        btn_return = tk.Button(
            root, text="Return to original block", command=self.restoreState, padx=5
        )
        btn_return.grid(row=2, column=0, padx=5)
        btn_search.grid(row=2, column=1)

        search_filter = s_var_field, s_var_re
        for v in (s_var_field, s_var_re, search_chapters):
            v.trace_add("write", self.reset_search)

        self.master = master
        self.root = root
        self.filter = search_filter
        self.optSearchAll = search_chapters
        self.searchBox = search_re
        self.savedState = self.State(master)
        self.curState = self.State(master)
        self.reset_search()  # sets cur state
        root.withdraw()

    def show(self):
        self.savedState.save()
        self.master.options.saveOnBlockChange.set(False)
        self.master.options.skip_translated.set(False)
        self.root.deiconify()
        self.searchBox.focus()

    def close(self):
        self.master.options.saveOnBlockChange.set(self.savedState.save_per_block)
        self.master.options.skip_translated.set(self.savedState.skip_translated)
        self.root.withdraw()

    def toggle(self, event=None):
        if self.root.state() == "normal":
            self.close()
        else:
            self.show()

    def search(self, *_):
        min_ch = self.curState.chapter
        if self.optSearchAll.get():
            for ch in range(min_ch, len(self.master.fileMan.files)):
                self.master.fileMan.loadFile(ch)
                if self._search_text_blocks(ch):
                    return
        else:
            self._search_text_blocks(self.master.nav.cur_chapter)

    def _search_text_blocks(self, chapter: int):
        start_block = self.curState.block
        s_field, s_re = (x.get() for x in self.filter)

        # print(f"searching in {self.master.nav.cur_file.name} ({chapter}), "
        #       f"from {vars(self.cur_state)}, on {s_field} = {s_re}")
        file = self.master.fileMan.files[chapter]
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
                self.curState.setPos(chapter, i + 1)
                self.master.nav.change_chapter(chapter)
                self.master.nav.change_block(i)
                return True
        self.curState.setPos(chapter + 1, 0)
        return False

    def reset_search(self, event=None, *args):
        # event = the Var itself
        self.curState.setPos(0, 0)

    def restoreState(self):
        self.master.nav.change_chapter(self.savedState.chapter)
        self.master.nav.change_block(self.savedState.block)


class PreviewWindow:
    def __init__(self, master: Editor) -> None:
        root = tk.Toplevel()
        root.title("Preview")
        root.resizable(True, True)
        root.attributes("-alpha", 0.7, "-topmost", True)
        # previewWindow.overrideredirect(True)
        root.protocol("WM_DELETE_WINDOW", root.withdraw)
        root.bind("<Control-p>", self.toggle)
        # root.bind('<B1-Motion>',moveWindow)

        fontSize = tk.IntVar(value=16)  # common UI size
        fontSize.trace("w", self._evChangeFontSize)
        fontSizeCfg = ttk.Spinbox(root, from_=2, to=75, increment=1, textvariable=fontSize)
        fontSizeCfg.pack(expand=False, fill="x")
        previewFont = fonts.create(root, id="preview", size=fontSize.get())
        previewText = text.TextBox(root, font=previewFont)
        previewText.pack(expand=True, fill="both")

        self.master = master
        self.root = root
        self.text = previewText
        self.fontSize = fontSize
        root.withdraw()

    def setText(self, text: str):
        self.text.loadRichText(text)

    def moveWindow(self, event):
        raise NotImplementedError
        self.root.geometry(f"+{event.x_root}+{event.y_root}")

    def _evChangeFontSize(self, *_args):  # Name, ???, action
        # Excepts on del or first number because it triggers on emptied input first
        try:
            newsize = self.fontSize.get()
        except tk.TclError:
            return
        self.text.fontConfig(size=newsize)

    def toggle(self, event=None):
        if self.root.state() == "normal":
            self.root.withdraw()
        else:
            self.root.deiconify()


class MergeWindow:
    def __init__(self, master: Editor) -> None:
        root = tk.Toplevel()
        root.title("Merge")
        root.resizable(True, True)
        root.protocol("WM_DELETE_WINDOW", root.withdraw)
        self.master = master
        self.root = root
        self.nav = master.nav
        master.merging = True

        selectionFrame = tk.Frame(root)
        viewFrame = tk.Frame(root)
        fileNum = tk.IntVar(value=1)
        fileNumPicker = ttk.Spinbox(selectionFrame, from_=1, to=5, increment=1, width=8, textvariable=fileNum)
        fileNumPicker.grid(row=0, column=0)
        fileNum.trace("w", self.evFileNumChange)
        ttk.Separator(viewFrame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        textOrig = text.TextBox(viewFrame, size=(None,3))
        textOrig.pack(anchor="w")
        textOrig.loadRichText(master.nav.cur_data.get("enText"))
        selectionFrame.pack()
        viewFrame.pack()

        self.textOrig = textOrig
        self.fileNum = fileNum
        self.fileNumPicker = fileNumPicker
        self.filePickers: list[ttk.Combobox] = list()
        self.selectionFrame = selectionFrame
        self.viewFrame = viewFrame

    def setFiles(self, files:Path):
        if files.is_file():
            files = (files,)
        elif files.is_dir():
            files = files.glob("*.json")
        self.files = [TranslationFile(f) for f in files]
        self.fileNames = [f.name for f in self.files]
        firstPicker = self.createFilePicker()
        if len(self.files) == 1:
            firstPicker.current(0)
            display.setActive(self.fileNumPicker, False)
            self.changeFile(widget=firstPicker)

    def createFilePicker(self):
        filePicker = ttk.Combobox(self.selectionFrame, width=30)
        filePicker.id = len(self.filePickers)
        filePicker.view = self.createBlockView()
        filePicker.activeFile = None
        filePicker.config(values=self.fileNames)
        filePicker.bind("<<ComboboxSelected>>", self.changeFile)
        filePicker.bind("<Destroy>", lambda e: e.widget.view.destroy())
        filePicker.grid(row=0, column=len(self.filePickers) + 1)
        self.filePickers.append(filePicker)
        return filePicker

    def createBlockView(self):
        sep = ttk.Separator(self.viewFrame, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=20)
        textbox = text.TextBox(self.viewFrame, size=(None,3))
        textbox.pack(anchor="w")
        textbox.sep = sep
        textbox.bind("<Destroy>", lambda e: e.widget.sep.destroy())
        return textbox

    def changeFile(self, event=None, widget: ttk.Combobox = None):
        widget = widget or event.widget
        widget.activeFile = self.files[widget.current()]
        self.evBlockUpdated(self.master.nav.cur_data, self.master.nav.cur_block, widget=widget)

    def evBlockUpdated(self, data: dict, blockIdx: int, widget: ttk.Combobox = None):
        if widget is None:
            self.textOrig.loadRichText(data.get("enText"))
        pickers = (widget,) if widget else self.filePickers
        for picker in pickers:
            if not picker.activeFile:
                self.master.status.log(f"No active file for picker {picker.id}")
                continue
            try:
                picker.view.loadRichText(picker.activeFile.textBlocks[blockIdx].get("enText"))
            except IndexError:
                pass

    def evFileNumChange(self, *_):
        reqNumPickers = self.fileNum.get()
        curNumPickers = len(self.filePickers)
        if curNumPickers == reqNumPickers:
            return
        elif curNumPickers < reqNumPickers:
            while len(self.filePickers) < reqNumPickers:
                self.createFilePicker()
        elif curNumPickers > reqNumPickers:
            while len(self.filePickers) > reqNumPickers:
                p = self.filePickers.pop()
                p.destroy()

#todo: merge with SaveState
class Status:
    def __init__(self, editor: Editor) -> None:
        self.editor = editor
        self.widget = tk.Frame(editor.root)
        self.saveStatus = tk.Label(self.widget)
        self.statusLog = tk.Label(self.widget)

        self.fileSaved = None
        self._defaultBg = self.statusLog.cget("background")

        self.saveStatus.pack(side=tk.LEFT, padx=(0,5))
        self.statusLog.pack(side=tk.LEFT, fill=tk.X)

    def log(self, text:str):
        self.statusLog.config(text=text, bg="#34c6eb")
        self.statusLog.after(500, lambda: self.statusLog.config(bg=self._defaultBg))

    def setSaved(self):
        if self.fileSaved:
            return
        self.saveStatus.config(text="Saved", fg="#008a29")
        self.fileSaved = True

    def setUnsaved(self):
        if not self.fileSaved:
            return
        self.saveStatus.config(text="Unsaved", fg="#8a0000")
        self.fileSaved = False

    def onFileChanged(self, chapter):
        if chapter in self.editor.fileMan.saveState.unsavedChanges:
            self.setUnsaved()
        else:
            self.setSaved()


class SpeakerNotes:
    file = Path("src/data/speaker_notes.json")
    wrapLen = 35

    def __init__(self, editor: Editor) -> None:
        self.notes = utils.readJson(self.file)
        self.changed = False
        self.widget = display.SlidingTray(editor.root, "Speaker Notes", vertical=True)
        self.scrollFrame = display.ScrollableFrame(self.widget.tray, True)
        self.textBox = text.TextBoxEditable(
            self.scrollFrame.content,
            size=(self.wrapLen, 50),
            font=fonts.UI_JP,
            wrap=tk.WORD,
        )
        self.textBox.pack(fill=tk.BOTH)
        self.scrollFrame.pack(fill=tk.BOTH, expand=1)

    def _parseSpeaker(self, block):
        return block.get("jpName", "default")

    def load(self, event):
        speaker = self._parseSpeaker(event.user_data)
        note = self.notes.get(speaker, "")
        self.textBox.loadRichText(note)
        self.textBox.edit_modified(False)

    def save(self, event):
        if not self.textBox.edit_modified():
            # print("not modified")
            return
        note = text.normalize(self.textBox.toRichText())
        speaker = self._parseSpeaker(event.user_data)
        if len(note) < 2:  # empty text
            self.notes.pop(speaker, None)
        else:
            self.notes[speaker] = note
        # print("Saved: ", note, "\n", "For: ", speaker)

    def onExit(self):
        utils.writeJson(self.file, self.notes)


class TextLog:
    MODE_JP = 0
    MODE_EN = 1
    MODE_MIX = 2
    TEXT_KEYS = ("jpText", "enText")
    NAME_KEY = ("jpName", "enName")
    TAG_KEYS = ("jp", "en")

    def __init__(self, master: Editor) -> None:
        self.master = master
        self.root = root = tk.Toplevel(master.root)
        root.title("Text Log")
        root.protocol("WM_DELETE_WINDOW", self.toggle)
        root.resizable(False, True)

        self.mode = TextLog.MODE_EN
        # self.lastLoad = (None, None)
        root.bind_all("<<BlockSaved>>", self.evhOnBlockChange)
        font = fonts.create(root, size=12, id="tlog")
        self.text_area = text.TextBoxEditable(root, size=(None, 25), font=font)

        scroll = tk.Scrollbar(root, command=self.text_area.yview)
        self.text_area.config(yscrollcommand=scroll.set)

        frm_btns = tk.Frame(root)
        buttons = (
            ("Undo", self.text_area.edit_undo),
            ("Redo", self.text_area.edit_redo),
            ("English", lambda: self.setMode(TextLog.MODE_EN)),
            ("Japanese", lambda: self.setMode(TextLog.MODE_JP)),
            ("Mixed", lambda: self.setMode(TextLog.MODE_MIX))
        )
        for txt, cmd in buttons:
            tk.Button(frm_btns, text=txt, command=cmd).pack(side=tk.LEFT, padx=5, pady=5)
        save_button = tk.Button(frm_btns, text="Save Changes", command=self.save_edits)
        save_button.pack(side=tk.RIGHT, padx=5, pady=5)

        frm_opts = tk.Frame(root)
        self.useUmaFont = tk.BooleanVar(frm_opts, name="umafont", value=True)
        self.useUmaFont.trace_add("write", self.swapFont)
        tk.Checkbutton(frm_opts, text="Uma font", variable=self.useUmaFont).pack(side=tk.LEFT, padx=3)
        self.fontSize = fontSize = tk.IntVar(frm_opts, value=13)
        fontSize.trace_add("write", self.changeFontSize)
        ttk.Spinbox(frm_opts, from_=2, to=75, increment=1, textvariable=fontSize).pack(side=tk.LEFT, padx=3)

        root.grid_rowconfigure(0, weight=1)
        self.text_area.grid(sticky=tk.NS)
        scroll.grid(row=0, column=1, sticky=tk.NS)
        frm_btns.grid(row=1, columnspan=2, sticky=tk.EW)
        frm_opts.grid(row=2, columnspan=2, sticky=tk.EW)

        self.text_area.tag_configure("en")
        self.text_area.tag_configure("jp")
        self.text_area.tag_configure("name", background="light grey")
        root.withdraw()

    def setMode(self, mode):
        self.mode = mode
        cur_idx = self.text_area.index(tk.INSERT)
        self.populate_texts()
        self.text_area.see(cur_idx)
        self.text_area.mark_set(tk.INSERT, cur_idx)
        # todo: scroll to same block idx

    def populate_texts(self):
        if not self.master.nav.cur_file:
            return False
        # if self.lastLoad == (self.mode, self.master.nav.cur_file):
        #     return True
        text.clearText(self.text_area)
        self.text_area.config(width=calcLineLen(self.master.nav.cur_file))

        if self.mode == TextLog.MODE_EN:
            self.text_area.toggleSpellCheck(True)
        else:
            self.text_area.toggleSpellCheck(False)

        if self.mode == TextLog.MODE_MIX:
            for block in self.master.nav.cur_file.textBlocks:
                jp_name = block.get(self.NAME_KEY[self.MODE_JP], "")
                en_name = block.get(self.NAME_KEY[self.MODE_EN], "")
                jp_Text = block.get(self.TEXT_KEYS[self.MODE_JP], "")
                en_Text = block.get(self.TEXT_KEYS[self.MODE_EN], "")
                text.setText(self.text_area,f"{jp_name} / {en_name}:", tag="name", append=True)
                self.text_area.loadRichText(f"\n{jp_Text}", tag="jp", append=True)
                self.text_area.loadRichText(f"\n\n{en_Text}\n\n", tag="en", append=True)
        else:
            for block in self.master.nav.cur_file.textBlocks:
                block_name = block.get(self.NAME_KEY[self.mode], "")
                block_text = block.get(self.TEXT_KEYS[self.mode], "")
                text.setText(self.text_area, f"{block_name}:", tag="name", append=True)
                self.text_area.loadRichText(f"\n{block_text}\n\n", tag=self.TAG_KEYS[self.mode], append=True)

        # self.lastLoad = (self.mode, self.master.nav.cur_file)
        return True

    def toggle(self, event=None):
        if self.root.state() == "normal":
            self.root.withdraw()
        else:
            if not self.populate_texts():
                self.master.status.log("No active file")
                return
            self.root.deiconify()

    def save_edits(self):
        if self.mode == TextLog.MODE_JP:
            return
        ranges = self.text_area.tag_ranges("en")
        blockEquiv = len(ranges)//2

        textBLocks = self.master.nav.cur_file.textBlocks
        if blockEquiv != len(textBLocks):
            messagebox.showerror(message="Text log is corrupted, aborting save.")
            print(f"mode: {self.mode}, edit blocks: {blockEquiv}, file blocks: {len(textBLocks)}\n")
            print(ranges)
            return

        for i, (start, end) in enumerate(text.TextBox.deinterleaveTagRange(ranges)):
            block_text = text.normalize(self.text_area.toRichText(start, end))
            if textBLocks[i]["enText"] == block_text:
                continue
            textBLocks[i]["enText"] = block_text
            self.master.status.setUnsaved()
            self.master.fileMan.saveState.unsavedChanges.add(self.master.nav.cur_chapter)
            # Directly update the main UI English text box if it's the currently displayed block
            if i == self.master.nav.cur_block:
                self.master.textBoxEn.loadRichText(block_text)
        self.text_area.edit_reset()

    def swapFont(self, *_):
        if self.useUmaFont.get():
            self.text_area.fontConfig(family=fonts.UMATL_FONT_NAME)
        else:
            self.text_area.fontConfig(family=fonts.getDefaultFontName())

    def changeFontSize(self, *_):
        try:
            newsize = self.fontSize.get()
        except tk.TclError:
            return
        self.text_area.fontConfig(size=newsize)

    def evhOnBlockChange(self, event):
        if self.root.winfo_ismapped() and self.master.textBoxEn.edit_modified():
            self.populate_texts()
