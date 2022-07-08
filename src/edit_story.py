from argparse import SUPPRESS
import re
import common
from helpers import isEnglish
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font
import textprocess

TEXTBOX_WIDTH = 54


def change_chapter(event=None):
    global cur_chapter
    global cur_block
    global chapter_dropdown
    cur_chapter = chapter_dropdown.current()
    cur_block = 0
    load_block(None, True)

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
    global cur_chapter
    global cur_block
    global block_dropdown
    global files
    global save_on_next

    save_block()
    if save_on_next.get() == 1:
        saveFile()

    cur_block = block_dropdown.current()
    load_block(dir=dir)


def load_block(event=None, loadBlocks=False, reload=False, dir=1):
    global files
    global cur_chapter
    global cur_block
    global chapter_dropdown
    global block_dropdown
    global text_box_jp
    global text_box_en
    global speaker_jp_entry
    global speaker_en_entry
    global block_duration_label
    global block_duration_spinbox
    global btn_next
    global next_index
    global btn_choices
    global cur_choices
    global cur_colored
    global extra_text_list_textboxes

    # print(cur_chapter, cur_block)

    if isinstance(files[cur_chapter], str):
        files[cur_chapter] = common.TranslationFile(files[cur_chapter])
    elif reload:
        files[cur_chapter].reload()
    blocks = files[cur_chapter].textBlocks

    if loadBlocks:
        block_dropdown['values'] = [f"{i+1} - {block['jpText'][:8]}" for i, block in enumerate(blocks)]
        ll = textprocess.calcLineLen(files[cur_chapter], False)
        # Attempt to calc the relation of line length to text box size
        ll = int(ll / (0.958 * ll**0.057) + 1) if ll else TEXTBOX_WIDTH
        text_box_en.config(width=ll)
        text_box_jp.config(width=ll)

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
        speaker_en_entry.insert(0, cur_block_data.get('enName', ""))

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
        btn_choices.config(bg='SystemButtonFace')
        
    # Update colored button
    cur_colored = cur_block_data.get('coloredText')
    if cur_colored:
        btn_colored['state'] = 'normal'
        btn_colored.config(bg='#00ff00')
        toggleTextListPopup(allowShow=False, target=cur_colored)
    else:
        btn_colored['state'] = 'disabled'
        btn_colored.config(bg='SystemButtonFace')
        

def save_block():
    global files
    global cur_chapter
    global speaker_en_entry
    global text_box_en
    global block_duration_spinbox

    cur_file = files[cur_chapter]
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
    root.clipboard_append(files[cur_chapter].textBlocks[cur_block]['jpText'])


def saveFile(event=None):
    if save_on_next.get() == 0:
        print("Saved")
    save_block()
    files[cur_chapter].save()


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
    text_list_popup_scrollable = False

    extra_text_list_textboxes = list()
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
        cur_jp_text = tk.Text(window_frame, width=42, height=2, font=large_font)
        cur_jp_text.pack(anchor="w")
        cur_en_text = tk.Text(window_frame, height=2, width=42, undo=True, font=large_font)
        cur_en_text.pack(anchor="w")
        extra_text_list_textboxes.append((cur_jp_text, cur_en_text))
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
    proc_text = textprocess.processText(files[cur_chapter],
                                        cleanText(text_box_en.get(1.0, tk.END)),
                                        {"redoNewlines": True if event.state & 0x0001 else False,
                                         "replaceMode": "limit",
                                         "lineLength": 60,
                                         "targetLines": 99})
    text_box_en.delete(1.0, tk.END)
    text_box_en.insert(tk.END, proc_text)
    return "break"


def txt_for_display(text, reverse=False):
    if files[cur_chapter].escapeNewline:
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
    # root.geometry("693x250")
    large_font = Font(root, size=18)

    chapter_label = tk.Label(root, text="Chapter")
    chapter_label.grid(row=0, column=0)
    textblock_label = tk.Label(root, text="Block")
    textblock_label.grid(row=0, column=2)

    chapter_dropdown = ttk.Combobox(root)
    chapter_dropdown['values'] = [f.split("\\")[-1] for f in files]
    chapter_dropdown.bind("<<ComboboxSelected>>", change_chapter)
    chapter_dropdown.grid(row=0, column=1)
    block_dropdown = ttk.Combobox(root)
    block_dropdown.bind("<<ComboboxSelected>>", change_block)
    block_dropdown.grid(row=0, column=3)

    speaker_jp_label = tk.Label(root, text="Speaker (JP)")
    speaker_jp_label.grid(row=1, column=0)
    speaker_jp_entry = tk.Entry(root, width=30)
    speaker_jp_entry.grid(row=1, column=1)

    speaker_en_label = tk.Label(root, text="Speaker (EN)")
    speaker_en_label.grid(row=1, column=2)
    speaker_en_entry = tk.Entry(root, width=30)
    speaker_en_entry.grid(row=1, column=3)

    block_duration_label = tk.Label(root, text="Text Duration")
    block_duration_label.grid(row=2, column=2)
    block_duration_spinbox = ttk.Spinbox(root, from_=0, to=9999, increment=1, width=5)
    block_duration_spinbox.grid(row=2, column=3)

    text_box_jp = tk.Text(root, width=TEXTBOX_WIDTH, height=4, state='disabled', font=large_font)
    text_box_jp.grid(row=3, column=0, columnspan=4)

    text_box_en = tk.Text(root, width=TEXTBOX_WIDTH, height=5, undo=True, font=large_font)
    text_box_en.grid(row=4, column=0, columnspan=4)

    btn_choices = tk.Button(root, text="Choices", command=lambda: toggleTextListPopup(target=cur_choices), state='disabled', width=10)
    btn_choices.grid(row=5, column=0)
    btn_colored = tk.Button(root, text="Colored", command=lambda: toggleTextListPopup(target=cur_colored), state='disabled', width=10)
    btn_colored.grid(row=5, column=1)
    btn_reload = tk.Button(root, text="Reload", command=lambda: load_block(reload=True), width=10)
    btn_reload.grid(row=5, column=2)
    btn_save = tk.Button(root, text="Save", command=saveFile, width=10)
    btn_save.grid(row=5, column=3)
    btn_next = tk.Button(root, text="Next", command=next_block, width=10)
    btn_next.grid(row=5, column=4)

    save_on_next = tk.IntVar()
    save_on_next.set(0)
    save_checkbox = tk.Checkbutton(root, text="Save chapter on block change", variable=save_on_next)
    save_checkbox.grid(row=6, column=3)
    skip_translated = tk.IntVar()
    skip_translated.set(0)
    skip_checkbox = tk.Checkbutton(root, text="Skip translated blocks", variable=skip_translated)
    skip_checkbox.grid(row=6, column=2)

    chapter_dropdown.current(cur_chapter)
    change_chapter()
    block_dropdown.current(cur_block)
    create_text_list_popup()

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

    root.mainloop()


if __name__ == "__main__":
    main()
