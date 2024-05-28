from tkinter.font import Font, nametofont
from common import constants
from functools import cache

if constants.IS_WIN:
    from ctypes import byref, create_string_buffer, create_unicode_buffer, windll


_DYNAMIC: dict[tuple, Font] = dict()
UMATL_FONT_NAME = "RodinWanpakuPro UmaTl B"

def load(fontPath):
    # code modified from https://github.com/ifwe/digsby/blob/f5fe00244744aa131e07f09348d10563f3d8fa99/digsby/src/gui/native/win/winfonts.py#L15
    if not constants.IS_WIN:
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


def create(root, name=UMATL_FONT_NAME, size=18, italic=False, bold=False, id=None):
    if not id:
        id = (name, size, italic, bold)
    if id in _DYNAMIC:
        return _DYNAMIC[id]
    _DYNAMIC[id] = font = Font(
        root=root,
        family=name,
        size=size,
        weight="bold" if bold else "normal",
        slant="italic" if italic else "roman",
    )
    return font


def get(id):
    return _DYNAMIC.get(id)


def createFrom(root, font:Font = None, size=None, italic=False, bold=False, id=None):
    """Duplicate a font with new parameters, uses default tk font if not specified."""
    if id and (f := _DYNAMIC.get(id)):
        return f
    if font is None:
        font = nametofont("TkDefaultFont")
    # elif isinstance(font, tk.Widget):
        # pass
    font = font.actual()
    return create(root, font["family"], size or font["size"], italic, bold, id)

@cache
def getDefaultFontName():
    return nametofont("TkDefaultFont").actual()["family"]

def init(root):
    global DEFAULT, UI_JP, BOLD, ITALIC
    load(r"src/data/RodinWanpakuPro-UmaTl.otf")
    DEFAULT = create(root, id="default")
    UI_JP = create(root, "Meiryo UI", size=9, id="jp")
    BOLD = create(root, bold=True, id="bold")
    ITALIC = create(root, italic=True, id="italic")
