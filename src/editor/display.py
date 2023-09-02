import tkinter as tk
from tkinter import ttk


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
