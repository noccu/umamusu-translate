import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

from common import constants as const

if const.IS_WIN:
    from ctypes import byref, create_string_buffer, create_unicode_buffer, windll


class FontManager:
    fontLoaded = False

    def __init__(self, master) -> None:
        if not FontManager.fontLoaded:
            self.loadFont(r"src/data/RodinWanpakuPro-UmaTl.otf")
        FontManager.fontLoaded = True

        # Todo: consider adding general functions and defining these externally through them
        self.FONT_LARGE = FONT_LARGE = Font(
            master.root, family="RodinWanpakuPro UmaTl B", size=18, weight="normal"
        )
        self.FONT_BOLD = FONT_LARGE.copy()
        self.FONT_BOLD.config(weight="bold")
        self.FONT_ITALIC = FONT_LARGE.copy()
        self.FONT_ITALIC.config(slant="italic")

    def loadFont(self, fontPath):
        # code modified from https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
        if not const.IS_WIN:
            print(
                "Non-Windows system: Fonts, lengths, and previews won't match game.\n"
                "To load custom game font install 'src/data/RodinWanpakuPro-B-ex.otf' to system fonts."
            )
            return
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


class ScrollableFrame:
    def __init__(self, parent: tk.Toplevel):
        scroll_frame = ttk.Frame(parent)
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

        scroll_canvas.bind_all("<MouseWheel>", self.scroll)
        window_frame.bind("<Enter>", self.toggle)
        window_frame.bind("<Leave>", self.toggle)

        self.canvas = scroll_canvas
        self.isScrollable = False
        self.content = window_frame

    def toggle(self, e):
        self.isScrollable = not self.isScrollable

    def scroll(self, e):
        if self.isScrollable:
            self.canvas.yview_scroll(-1 * int(e.delta / 35), "units")


def _switchWidgetFocusForced(e):
    e.widget.tk_focusNext().focus()
    return "break"


def setActive(widget: tk.Widget, active: bool):
    widget["state"] = "normal" if active else "disabled"


def setText(widget: tk.Widget, text: str):
    widget["text"] = text
