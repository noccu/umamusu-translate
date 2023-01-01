from argparse import SUPPRESS
import re
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
from types import SimpleNamespace

import common
from helpers import isEnglish
import textprocess

if common.IS_WIN:
    from ctypes import windll, byref, create_unicode_buffer, create_string_buffer

TEXTBOX_WIDTH = 54
COLOR_WIN = "systemWindow" if common.IS_WIN else "white"
COLOR_BTN = "SystemButtonFace" if common.IS_WIN else "gray"
AUDIO_PLAYER = None

class AudioPlayer:
    curPlaying = (None, 0)
    subkey = None
    audioOut = None
    wavData = None
    subFiles = None
    def __init__(self) -> None:
        global pyaudio, sqlite3, wave, restore, AWB, HCA
        import pyaudio, sqlite3, wave, restore
        from PyCriCodecs import AWB, HCA
        self.pyaud = pyaudio.PyAudio()
        self._db = sqlite3.connect(common.GAME_META_FILE)
        self._restoreArgs = restore.parseArgs([])
    def dealloc(self):
        self._db.close()
        if isinstance(self.audioOut, pyaudio.Stream):
            self.audioOut.close()
        self.pyaud.terminate()
    def play(self, storyId, idx, sType="story"):
        if idx < 0:
            print("Text block is not voiced.")
            return
        if reloaded := self.curPlaying[0] != storyId:
            if sType == "home":
                stmt = f"SELECT h FROM a WHERE n LIKE 'sound%{storyId[:2]}\_{storyId[2:]}.awb' ESCAPE '\\'"
            else:
                stmt = f"SELECT h FROM a WHERE n LIKE 'sound%{storyId}.awb'"
            h = self._db.execute(stmt).fetchone()
            if h is None:
                print("Couldn't find audio asset.")
                return
            asset = common.GameBundle.fromName(h[0], load=False)
            asset.bundleType = "sound"
            if not asset.exists:
                restore.save(asset, self._restoreArgs)
            self.load(str(asset.bundlePath))
        if reloaded or self.curPlaying[1] != idx:
            if idx > len(self.subFiles):
                print("Index out of range")
                return
            self.decodeAudio(self.subFiles[idx])
        self.curPlaying = (storyId, idx)
        self.audioOut.write(self.wavData)
    def load(self, path: str):
        awbFile = AWB(path)
        # get by idx method seems to corrupt half the files??
        self.subFiles = [f for f in awbFile.getfiles()]
        self.subkey = awbFile.subkey
        awbFile.stream.close()
    def decodeAudio(self, hcaFile:bytes):
        hcaFile:HCA = HCA(hcaFile, key=75923756697503, subkey=self.subkey)
        channels = hcaFile.hca.get("ChannelCount")
        rate = hcaFile.hca.get("SampleRate")
        hcaFile.decode() # leaves a wav ByteIOStream in stream attr
        with wave.open(hcaFile.stream, "rb") as wavFile:
            bpc = wavFile.getsampwidth()
            # read the whole file because it's small anyway
            self.wavData = wavFile.readframes(wavFile.getnframes())
        hcaFile.stream.close() # probably not needed (lib sure doesn't) but eh
        self._createStream(bpc, channels, rate) # ready the stream to play this data
    def _createStream(self, bpc = 2, channels = 1, rate = 48000):
        if isinstance(self.audioOut, pyaudio.Stream):
            if self.audioOut._channels != channels or self.audioOut._rate != rate:
                self.audioOut.close()
            else:
                return
        self.audioOut = self.pyaud.open(
            format=self.pyaud.get_format_from_width(width=bpc),
            channels = channels,
            rate = rate,
            output=True
        )

def change_chapter(event=None, initialLoad=False):
    global cur_chapter
    global cur_block
    global cur_file

    if not initialLoad: save_block()
    cur_chapter = chapter_dropdown.current()
    cur_block = 0

    loadFile()
    cur_file = files[cur_chapter]

    block_dropdown['values'] = [f"{i+1} - {block['jpText'][:16]}" for i, block in enumerate(cur_file.textBlocks)]
    ll = textprocess.calcLineLen(cur_file, False)
    # Attempt to calc the relation of line length to text box size
    # ll = int(ll / (0.958 * ll**0.057) + 1) if ll else TEXTBOX_WIDTH # default font
    # ll = int(ll / (1.067 * ll**0.057) + 1) if ll else TEXTBOX_WIDTH # game font attempt 1
    ll = int(ll / (1.135 * ll**0.05) + 1) if ll else TEXTBOX_WIDTH

    text_box_en.config(width=ll)
    text_box_jp.config(width=ll)

    load_block()


def reload_chapter(event=None):
    cur_file.reload()
    load_block()


def prev_ch(event=None):
    if cur_chapter - 1 > -1:
        chapter_dropdown.current(cur_chapter - 1)
        change_chapter()
    else: print("Reached first chapter")


def next_ch(event=None):
    if cur_chapter + 1 < len(files):
        chapter_dropdown.current(cur_chapter + 1)
        change_chapter()
    else: print("Reached last chapter")


def change_block(event=None, dir=1):
    global cur_block

    save_block()
    if save_on_next.get() == 1:
        saveFile()

    cur_block = block_dropdown.current()
    load_block(dir=dir)


def load_block(event=None, dir=1):
    global cur_block
    global next_index
    global cur_choices
    global cur_colored

    blocks = cur_file.textBlocks
    cur_block_data =  blocks[cur_block]

    if skip_translated.get() == 1:
        while 0 < cur_block < len(blocks) - 1 and (cur_block_data['enText'] or isEnglish(cur_block_data['jpText'])):
            cur_block += dir
            cur_block_data = blocks[cur_block]
        block_dropdown.current(cur_block)

    next_index = cur_block_data.get('nextBlock', cur_block + 2) - 1
    if next_index < 1 or next_index >= len(blocks):
        next_index = -1
    if next_index > 0:
        btn_next['state'] = 'normal'
        btn_next['text'] = f"Next ({next_index + 1})"
    else:
        btn_next['state'] = 'disabled'
        btn_next['text'] = "Next"

    # Fill in the text boxes
    speaker_jp_entry.delete(0, tk.END)
    speaker_jp_entry.insert(0, cur_block_data.get('jpName', ""))
    if cur_block_data.get('jpName') in common.NAMES_BLACKLIST:
        speaker_en_entry.delete(0, tk.END)
        speaker_en_entry['state'] = 'disabled'
    else:
        speaker_en_entry['state'] = 'normal'
        speaker_en_entry.delete(0, tk.END)
        en_name = cur_block_data.get('enName', "")
        if en_name:
            speaker_en_entry.insert(0, en_name)
            speaker_en_entry.config(bg=COLOR_WIN)
        else:
            speaker_en_entry.config(bg='red')

    # Spinbox for text block duration
    block_duration_spinbox.delete(0, tk.END)
    if "origClipLength" in cur_block_data:
        block_duration_label.config(text=f"Text Duration ({cur_block_data['origClipLength']})")
    if "newClipLength" in cur_block_data:
        block_duration_spinbox.insert(0, cur_block_data['newClipLength'])
    else:
        if "origClipLength" in cur_block_data:
            block_duration_spinbox.insert(0, cur_block_data['origClipLength'])
        else:
            block_duration_spinbox.insert(0, "-1")

    text_box_jp.configure(state='normal')
    text_box_jp.delete(1.0, tk.END)
    text_box_jp.insert(tk.END, txt_for_display(cur_block_data['jpText']))
    text_box_jp.configure(state='disabled')
    text_box_en.delete(1.0, tk.END)
    text_box_en.insert(tk.END, txt_for_display(cur_block_data['enText']))

    # Update choices button
    cur_choices = cur_block_data.get('choices')
    if cur_choices:
        btn_choices['state'] = 'normal'
        btn_choices.config(bg='#00ff00')
        toggleTextListPopup(allowShow=False, target=cur_choices)
    else:
        btn_choices['state'] = 'disabled'
        btn_choices.config(bg=COLOR_BTN)
        
    # Update colored button
    cur_colored = cur_block_data.get('coloredText')
    if cur_colored:
        btn_colored['state'] = 'normal'
        btn_colored.config(bg='#00ff00')
        toggleTextListPopup(allowShow=False, target=cur_colored)
    else:
        btn_colored['state'] = 'disabled'
        btn_colored.config(bg=COLOR_BTN)
        

def save_block():
    if "enName" in cur_file.textBlocks[cur_block]:
        cur_file.textBlocks[cur_block]['enName'] = cleanText(speaker_en_entry.get())
    cur_file.textBlocks[cur_block]['enText'] = txt_for_display(text_box_en.get(1.0, tk.END), reverse=True)

    # Get the new clip length from spinbox
    new_clip_length = block_duration_spinbox.get()
    if new_clip_length.isnumeric():
        new_clip_length = int(new_clip_length)
        if "origClipLength" in cur_file.textBlocks[cur_block] and new_clip_length != cur_file.textBlocks[cur_block]['origClipLength']:
            cur_file.textBlocks[cur_block]['newClipLength'] = new_clip_length
        else:
            cur_file.textBlocks[cur_block].pop('newClipLength', None)
            if not "origClipLength" in cur_file.textBlocks[cur_block]:
                messagebox.showwarning(master=block_duration_spinbox, title="Cannot save clip length",
                                       message="This text block does not have an original clip length defined and thus cannot save a custom clip length. Resetting to -1.")
                block_duration_spinbox.delete(0, tk.END)
                block_duration_spinbox.insert(0, "-1")
    elif new_clip_length != "-1":
        cur_file.textBlocks[cur_block].pop('newClipLength', None)


def prev_block(event=None):
    if cur_block - 1 > -1:
        block_dropdown.current(cur_block - 1)
        change_block(dir=-1)


def next_block(event=None):
    if next_index != -1:
        block_dropdown.current(next_index)
        change_block()
    else: print("Reached end of chapter")


def copy_block(event=None):
    root.clipboard_clear()
    root.clipboard_append(cur_file.textBlocks[cur_block]['jpText'])

def loadFile(chapter=None):
    ch = chapter or cur_chapter
    if isinstance(files[ch], str):
        files[ch] = common.TranslationFile(files[ch])

def saveFile(event=None):
    if save_on_next.get() == 0:
        print("Saved")
    save_block()
    cur_file.save()


def show_text_list():
    global cur_text_list

    if cur_text_list:
        cur_text_list = cur_text_list
        for i, t in enumerate(extra_text_list_textboxes):
            if i < len(cur_text_list):
                jpBox, enBox = t
                jpBox['state'] = 'normal' # enable insertion...
                enBox['state'] = 'normal'
                jpBox.insert(tk.END, cur_text_list[i]['jpText'])
                enBox.insert(tk.END, cur_text_list[i]['enText'])
                jpBox['state'] = 'disabled'
        text_list_window.deiconify()
        text_list_window.firstText.focus()


def close_text_list():
    for i, t in enumerate(extra_text_list_textboxes):
        jpBox, enBox = t
        if cur_text_list and i < len(cur_text_list):
            cur_text_list[i]['enText'] = cleanText(enBox.get(1.0, tk.END))  # choice don't really need special handling
        jpBox['state'] = 'normal'  # enable deletion...
        jpBox.delete(1.0, tk.END)
        enBox.delete(1.0, tk.END)
        jpBox['state'] = 'disabled'
        enBox['state'] = 'disabled'
    text_list_window.withdraw()


def create_text_list_popup():
    global extra_text_list_textboxes
    global text_list_window
    global cur_choices
    global cur_colored
    global cur_text_list
    global text_list_popup_scrollable

    extra_text_list_textboxes = list()
    text_list_popup_scrollable = False
    cur_choices = None
    cur_colored = None
    cur_text_list = None

    text_list_window = tk.Toplevel()
    text_list_window.protocol("WM_DELETE_WINDOW", close_text_list)
    text_list_window.title("Additional Text Lists")
    text_list_window.geometry("580x450")  # 800 for full

    scroll_frame = ttk.Frame(text_list_window)
    scroll_frame.pack(fill='both', expand=True)

    scroll_canvas = tk.Canvas(scroll_frame)
    scroll_canvas.pack(side='left', fill='both', expand=True)

    scroll_bar = ttk.Scrollbar(scroll_frame, orient='vertical', command=scroll_canvas.yview)
    scroll_bar.pack(side='right', fill='y')

    scroll_canvas.configure(yscrollcommand=scroll_bar.set)
    scroll_canvas.bind('<Configure>', lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox('all')))

    window_frame = ttk.Frame(scroll_canvas)
    scroll_canvas.create_window((0, 0), window=window_frame, anchor='nw')

    def toggle_scroll(e):
        global text_list_popup_scrollable
        text_list_popup_scrollable = not text_list_popup_scrollable

    def scroll(e):
        if text_list_popup_scrollable:
            scroll_canvas.yview_scroll(-1 * int(e.delta / 35), "units")

    scroll_canvas.bind_all("<MouseWheel>", scroll)
    window_frame.bind('<Enter>', toggle_scroll)
    window_frame.bind('<Leave>', toggle_scroll)

    for i in range(0, 5):
        cur_jp_text = tk.Text(window_frame, takefocus=0, width=42, height=2, font=large_font)
        cur_jp_text.pack(anchor="w")
        cur_en_text = tk.Text(window_frame, height=2, width=42, undo=True, font=large_font)
        cur_en_text.pack(anchor="w")
        extra_text_list_textboxes.append((cur_jp_text, cur_en_text))
        cur_en_text.bind('<Tab>', _switchWidgetFocusForced)
        if i == 0:
            text_list_window.firstText = cur_en_text
        if i < 4:
            ttk.Separator(window_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
    close_text_list()


def toggleTextListPopup(event=None, allowShow=True, target=None):
    global cur_text_list
    if text_list_window.state() == "normal":
        close_text_list()
        # Actually open other type if old window closed by opening another type, 
        if target is not cur_text_list: toggleTextListPopup(allowShow=allowShow, target=target)
    elif allowShow: 
        cur_text_list = target
        show_text_list()


def create_search_popup():
    global search_window
    global search_filter
    global search_chapters
    global search_orig_state

    # set it here so it exists when window closed without searching
    search_orig_state = cur_block, cur_chapter, save_on_next.get(), skip_translated.get()
    reset_search() # sets cur state

    search_window = tk.Toplevel()
    search_window.title("Search")
    search_window.protocol("WM_DELETE_WINDOW", close_search)
    search_window.bind("<Control-f>", toggleSearchPopup)

    s_var_field = tk.StringVar(search_window, value="enText")
    s_var_re = tk.StringVar(search_window)
    lb_field = tk.Label(search_window, text="Field:")
    lb_re = tk.Label(search_window, text="Search (supports regex):")
    search_field = tk.Entry(search_window, width=20, font=large_font, textvariable=s_var_field)
    search_re = tk.Entry(search_window, name="filter", width=40, font=large_font, textvariable=s_var_re)
    lb_field.grid(column=0, sticky=tk.E)
    lb_re.grid(column=0, sticky=tk.E)
    search_field.grid(row=0, column=1, columnspan=2, sticky=tk.W)
    search_re.grid(row=1, column=1, columnspan=2, sticky=tk.W)
    search_re.bind("<Return>", search_text)

    search_chapters = tk.IntVar()
    search_chapters.set(0)
    chk_search_chapters = tk.Checkbutton(search_window, text="Search all loaded chapters", variable=search_chapters)
    chk_search_chapters.grid(column=2, pady=5, sticky=tk.E)

    btn_search = tk.Button(search_window, text="Search / Next", name="search",command=search_text)
    btn_return = tk.Button(search_window, text="Return to original block", command=restore_search_state, padx=5)
    btn_return.grid(row=2, column=0, padx=5)
    btn_search.grid(row=2, column=1)

    search_filter = s_var_field, s_var_re
    for v in (s_var_field, s_var_re, search_chapters):
        v.trace_add("write", reset_search)
    search_window.withdraw()


def search_text(*_):
    min_ch = search_cur_state[0]
    if search_chapters.get():
        for ch in range(min_ch, len(files)):
            loadFile(ch)
            if _search_text_blocks(ch):
                return
    else:
        _search_text_blocks(cur_chapter)


def _search_text_blocks(chapter):
    global search_cur_state

    start_block = search_cur_state[1]
    s_field, s_re = (x.get() for x in search_filter)

    # print(f"searching in {cur_file.name}, from {search_cur_state}, on {s_field} = {s_re}")
    file = files[chapter]
    for i in range(start_block, len(file.textBlocks)):
        block = file.textBlocks[i]
        if re.search(s_re, block.get(s_field, ""), flags=re.IGNORECASE):
            # print(f"Found {s_re} at ch{chapter}:b{i}")
            if chapter != cur_chapter:
                chapter_dropdown.current(chapter)
                change_chapter()
            block_dropdown.current(i)
            change_block()
            search_cur_state = cur_chapter, i + 1
            return True
    search_cur_state = cur_chapter + 1, 0
    return False


def reset_search(event=None, *args):
    # event = the Var itself
    global search_cur_state
    search_cur_state = 0, 0


def restore_search_state():
    ch, b, *_ = search_orig_state
    chapter_dropdown.current(ch)
    change_chapter()
    block_dropdown.current(b)
    change_block()


def show_search():
    global search_orig_state
    search_orig_state = cur_chapter, cur_block, save_on_next.get(), skip_translated.get()
    save_on_next.set(0)
    skip_translated.set(0)
    search_window.deiconify()
    search_window.nametowidget("filter").focus()

    
def close_search():
    save_on_next.set(search_orig_state[2])
    skip_translated.set(search_orig_state[3])
    search_window.withdraw()


def toggleSearchPopup(event=None):
    global cur_text_list
    if search_window.state() == "normal":
        close_search()
    else: 
        show_search()


def char_convert(event=None):
    pos = text_box_en.index(tk.INSERT)
    start = pos + "-6c"
    txt = text_box_en.get(start, pos)
    m = re.search(r"[A-Z0-9]+", txt)
    if m:
        try:
            res = chr(int(m.group(0), 16))
        except:
            return
        text_box_en.replace(f"{start}+{str(m.start())}c", pos, res)


def del_word(event):
    pos = text_box_en.index(tk.INSERT)
    start = "linestart" if event.state & 0x0001 else "wordstart"
    end = "lineend" if event.state & 0x0001 else "wordend"
    if event.keycode == 8:
        text_box_en.delete(f"{pos} -1c {start}", pos)
    elif event.keycode == 46:
        text_box_en.delete(pos, f"{pos} {end}")


def format_text(event):
    if not text_box_en.tag_ranges("sel"):
        print("No selection to format.")
        return
    if event.keycode == 73:
        open = "<i>"
        close = "</i>"
    elif event.keycode == 66:
        open = "<b>"
        close = "</b>"
    else:
        return

    text_box_en.insert(tk.SEL_FIRST, open)
    text_box_en.insert(tk.SEL_LAST, close)
    return "break"  # prevent control char entry


def process_text(event):
    proc_text = textprocess.processText(cur_file,
                                        cleanText(text_box_en.get(1.0, tk.END)),
                                        {"redoNewlines": True if event.state & 0x0001 else False,
                                         "replaceMode": "limit",
                                         "lineLength": 60,
                                         "targetLines": 99})
    text_box_en.delete(1.0, tk.END)
    text_box_en.insert(tk.END, proc_text)
    return "break"


def txt_for_display(text, reverse=False):
    if cur_file.escapeNewline:
        if reverse:
            text = cleanText(text)
            return text.replace("\n", "\\n")
        else:
            return text.replace("\\n", "\n")
    else:
        if reverse:
            text = cleanText(text)
        return text


def cleanText(text: str):
    return " \n".join([line.strip() for line in text.strip().split("\n")])

def loadFont(fontPath):
    # code modified from https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
    # origFontList = list(tk.font.families())
    if isinstance(fontPath, bytes):
        pathbuf = create_string_buffer(fontPath)
        AddFontResourceEx = windll.gdi32.AddFontResourceExA
    elif isinstance(fontPath, str):
        pathbuf = create_unicode_buffer(fontPath)
        AddFontResourceEx = windll.gdi32.AddFontResourceExW
    else:
        raise TypeError('fontPath must be bytes or str')

    flags = 0x10 | 0x20 # private and not enumerable
    # flags = 0x10 | 0 # private and enumerable

    numFontsAdded = AddFontResourceEx(byref(pathbuf), flags, 0)
    # print(f"added {numFontsAdded} fonts:", [name for name in tk.font.families() if name not in origFontList])
    # print(tk.font.families()[-3:])

    return numFontsAdded


def tlNames():
    import names
    names.translate(cur_file)
    load_block()

def nextMissingName():
    for idx, block in enumerate(cur_file.textBlocks):
        if block.get("jpName") not in common.NAMES_BLACKLIST and not block.get("enName"):
            block_dropdown.current(idx)
            change_block()


def listen(event=None):
    global AUDIO_PLAYER
    if cur_file.version < 6:
        print("Old file version, does not have voice info.")
        return
    storyId = cur_file.data.get("storyId")
    voiceIdx = cur_file.textBlocks[cur_block].get("voiceIdx")
    if len(storyId) != 9:
        # Could support a few other types but isn't useful.
        print("Unsupported type.")
        return
    elif storyId is None:
        print("File has an invalid storyid.")
        return
    elif voiceIdx is None:
        print("No voice info found for this block.")
        return
    else:
        if not AUDIO_PLAYER:
            AUDIO_PLAYER = AudioPlayer()
        AUDIO_PLAYER.play(storyId, voiceIdx, sType=cur_file.type)


def _switchWidgetFocusForced(e):
    e.widget.tk_focusNext().focus()
    return "break"

def onClose(event=None):
    if AUDIO_PLAYER:
        AUDIO_PLAYER.dealloc()
    root.quit()

def main():
    global files
    global root
    global cur_chapter
    global cur_block
    global chapter_dropdown
    global block_dropdown
    global btn_next
    global speaker_jp_entry
    global speaker_en_entry
    global block_duration_label
    global block_duration_spinbox
    global text_box_jp
    global text_box_en
    global btn_choices
    global btn_colored
    global save_on_next
    global skip_translated
    global large_font

    cur_chapter = 0
    cur_block = 0

    ap = common.Args("Story editor", types=common.SUPPORTED_TYPES)
    ap.add_argument("-src")
    ap.add_argument("-dst", help=SUPPRESS)
    args = ap.parse_args()
    if args.src:
        files = [args.src]
    else:
        files = common.searchFiles(args.type, args.group, args.id, args.idx, changed = args.changed)
        if not files:
            print("No files match given criteria")
            raise SystemExit

    files.sort()

    root = tk.Tk()
    root.title("Edit Story")
    root.resizable(False, False)
    if common.IS_WIN: loadFont(r"src/data/RodinWanpakuPro-B-ex.otf")
    else: print("Non-Windows system: To load custom game font install 'src/data/RodinWanpakuPro-B-ex.otf' to system fonts.")
    large_font = Font(root, family="RodinWanpakuPro B", size=18, weight="normal")

    chapter_label = tk.Label(root, text="Chapter")
    chapter_label.grid(row=0, column=0)
    textblock_label = tk.Label(root, text="Block")
    textblock_label.grid(row=0, column=2)

    chapter_dropdown = ttk.Combobox(root, width=35)
    chapter_dropdown['values'] = [f.split("\\")[-1] for f in files]
    chapter_dropdown.bind("<<ComboboxSelected>>", change_chapter)
    chapter_dropdown.grid(row=0, column=1, sticky=tk.NSEW)
    block_dropdown = ttk.Combobox(root, width=35)
    block_dropdown.bind("<<ComboboxSelected>>", change_block)
    block_dropdown.grid(row=0, column=3, sticky=tk.NSEW)

    speaker_jp_label = tk.Label(root, text="Speaker (JP)")
    speaker_jp_label.grid(row=1, column=0)
    speaker_jp_entry = tk.Entry(root)
    speaker_jp_entry.grid(row=1, column=1, sticky=tk.NSEW)

    speaker_en_label = tk.Label(root, text="Speaker (EN)")
    speaker_en_label.grid(row=1, column=2)
    speaker_en_entry = tk.Entry(root)
    speaker_en_entry.grid(row=1, column=3, sticky=tk.NSEW)

    block_duration_label = tk.Label(root, text="Text Duration")
    block_duration_label.grid(row=2, column=2)
    block_duration_spinbox = ttk.Spinbox(root, from_=0, to=9999, increment=1, width=5)
    block_duration_spinbox.grid(row=2, column=3, sticky=tk.W)

    text_box_jp = tk.Text(root, width=TEXTBOX_WIDTH, height=4, state='disabled', font=large_font)
    text_box_jp.grid(row=3, column=0, columnspan=4)

    text_box_en = tk.Text(root, width=TEXTBOX_WIDTH, height=5, undo=True, font=large_font)
    text_box_en.grid(row=4, column=0, columnspan=4)

    frm_btns_bot = tk.Frame(root)
    btn_choices = tk.Button(frm_btns_bot, text="Choices", command=lambda: toggleTextListPopup(target=cur_choices), state='disabled', width=10)
    btn_choices.grid(row=0, column=0)
    btn_colored = tk.Button(frm_btns_bot, text="Colored", command=lambda: toggleTextListPopup(target=cur_colored), state='disabled', width=10)
    btn_colored.grid(row=1, column=0)
    btn_listen = tk.Button(frm_btns_bot, text="Listen", command=listen, width=10)
    btn_listen.grid(row=0, column=1)
    btn_search = tk.Button(frm_btns_bot, text="Search", command=toggleSearchPopup, width=10)
    btn_search.grid(row=1, column=1)
    btn_reload = tk.Button(frm_btns_bot, text="Reload", command=reload_chapter, width=10)
    btn_reload.grid(row=0, column=2)
    btn_save = tk.Button(frm_btns_bot, text="Save", command=saveFile, width=10)
    btn_save.grid(row=1, column=2)
    btn_prev = tk.Button(frm_btns_bot, text="Prev", command=prev_block, width=10)
    btn_prev.grid(row=0, column=3)
    btn_next = tk.Button(frm_btns_bot, text="Next", command=next_block, width=10)
    btn_next.grid(row=1, column=3)
    frm_btns_bot.grid(row=5, columnspan=4, sticky=tk.NSEW)
    for idx in range(frm_btns_bot.grid_size()[0]):
        frm_btns_bot.columnconfigure(idx, weight=1)

    frm_btns_side = tk.Frame(root)
    side_buttons = (
        tk.Button(frm_btns_side, text="Italic", command=lambda: format_text(SimpleNamespace(key=73))),
        tk.Button(frm_btns_side, text="Bold", command=lambda: format_text(SimpleNamespace(key=66))),
        tk.Button(frm_btns_side, text="Convert\nunicode codepoint", command=char_convert),
        tk.Button(frm_btns_side, text="Process text", command=lambda: process_text(SimpleNamespace(state=0))),
        tk.Button(frm_btns_side, text="Process text\n(clean newlines)", command=lambda: process_text(SimpleNamespace(state=1))),
        tk.Button(frm_btns_side, text="Translate speakers", command=tlNames),
        tk.Button(frm_btns_side, text="Find missing speakers", command=nextMissingName)
    )
    for btn in side_buttons:
        btn.pack(pady=3, fill=tk.X)
    frm_btns_side.grid(column=5, row=0, rowspan=5, sticky=tk.NE)


    save_on_next = tk.IntVar()
    save_on_next.set(0)
    save_checkbox = tk.Checkbutton(root, text="Save chapter on block change", variable=save_on_next)
    save_checkbox.grid(row=6, column=3)
    skip_translated = tk.IntVar()
    skip_translated.set(0)
    skip_checkbox = tk.Checkbutton(root, text="Skip translated blocks", variable=skip_translated)
    skip_checkbox.grid(row=6, column=2)
    for f in (root, frm_btns_bot, frm_btns_side):
        for w in f.children.values():
            w.configure(takefocus=0)
    text_box_en.configure(takefocus=1)
    speaker_en_entry.configure(takefocus=1)
    text_box_en.bind('<Tab>', _switchWidgetFocusForced)
    speaker_en_entry.bind('<Tab>', _switchWidgetFocusForced)
    text_box_en.focus()

    create_text_list_popup()
    create_search_popup()
    chapter_dropdown.current(cur_chapter)
    change_chapter(initialLoad=True)
    block_dropdown.current(cur_block)

    root.bind("<Control-Return>", next_block)
    root.bind("<Control-s>", saveFile)
    root.bind("<Alt-Up>", prev_block)
    root.bind("<Alt-Down>", next_block)
    root.bind("<Control-Alt-Up>", prev_ch)
    root.bind("<Control-Alt-Down>", next_ch)
    root.bind("<Alt-Right>", copy_block)
    root.bind("<Alt-c>", lambda _: toggleTextListPopup(target=cur_choices))
    text_list_window.bind("<Alt-c>", lambda _: toggleTextListPopup(target=cur_choices))
    root.bind("<Control-Alt-c>", lambda _: toggleTextListPopup(target=cur_colored))
    text_list_window.bind("<Control-Alt-c>", lambda _: toggleTextListPopup(target=cur_colored))
    root.bind("<Alt-x>", char_convert)
    root.bind("<Control-BackSpace>", del_word)
    root.bind("<Control-Shift-BackSpace>", del_word)
    root.bind("<Control-Delete>", del_word)
    root.bind("<Control-Shift-Delete>", del_word)
    text_box_en.bind("<Control-i>", format_text)
    text_box_en.bind("<Control-b>", format_text)
    text_box_en.bind("<Alt-f>", process_text)
    text_box_en.bind("<Alt-F>", process_text)
    root.bind("<Control-f>", toggleSearchPopup)
    root.bind("<Control-h>", listen)

    root.protocol("WM_DELETE_WINDOW", onClose)

    root.mainloop()


if __name__ == "__main__":
    main()
