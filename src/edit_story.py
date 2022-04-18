from numpy import block
import common
import json
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

args = common.Args().parse()
if args.getArg("-h"):
    common.usage("-n <db-translate uma-name.csv> [-src <file to process>]")
NAMES_FILE = args.getArg("-n", False)
TARGET_FILE = args.getArg("-src", False)
TARGET_TYPE = args.getArg("-t", "story").lower()
TARGET_GROUP = args.getArg("-g", False)
TARGET_ID = args.getArg("-id", False)
TARGET_IDX = args.getArg("-idx", False)


def read_json(file):
    with open(file, "r", encoding='utf-8') as f:
        data = json.load(f)
    return data


def save_json(data, file):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def change_chapter(event = None):
    global cur_chapter
    global cur_block
    global chapter_dropdown
    cur_chapter = chapter_dropdown.current()
    cur_block = 0
    load_block()


def change_block(event = None):
    global cur_chapter
    global cur_block
    global block_dropdown
    cur_block = block_dropdown.current()
    load_block()


def load_block(event = None):
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

    chapter_dropdown.current(cur_chapter)

    blocks = read_json(files[cur_chapter])['text']

    block_dropdown['values'] = [f"{i+1} - {blocks[i]['jpText'][:8]}" for i in range(len(blocks))]
    block_dropdown.current(cur_block)

    cur_block_data =  blocks[cur_block]
    next_index = cur_block_data['nextBlock'] - 1
    if next_index < 1:
        next_index = -1
    if next_index > 0:
        btn_next['state'] = 'normal'
        btn_next['text'] = f"Next ({next_index + 1})"
    else:
        btn_next['state'] = 'disabled'
        btn_next['text'] = "Next"

    # Fill in the text boxes
    speaker_jp_entry.delete(0, tk.END)
    speaker_jp_entry.insert(0, cur_block_data['jpName'])
    speaker_en_entry.delete(0, tk.END)
    speaker_en_entry.insert(0, cur_block_data['enName'])

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
    text_box_jp.insert(tk.END, cur_block_data['jpText'])
    text_box_jp.configure(state='disabled')
    text_box_en.delete(1.0, tk.END)
    text_box_en.insert(tk.END, cur_block_data['enText'])

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

    cur_file = read_json(files[cur_chapter])
    cur_file['text'][cur_block]['enName'] = " \n".join([line.strip() for line in speaker_en_entry.get().strip().split("\n")])
    cur_file['text'][cur_block]['enText'] = " \n".join([line.strip() for line in text_box_en.get(1.0, tk.END).strip().split("\n")])

    if cur_choices and cur_choices_texts:
        for i in range(len(cur_choices_texts)):
            cur_file['text'][cur_block]['choices'][i]['enText'] = " \n".join([line.strip() for line in cur_choices_texts[i].strip().split("\n")])
    
    # Get the new clip length from spinbox
    new_clip_length = block_duration_spinbox.get()
    if new_clip_length.isnumeric():
        new_clip_length = int(new_clip_length)
        if "origClipLength" in cur_file['text'][cur_block] and new_clip_length != cur_file['text'][cur_block]['origClipLength']:
            cur_file['text'][cur_block]['newClipLength'] = new_clip_length
        else:
            cur_file['text'][cur_block].pop('newClipLength', None)
            if not "origClipLength" in cur_file['text'][cur_block]:
                messagebox.showwarning(master=block_duration_spinbox, title="Cannot save clip length", message="This text block does not have an original clip length defined and thus cannot save a custom clip length. Resetting to -1.")
                block_duration_spinbox.delete(0, tk.END)
                block_duration_spinbox.insert(0, "-1")
    elif new_clip_length != "-1":
        cur_file['text'][cur_block].pop('newClipLength', None)

    save_json(cur_file, files[cur_chapter])


def next_block():
    global next_index
    global cur_block
    global save_on_next

    if save_on_next.get() == 1:
        save_block()

    cur_block = next_index
    load_block()


def close_choices(popup_window):
    global cur_choices_texts
    global cur_choices_textboxes
    global cur_choices
    cur_choices_texts = [textbox.get(1.0, tk.END).strip().replace("\n", " \n") for textbox in cur_choices_textboxes]
    for i in range(len(cur_choices_texts)):
        cur_choices[i]['enText'] = cur_choices_texts[i]
    popup_window.destroy()


def show_choices():
    global files
    global cur_choices
    global cur_choices_textboxes

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
            cur_jp_text = tk.Text(window_frame, width=80, height=4)
            cur_jp_text.insert(tk.END, choice['jpText'])
            cur_jp_text['state'] = 'disabled'
            cur_jp_text.pack()
            cur_en_text = tk.Text(window_frame, height=4, width=80, undo=True)
            cur_choices_textboxes.append(cur_en_text)
            cur_en_text.insert(tk.END, choice['enText'])
            cur_en_text.pack()
            ttk.Separator(window_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)

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
    global cur_choices_texts

    cur_chapter = 0
    cur_block = 0
    cur_choices_texts = list()

    if TARGET_FILE:
        files = [TARGET_FILE]
    else:
        files = common.searchFiles(TARGET_TYPE, TARGET_GROUP, TARGET_ID, TARGET_IDX)
    
    files.sort()
    
    root = tk.Tk()
    root.title("Edit Story")
    root.geometry("693x250")

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

    text_box_jp = tk.Text(root, width=86, height=4, state='disabled')
    text_box_jp.grid(row=3, column=0, columnspan=4)

    text_box_en = tk.Text(root, width=86, height=4, undo=True)
    text_box_en.grid(row=4, column=0, columnspan=4)

    btn_choices = tk.Button(root, text="Choices", command=show_choices, state='disabled', width=10)
    btn_choices.grid(row=5, column=0)
    btn_reload = tk.Button(root, text="Reload", command=load_block, width=10)
    btn_reload.grid(row=5, column=1)
    btn_save = tk.Button(root, text="Save", command=save_block, width=10)
    btn_save.grid(row=5, column=2)
    btn_next = tk.Button(root, text="Next", command=next_block, width=10)
    btn_next.grid(row=5, column=3)

    save_on_next = tk.IntVar()
    save_on_next.set(1)
    save_checkbox = tk.Checkbutton(root, text="Save on next", variable=save_on_next)
    save_checkbox.grid(row=6, column=3)

    load_block()

    root.mainloop()
    



if __name__ == "__main__":
    TARGET_ID = '1026'
    TARGET_GROUP = '04'

    main()
