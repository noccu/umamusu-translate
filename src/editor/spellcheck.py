import regex as re
import tkinter as tk
from functools import partial

import symspellpy

from common.types import TranslationFile

from .display import PopupMenu


class SpellCheck:
    dictPath = "src/data/frequency_dictionary_en_82_765.txt"
    customDictPath = "src/data/umatl_spell_dict.txt"
    dictionary: symspellpy.SymSpell = None
    nameFreq = 30000000000
    defaultFreq = 30000
    newDict = list()

    def __init__(self, widget: tk.Text) -> None:
        widget.tag_config("spellError", underline=True, underlinefg="red")
        widget.tag_bind("spellError", "<Button-3>", self.show_suggestions)
        widget.bind("<KeyRelease>", self.check_spelling)
        widget.bind("<Control-space>", self.autocomplete)
        # widget.word_suggestions = {}
        self.menu = PopupMenu(widget, tearoff=0)
        self.widget = widget
        if SpellCheck.dictionary is None:
            SpellCheck.dictionary = symspellpy.SymSpell()
            SpellCheck.dictionary.load_dictionary(SpellCheck.dictPath, 0, 1)
            if not SpellCheck.dictionary.create_dictionary(self.customDictPath, "utf8"):
                print("No custom dict loaded.")
            self._loadNames()

    def add_word(self, word: str, fixRange: tuple, isName=False):
        lcword = word.lower()
        # Max importance of names
        # freq = 30000000000 if word[0].isupper() else 30000
        freq = SpellCheck.nameFreq if isName else SpellCheck.defaultFreq
        SpellCheck.newDict.append(f"{lcword} {freq}\n")
        SpellCheck.dictionary.create_dictionary_entry(lcword, freq)
        # Remove UI marking
        del self.widget.word_suggestions[word]
        self.widget.tag_remove("spellError", *fixRange)

    def _loadNames(self):
        namesFile = TranslationFile("translations/mdb/char-name.json")
        for entry in namesFile.textBlocks:
            name = entry.get("enText").lower().split()
            for n in name:
                if len(n) < 3:
                    continue
                SpellCheck.dictionary.create_dictionary_entry(n, SpellCheck.nameFreq)

    def check_spelling(self, event=None):
        if event and event.keysym not in ("space", "BackSpace", "Delete"):
            return
        text = self.widget.get("1.0", tk.END)
        words = re.split(r"[^\p{L}\-']+", text)
        # Reset state
        self.widget.tag_remove("spellError", "1.0", tk.END)
        self.widget.word_suggestions = {}
        # Iterate over each word and check for spelling errors
        searchIdx = 0
        for word in words:
            if word == "" or len(word) == 1 or word.lower() in SpellCheck.dictionary.words:
                searchIdx += len(word)
                continue
            # print(f"Looking up {word}")
            suggestions = SpellCheck.dictionary.lookup(
                word, symspellpy.Verbosity.CLOSEST, transfer_casing=True
            )
            startIdx = text.index(word, searchIdx)
            endIdx = startIdx + len(word)
            searchIdx += len(word)
            self.widget.tag_add("spellError", f"1.0+{startIdx}c", f"1.0+{endIdx}c")
            self.widget.word_suggestions[word] = suggestions

    def autocomplete(self, event: tk.Event = None):
        # TCL regex  = weird, also reverse search = everything reverse?
        # \M = word boundary (end only), \Z = end of string, \A = start
        # Both \A and \Z seem to work bu only \M worked before, I think?
        wordstart = self.widget.search(
            r"[^ ]+(?=\Z|[\n ])", index=tk.INSERT, backwards=True, regexp=True, nocase=True
        )
        partialWord = self.widget.get(wordstart, tk.INSERT)
        # Keep capitalization
        isCapitalized = partialWord[0].isupper()
        partialWord = partialWord.lower()
        self.menu.clear()
        suggestions = 0
        for word in SpellCheck.dictionary.words:
            if word.startswith(partialWord):
                if isCapitalized:
                    word = word.title()
                self.menu.add_command(
                    label=word, command=partial(self.autoReplace, wordstart, word)
                )
                suggestions += 1
            if suggestions == 25:
                break
        self.menu.show(event, atInsert=True)

    def autoReplace(self, wordstart, word):
        self.widget.delete(wordstart, tk.INSERT)
        self.widget.insert(wordstart, word)

    def show_suggestions(self, event):
        currentSpellFix = self.widget.tag_prevrange(
            "spellError", tk.CURRENT
        ) or self.widget.tag_nextrange("spellError", tk.CURRENT)
        clicked_word = self.widget.get(*currentSpellFix)
        # print(f"Clicked {clicked_word}")
        suggestions = self.widget.word_suggestions.get(clicked_word)
        # Set up context menu handling
        self.menu.clear()
        for suggestion in suggestions:
            self.menu.add_command(
                label=suggestion.term,
                command=partial(self.replace_word, currentSpellFix, clicked_word, suggestion.term),
            )
        self.menu.add_separator()
        self.menu.add_command(
            label="Add to dictionary", command=lambda: self.add_word(clicked_word, currentSpellFix)
        )
        self.menu.add_command(
            label="Add as name", command=lambda: self.add_word(clicked_word, currentSpellFix, True)
        )
        self.menu.show(event)

    def replace_word(self, fixRange, oldWord, replacement):
        del self.widget.word_suggestions[oldWord]
        self.widget.tag_remove("spellError", *fixRange)
        self.widget.delete(*fixRange)
        self.widget.insert(fixRange[0], replacement)
        # print(f"Replaced {oldWord} with {replacement}")

    @classmethod
    def saveNewDict(cls):
        if len(cls.newDict) == 0:
            return
        with open(cls.customDictPath, "a", encoding="utf8", newline="\n") as f:
            f.writelines(cls.newDict)
        print("New words added to umatl dict.")
