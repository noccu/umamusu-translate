from argparse import SUPPRESS
import re
import common
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.font import Font


def change_chapter(event = None):
    global cur_chapter
    global cur_block
    global chapter_dropdown
    cur_chapter = chapter_dropdown.current()
    cur_block = 0
    load_block(None, True)

def change_block(event = None, dir = 1):
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

def txt_for_display(text, reverse = False):
    if files[cur_chapter].type in ("mdb", "race", "preview"):
        if reverse:
            text = cleanText(text)
            return text.replace("\n", "\\n")
        else:
            return text.replace("\\n", "\n")
    else: 
        if reverse:
            text = cleanText(text)
        return text

def cleanText(text):
    return " \n".join([line.strip() for line in text.strip().split("\n")])

def load_block(event = None, loadBlocks = False, reload = False, dir = 1):
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
    global cur_choices_textboxes
    global cur_choices_texts

    # print(cur_chapter, cur_block)


    if isinstance(files[cur_chapter], str):
        files[cur_chapter] = common.TranslationFile(files[cur_chapter])
    elif reload:
        files[cur_chapter] = common.TranslationFile(files[cur_chapter].file)
    blocks = files[cur_chapter].textBlocks

    if loadBlocks:
        block_dropdown['values'] = [f"{i+1} - {block['jpText'][:8]}" for i, block in enumerate(blocks)]

    cur_block_data =  blocks[cur_block]

    if skip_translated.get() == 1:
        while cur_block_data['enText'] and cur_block > 0 and cur_block < len(blocks)-1:
            cur_block += dir
            cur_block_data =  blocks[cur_block]
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
    btn_choices['state'] = 'disabled'
    btn_choices.config(bg='SystemButtonFace')
    cur_choices = None
    cur_choices_textboxes = list()
    cur_choices_texts = list()
    if 'choices' in cur_block_data:
        btn_choices['state'] = 'normal'
        btn_choices.config(bg='#00ff00')
        cur_choices = cur_block_data['choices']

    # print(cur_block_data)


def save_block():
    global files
    global cur_chapter
    global cur_choices
    global cur_choices_texts
    global speaker_en_entry
    global text_box_en
    global block_duration_spinbox

    cur_file = files[cur_chapter]
    if "enName" in cur_file.textBlocks[cur_block]: 
        cur_file.textBlocks[cur_block]['enName'] = cleanText(speaker_en_entry.get())
    cur_file.textBlocks[cur_block]['enText'] = txt_for_display(text_box_en.get(1.0, tk.END), reverse=True)

    if cur_choices and cur_choices_texts:
        for i in range(len(cur_choices_texts)):
            cur_file.textBlocks[cur_block]['choices'][i]['enText'] = txt_for_display(cur_choices_texts[i], reverse=True)

    # Get the new clip length from spinbox
    new_clip_length = block_duration_spinbox.get()
    if new_clip_length.isnumeric():
        new_clip_length = int(new_clip_length)
        if "origClipLength" in cur_file.textBlocks[cur_block] and new_clip_length != cur_file.textBlocks[cur_block]['origClipLength']:
            cur_file.textBlocks[cur_block]['newClipLength'] = new_clip_length
        else:
            cur_file.textBlocks[cur_block].pop('newClipLength', None)
            if not "origClipLength" in cur_file.textBlocks[cur_block]:
                messagebox.showwarning(master=block_duration_spinbox, title="Cannot save clip length", message="This text block does not have an original clip length defined and thus cannot save a custom clip length. Resetting to -1.")
                block_duration_spinbox.delete(0, tk.END)
                block_duration_spinbox.insert(0, "-1")
    elif new_clip_length != "-1":
        cur_file.textBlocks[cur_block].pop('newClipLength', None)

def prev_block(event = None):
    if cur_block - 1 > -1:
        block_dropdown.current(cur_block - 1)
        change_block(dir=-1)

def next_block(event = None):
    if next_index != -1:
        block_dropdown.current(next_index)
        change_block()
    else: print("Reached end of chapter")

def copy_block(event = None):
    root.clipboard_clear()
    root.clipboard_append(files[cur_chapter].textBlocks[cur_block]['jpText'])


def close_choices(popup_window):
    global cur_choices_texts
    global cur_choices_textboxes
    global cur_choices
    cur_choices_texts = [textbox.get(1.0, tk.END).strip().replace("\n", " \n") for textbox in cur_choices_textboxes]
    for i in range(len(cur_choices_texts)):
        cur_choices[i]['enText'] = cur_choices_texts[i]
    popup_window.destroy()

def saveFile(event = None):
    global files
    global cur_chapter
    if save_on_next.get() == 0:
        print("Saved")
    save_block()
    files[cur_chapter].save()

def show_choices():
    global files
    global cur_choices
    global cur_choices_textboxes
    global large_font

    cur_choices_textboxes = list()

    if cur_choices:
        popup_window = tk.Toplevel()
        popup_window.protocol("WM_DELETE_WINDOW", lambda: close_choices(popup_window))
        popup_window.title("Choices")
        popup_window.geometry("693x400")

        scroll_frame = ttk.Frame(popup_window)
        scroll_frame.pack(fill='both', expand=True)

        scroll_canvas = tk.Canvas(scroll_frame)
        scroll_canvas.pack(side='left', fill='both', expand=True)

        scroll_bar = ttk.Scrollbar(scroll_frame, orient='vertical', command=scroll_canvas.yview)
        scroll_bar.pack(side='right', fill='y')

        scroll_canvas.configure(yscrollcommand=scroll_bar.set)
        scroll_canvas.bind('<Configure>', lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox('all')))

        window_frame = ttk.Frame(scroll_canvas)
        scroll_canvas.create_window((0, 0), window=window_frame, anchor='nw')

        for choice in cur_choices:
            cur_jp_text = tk.Text(window_frame, width=50, height=2, font=large_font)
            cur_jp_text.insert(tk.END, choice['jpText'])
            cur_jp_text['state'] = 'disabled'
            cur_jp_text.pack()
            cur_en_text = tk.Text(window_frame, height=2, width=50, undo=True, font=large_font)
            cur_choices_textboxes.append(cur_en_text)
            cur_en_text.insert(tk.END, choice['enText'])
            cur_en_text.pack()
            ttk.Separator(window_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)

def char_convert(event = None):
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
    global save_on_next
    global skip_translated
    global cur_choices_texts
    global large_font

    cur_chapter = 0
    cur_block = 0
    cur_choices_texts = list()

    ap = common.Args("Story editor")
    ap.add_argument("-src")
    ap.add_argument("-dst", help=SUPPRESS)
    args = ap.parse_args()
    if args.src:
        files = [args.src]
    else:
        files = common.searchFiles(args.type, args.group, args.id, args.idx)

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

    text_box_jp = tk.Text(root, width=54, height=4, state='disabled', font=large_font)
    text_box_jp.grid(row=3, column=0, columnspan=4)

    text_box_en = tk.Text(root, width=54, height=5, undo=True, font=large_font)
    text_box_en.grid(row=4, column=0, columnspan=4)

    btn_choices = tk.Button(root, text="Choices", command=show_choices, state='disabled', width=10)
    btn_choices.grid(row=5, column=0)
    btn_reload = tk.Button(root, text="Reload", command=lambda: load_block(reload=True), width=10)
    btn_reload.grid(row=5, column=1)
    btn_save = tk.Button(root, text="Save", command=saveFile, width=10)
    btn_save.grid(row=5, column=2)
    btn_next = tk.Button(root, text="Next", command=next_block, width=10)
    btn_next.grid(row=5, column=3)

    save_on_next = tk.IntVar()
    save_on_next.set(0)
    save_checkbox = tk.Checkbutton(root, text="Save chapter on block change", variable=save_on_next)
    save_checkbox.grid(row=6, column=3)
    skip_translated = tk.IntVar()
    skip_translated.set(0)
    skip_checkbox = tk.Checkbutton(root, text="Skip translated blocks", variable=skip_translated)
    skip_checkbox.grid(row=6, column=2)

    root.bind("<Control-Return>", next_block)
    root.bind("<Control-s>", saveFile)
    root.bind("<Alt-Up>", prev_block)
    root.bind("<Alt-Down>", next_block)
    root.bind("<Alt-Right>", copy_block)
    root.bind("<Alt-x>", char_convert)
    root.bind("<Control-BackSpace>", del_word)
    root.bind("<Control-Shift-BackSpace>", del_word)
    root.bind("<Control-Delete>", del_word)
    root.bind("<Control-Shift-Delete>", del_word)

    chapter_dropdown.current(cur_chapter)
    change_chapter()
    block_dropdown.current(cur_block)

    root.mainloop()




if __name__ == "__main__":
    main()
