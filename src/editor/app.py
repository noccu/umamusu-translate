import re
import tkinter as tk
from tkinter import messagebox, ttk
from types import SimpleNamespace

from common import constants as const
from common.constants import NAMES_BLACKLIST

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

        speaker_jp_label = tk.Label(root, text="Speaker (JP)")
        speaker_jp_label.grid(row=1, column=0)
        speaker_jp_entry = tk.Entry(root, state="readonly")
        speaker_jp_entry.grid(row=1, column=1, sticky=tk.NSEW)
        self.speakerJp = speaker_jp_entry

        speaker_en_label = tk.Label(root, text="Speaker (EN)")
        speaker_en_label.grid(row=1, column=2)
        speaker_en_entry = tk.Entry(root)
        speaker_en_entry.grid(row=1, column=3, sticky=tk.NSEW)
        self.speakerEn = speaker_en_entry

        block_duration_label = tk.Label(root, text="Text Duration")
        block_duration_label.grid(row=2, column=2)
        block_duration_spinbox = ttk.Spinbox(root, from_=0, to=9999, increment=1, width=5)
        block_duration_spinbox.grid(row=2, column=3, sticky=tk.W)
        self.blockDuration = block_duration_spinbox
        self.blockDurationLabel = block_duration_label

        self.textBoxJp = text.TextBox(root, size=(None,5))
        self.textBoxJp.grid(row=3, column=0, columnspan=4)

        self.textBoxEn = text_box_en = text.TextBoxEditable(root, size=(None, 6))
        text_box_en.grid(row=4, column=0, columnspan=4)
        text_box_en.linkTo(self.textBoxJp, root)

        frm_btns_bot = tk.Frame(root)
        btn_choices = tk.Button(
            frm_btns_bot,
            text="Choices",
            command=lambda: self.extraText.toggle(target=self.extraText.cur_choices),
            state="disabled",
            width=10,
        )
        btn_choices.grid(row=0, column=0)
        btn_colored = tk.Button(
            frm_btns_bot,
            text="Colored",
            command=lambda: self.extraText.toggle(target=self.extraText.cur_colored),
            state="disabled",
            width=10,
        )
        btn_colored.grid(row=1, column=0)
        btn_listen = tk.Button(
            frm_btns_bot, text="Listen", command=self.audio.listen, width=10
        )
        btn_listen.grid(row=0, column=1)
        btn_search = tk.Button(frm_btns_bot, text="Search", command=self.search.toggle, width=10)
        btn_search.grid(row=1, column=1)
        btn_reload = tk.Button(
            frm_btns_bot, text="Reload", command=self.nav.reload_chapter, width=10
        )
        btn_reload.grid(row=0, column=2)
        btn_save = tk.Button(frm_btns_bot, text="Save", command=self.saveFile, width=10)
        btn_save.grid(row=1, column=2)
        btn_prev = tk.Button(frm_btns_bot, text="Prev", command=self.nav.prev_block, width=10)
        btn_prev.grid(row=0, column=3)
        btn_next = tk.Button(frm_btns_bot, text="Next", command=self.nav.next_block, width=10)
        btn_next.grid(row=1, column=3)
        frm_btns_bot.grid(row=5, columnspan=4, sticky=tk.NSEW)
        for idx in range(frm_btns_bot.grid_size()[0]):
            frm_btns_bot.columnconfigure(idx, weight=1)
        # Todo: move to nav class?
        self.nav.btnNext = btn_next
        self.nav.btnPrev = btn_prev
        self.btnChoices = btn_choices
        self.btnColored = btn_colored

        # Todo: split off?
        frm_btns_side = tk.Frame(root)
        side_buttons = (
            tk.Button(
                frm_btns_side,
                text="Italic",
                command=lambda: text_box_en.format_text(SimpleNamespace(keysym="i")),
            ),
            tk.Button(
                frm_btns_side,
                text="Bold",
                command=lambda: text_box_en.format_text(SimpleNamespace(keysym="b")),
            ),
            tk.Button(
                frm_btns_side, text="Convert\nunicode codepoint", command=text_box_en.char_convert
            ),
            tk.Button(
                frm_btns_side,
                text="Process text",
                command=self._evProcessText,
            ),
            tk.Button(
                frm_btns_side,
                text="Process text\n(clean newlines)",
                command=lambda: self._evProcessText(redoNewlines=True),
            ),
            tk.Button(
                frm_btns_side,
                text="Process text\n(whole chapter)",
                command=lambda: self._evProcessText(wholeFile=True),
            ),
            tk.Button(frm_btns_side, text="Translate speakers", command=self.tlNames),
            tk.Button(
                frm_btns_side, text="Find missing speakers", command=self.nav.nextMissingName
            ),
        )
        for btn in side_buttons:
            btn.pack(pady=3, fill=tk.X)
        frm_btns_side.grid(column=5, row=0, rowspan=5, sticky=tk.NE)

        ## Options
        # todo: move to a separate frame class
        save_checkbox = tk.Checkbutton(
            root, text="Save chapter on block change", variable=self.options.saveOnBlockChange
        )
        save_checkbox.grid(row=6, column=1)
        skip_checkbox = tk.Checkbutton(
            root, text="Skip translated blocks", variable=self.options.skip_translated
        )
        skip_checkbox.grid(row=6, column=0)
        set_humanTl_checkbox = tk.Checkbutton(
            root, text="Mark as human TL", variable=self.options.markHuman
        )
        set_humanTl_checkbox.grid(row=6, column=2)

        ## Focus management
        for f in (root, frm_btns_bot, frm_btns_side):
            for w in f.children.values():
                w.configure(takefocus=0)
        text_box_en.configure(takefocus=1)
        speaker_en_entry.configure(takefocus=1)
        text_box_en.bind("<Tab>", display._switchWidgetFocusForced)
        speaker_en_entry.bind("<Tab>", display._switchWidgetFocusForced)
        text_box_en.focus()

        # self.nav.change_chapter(initialLoad=True)

        ## Keybinds
        root.bind("<Control-Return>", self.nav.next_block)
        root.bind_all("<Control-s>", self.saveFile)
        root.bind("<Alt-Up>", self.nav.prev_block)
        root.bind("<Alt-Down>", self.nav.next_block)
        root.bind("<Control-Alt-Up>", self.nav.prev_ch)
        root.bind("<Control-Alt-Down>", self.nav.next_ch)
        root.bind("<Alt-c>", lambda _: self.extraText.toggle(target=self.extraText.cur_choices))
        root.bind(
            "<Control-Alt-c>", lambda _: self.extraText.toggle(target=self.extraText.cur_colored)
        )
        text_box_en.bind("<Alt-f>", self._evProcessText)
        text_box_en.bind("<Alt-F>", lambda e: self._evProcessText(e, redoNewlines=True))
        root.bind("<Control-f>", self.search.toggle)
        root.bind_all("<Control-h>", self.audio.listen)
        root.bind("<Control-p>", self.preview.toggle)

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
        root.geometry("580x450")  # 800 for full
        self.root = root

        # todo: can you call self funcs in a lambda? doesn't work in js iirc!
        root.bind("<Alt-c>", lambda _: self.toggle(target=self.cur_choices))
        root.bind("<Control-Alt-c>", lambda _: self.toggle(target=self.cur_colored))

        scrollFrame = display.ScrollableFrame(root)
        for i in range(0, 5):
            cur_jp_text = text.TextBox(scrollFrame.content, size=(42,2), takefocus=0)
            cur_jp_text.pack(anchor="w")
            cur_en_text = text.TextBoxEditable(scrollFrame.content, size=(42, 2))
            cur_en_text.linkTo(cur_jp_text, master.root)
            cur_en_text.pack(anchor="w")
            self.textBoxes.append((cur_jp_text, cur_en_text))
            cur_en_text.bind("<Tab>", display._switchWidgetFocusForced)
            if i == 0:
                self.firstText = cur_en_text
            if i < 4:
                ttk.Separator(scrollFrame.content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
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

        search_chapters = tk.IntVar()
        search_chapters.set(0)
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
        self.optSearchChapters = search_chapters
        self.searchBox = search_re
        # set it here so it exists when window closed without searching
        # todo: access these from master
        self.stateOnOpen = (
            self.master.nav.cur_block,
            self.master.nav.cur_chapter,
            self.master.options.saveOnBlockChange.get(),
            self.master.options.skip_translated.get(),
        )
        self.reset_search()  # sets cur state

        root.withdraw()

    def show(self):
        # todo: uhh...
        self.stateOnOpen = (
            self.master.nav.cur_block,
            self.master.nav.cur_chapter,
            self.master.options.saveOnBlockChange.get(),
            self.master.options.skip_translated.get(),
        )
        self.master.options.saveOnBlockChange.set(0)
        self.master.options.skip_translated.set(0)
        self.root.deiconify()
        self.searchBox.focus()

    def close(self):
        self.master.options.saveOnBlockChange.set(self.stateOnOpen[2])
        self.master.options.skip_translated.set(self.stateOnOpen[3])
        self.root.withdraw()

    def toggle(self, event=None):
        if self.root.state() == "normal":
            self.close()
        else:
            self.show()

    def search(self, *_):
        min_ch = self.search_cur_state[0]
        if self.optSearchChapters.get():
            for ch in range(min_ch, len(self.master.fileMan.files)):
                self.master.fileMan.loadFile(ch)
                if self._search_text_blocks(ch):
                    return
        else:
            self._search_text_blocks(self.master.nav.cur_chapter)

    def _search_text_blocks(self, chapter):
        start_block = self.search_cur_state[1]
        s_field, s_re = (x.get() for x in self.filter)

        # print(f"searching in {cur_file.name}, from {self.search_cur_state}, on {s_field} = {s_re}")
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
                if chapter != self.master.nav.cur_chapter:
                    self.master.nav.chapterPicker.current(chapter)
                    self.master.nav.change_chapter()
                self.master.nav.change_block(i)
                self.search_cur_state = self.master.nav.cur_chapter, i + 1
                return True
        self.search_cur_state = self.master.nav.cur_chapter + 1, 0
        return False

    def reset_search(self, event=None, *args):
        # event = the Var itself
        self.search_cur_state = 0, 0

    def restoreState(self):
        ch, b, *_ = self.stateOnOpen
        self.master.nav.chapterPicker.current(ch)
        self.master.nav.change_chapter()
        self.master.nav.change_block(b)


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
