from pathlib import Path
import re
import tkinter as tk
from tkinter import messagebox, ttk
from types import SimpleNamespace
from functools import partial

from common import constants as const
from common.constants import NAMES_BLACKLIST
from common.types import TranslationFile

from . import display, files, navigator, text, fonts
from .spellcheck import SpellCheck
from .audio import AudioPlayer


class Options:
    def __init__(self) -> None:
        self.markHuman = tk.BooleanVar()
        self.saveOnBlockChange = tk.BooleanVar()
        self.skip_translated = tk.BooleanVar()


class Editor:
    COLOR_WIN = "systemWindow" if const.IS_WIN else "white"
    COLOR_BTN = "SystemButtonFace" if const.IS_WIN else "gray"

    def __init__(self) -> None:
        root = tk.Tk()
        root.title("File Editor")
        root.resizable(False, False)
        self.root = root
        fonts.init(root)

        self.cur_chapter = 0
        self.cur_block = 0
        # Managers
        self.options = Options()
        self.fileMan = files.FileManager(self)
        self.nav = navigator.Navigator(self)
        self.audio = AudioPlayer(self)
        # Windows
        self.extraText = AdditionalTextWindow(self)
        self.search = SearchWindow(self)
        self.preview = PreviewWindow(self)
        self.merging = False

        # Speakers
        frm_speakers = tk.Frame(root)
        fnt_speakers = fonts.create(root, size=9)
        self.speakerJp = speaker_jp_entry = tk.Entry(frm_speakers, state="readonly", width=26, font=fnt_speakers)
        self.speakerEn = speaker_en_entry = tk.Entry(frm_speakers, width=26, font=fnt_speakers)
        tk.Label(frm_speakers, text="Speaker (JP)").grid()
        tk.Label(frm_speakers, text="Speaker (EN)").grid(row=1)
        speaker_jp_entry.grid(row=0, column=1)
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
        self.blockDurationLabel = block_duration_label = tk.Label(frm_meta, text="Text Duration")
        self.blockDuration = block_duration_spinbox = ttk.Spinbox(frm_meta, from_=0, to=1000, increment=1, width=5)
        block_duration_label.pack(side=tk.LEFT)
        block_duration_spinbox.pack(side=tk.LEFT)

        # Bottom bar
        frm_btns_bot = tk.Frame(root)
        self.btnColored = btn_colored = tk.Button(
            frm_btns_bot,
            text="Colored",
            command=lambda: self.extraText.toggle(target=self.extraText.cur_colored),
            state="disabled",
            width=10,
        )
        btn_listen = tk.Button(
            frm_btns_bot, text="Listen", command=self.audio.listen, width=10
        )
        btn_search = tk.Button(frm_btns_bot, text="Search", command=self.search.toggle, width=10)
        btn_reload = tk.Button(
            frm_btns_bot, text="Reload", command=self.nav.reload_chapter, width=10
        )
        btn_save = tk.Button(frm_btns_bot, text="Save", command=self.saveFile, width=10)
        # Todo: move prev/next to nav class
        self.nav.btnPrev = btn_prev = tk.Button(frm_btns_bot, text="Prev", command=self.nav.prev_block, width=10)
        self.nav.btnNext = btn_next = tk.Button(frm_btns_bot, text="Next", command=self.nav.next_block, width=10)
        btn_reload.grid(row=0, column=2)
        btn_save.grid(row=1, column=2)
        btn_prev.grid(row=0, column=3)
        btn_next.grid(row=1, column=3)
        btn_colored.grid(row=1, column=0)
        btn_listen.grid(row=0, column=1)
        btn_search.grid(row=1, column=1)
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
        )
        f_options = tk.Frame(root)
        for txt, var in opts:
            tk.Checkbutton(f_options, text=txt, variable=var).pack(side=tk.LEFT, ipadx=3)

        # Build UI
        self.nav.frm_blocks.grid(row=0, column=0, sticky=tk.NSEW, pady=5)
        frm_speakers.grid(row=0, column=1, sticky=tk.NSEW, pady=5)
        frm_text_edit.grid(row=1, columnspan=2, sticky=tk.NSEW)
        self.choices.widget.grid_configure(row=1, column=2, sticky=tk.NSEW)
        frm_editing_actions.grid(row=3, column=0, sticky=tk.W, pady=5)
        frm_meta.grid(row=3, column=1, sticky=tk.W)
        frm_btns_bot.grid(row=4, columnspan=2, sticky=tk.NSEW)
        f_options.grid(row=5, columnspan=2, sticky=tk.EW)

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
        self.root.quit()

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
            print("This choice is not active!")
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
        fontSizeCfg.pack(expand=True, fill="x")
        previewFont = fonts.create(root, id="preview", size=fontSize.get())
        previewText = tk.Label(root, font=previewFont, justify="left", anchor="w")
        previewText.pack(expand=True, fill="both")

        self.master = master
        self.root = root
        self.text = previewText
        self.font = previewFont
        self.fontSize = fontSize
        root.withdraw()

    def setText(self, text: str):
        self.text.config(text=text)

    def moveWindow(self, event):
        raise NotImplementedError
        self.root.geometry(f"+{event.x_root}+{event.y_root}")

    def _evChangeFontSize(self, *_args):  # Name, ???, action
        # Excepts on del or first number because it triggers on emptied input first
        try:
            newsize = self.fontSize.get()
        except tk.TclError:
            return
        self.font.config(size=newsize)

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
                print(f"No active file for picker {picker.id}")
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
