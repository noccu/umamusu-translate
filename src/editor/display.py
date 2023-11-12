import tkinter as tk
from tkinter import ttk
from . import fonts


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


class ScrollableFrame(tk.Frame):
    def __init__(self, parent: tk.Toplevel, scrollbar=False):
        super().__init__(parent)
        scroll_canvas = tk.Canvas(self, highlightthickness=0)
        scroll_canvas.pack(side="left", fill="both")

        if scrollbar:
            scroll_bar = ttk.Scrollbar(self, orient="vertical", command=scroll_canvas.yview)
            scroll_bar.pack(side="right", fill="y")
            scroll_canvas.configure(yscrollcommand=scroll_bar.set)

        content_frame = tk.Frame(scroll_canvas)
        scroll_canvas.create_window((0, 0), window=content_frame, anchor="nw")
        content_frame.bind(
            "<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"), width=content_frame.winfo_reqwidth())
        )
        content_frame.bind("<Enter>", self.enableScroll)
        content_frame.bind("<Leave>", self.disableScroll)
        content_frame.bind("<MouseWheel>", self.scroll)
        content_frame.bind("<Map>", self._ev_mapped)

        self.isScrollable = False
        self.canvas = scroll_canvas
        self.content = content_frame

    # Allow scrolling widget on any child
    #? Could also implement optional scroll event overwriting in scrollable children
    def _ev_mapped(self, e:tk.Event):
        self._bind_children(e.widget)

    def _bind_children(self, widget):
        for child in widget.winfo_children():
            child.bind("<MouseWheel>", self.scroll)
            self._bind_children(child)  # recurse

    def enableScroll(self, e):
        self.isScrollable = True

    def disableScroll(self, e):
        self.isScrollable = False

    def scroll(self, e):
        if self.isScrollable:
            self.canvas.yview_scroll(-1 * int(e.delta / 35), "units")


class SlidingTray(tk.Frame):
    def __init__(self, parent, text, vertical=False):
        super().__init__(parent)
        labelText = f"⇕ {text} ⇕"
        font = fonts.createFrom(self, None, id="tray")
        w = font.measure(labelText)
        h = font.metrics("linespace")
        activator = tk.Canvas(
            self, 
            width=h if vertical else w, 
            height=w if vertical else h
        )
        tray = tk.LabelFrame(self, text=text)
        textObj = activator.create_text(
            0,0, 
            anchor=tk.CENTER, 
            justify=tk.CENTER, 
            text=labelText, 
            angle=270 if vertical else 0
        )
        activator.bind("<ButtonPress-1>", self.toggle)
        activator.bind(
            "<Configure>", 
            lambda e: activator.coords(
                textObj, 
                activator.winfo_width()/2, 
                activator.winfo_height()/2
            )
        )
        activator.pack(side=tk.LEFT, fill=tk.Y, expand=1)
        self.tray = tray

    def toggle(self, ev=None):
        if self.tray.winfo_ismapped():
            self.retractTray()
        else:
            self.expandTray()

    def expandTray(self):
        self.tray.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
    def retractTray(self):
        self.tray.pack_forget()


def _switchWidgetFocusForced(e):
    e.widget.tk_focusNext().focus()
    return "break"


def setActive(widget: tk.Widget, active: bool):
    widget["state"] = "normal" if active else "disabled"
