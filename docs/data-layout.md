# Data Layout

An overview of the game vs translation data layout to provide an understanding of how the tool works at a high level.

For specific translation instructions, see [translating.md](translating.md).

First, there are two relevant game directories:
* `<install dir>`: The .exe file's install directory. You picked this when installing the game. Static game files and our added config files go here.
* `<local data dir>`: `~/AppData/LocalLow/cygames/umamusume/`. The 'local data directory', where the game downloads new (and old) content.

## Story/Lyrics etc.

### Game

The local data directory contains a file called `meta`, which is an SQLite database mapping story/winning live/etc. Unity files from a unity asset path (looks like a filepath) to a custom hash of its contents.

These downloaded Unity files are stored in `<local data dir>/dat/` as files named with this hash, grouped into directories by the first two letters of each hash. For example, for some story data with hash `QOSUQ2JXFMHDA2LJJR2SDVBQ4LOGOKME`, it is found in the file `~/AppData/LocalLow/cygames/umamusume/dat/QO/QOSUQ2JXFMHDA2LJJR2SDVBQ4LOGOKME`.

### Translations

The various story/song/etc. files are organized in this repo's `translations` folder by a typically three-part 'story ID' parsed based on the structure of the server filepath mentioned in the above `meta` database. See [id-structure.md](id-structure.md) for a breakdown of the meaning of each part of the story ID.

Json files storing the english translations for each of the game's data files - each of which is typically one scene - are stored in this repo at `translations/<text_type>/<group ID>/<sub-ID>/<idx> (title if available).json`.

E.g. `translations\story\04\1026\003 (譲れない答え).json`


## master.mdb (skills, names, etc.)

### Game

Located at `~/AppData/LocalLow/cygames/umamusume/master/master.mdb`, this is an SQLite database containing various non-dialogue data on the game, but including text data like menu screen text, item names, skill descriptions, etc.

### Translations

Stored in `translations/mdb`, these are organized as JSON files holding the various sub-types of data in `master.mdb`. Each contains JP to english text mappings.

`src/mdb/index.json` maps each of these files to the master.mdb database table that they apply to (most being in a `text_data` table).

To update `master.mdb`, it is simply searched for each of the JP text entries from these JSON files and replaced with the corresponding EN text.

Note therefore that updates to existing translations can only be applied by restoring `master.mdb` so it contains the original JP text, and re-running `mdb import.bat`. This is easily achieved by deleting `~/AppData/LocalLow/cygames/umamusume/master/master.mdb` and re-launching the game; it will re-download it. Alternatively you can use `python mdb/import.py --backup` and `python mdb/import.py --restore` to backup/restore a copy of master.mdb for convenience.

## UI (buttons, menu labels, etc.)

### Game
These mostly come from resource files in `<install dir>/umamusume_Data`. However, we don't really care where exactly, because this is where the TLG tool handles things for us.

### Translations

The TLG tool maps hashes of UI objects (e.g. buttons) to the strings of JP text that appear on them. It then replaces this text based on two dictionaries we provide to TLG in `<install dir>/localized_data/`:

* `dynamic.json`: A map from hashes to EN text.
* `static.json`: A map from JP text to EN text.

TLG will first check if a UI object's hash is in `dynamic.json` and set the text to that, and if not it will replace any substrings of the text with translations from `static.json`.

To generate these dicts, the translation repo maintains two dictionaries of its own:
* `src/data/static_dump.json`: A map of hashes to JP text. Short hashes for static text, long for dynamic. Note that since some text from master.mdb gets inserted before TLG sees it, some JP text in this file is partially-translated already.
* `translations/localify/ui.json`: A map of JP text to EN text.

These two files are used to construct `localify/localized_data/dynamic.json` and `localify/localized_data/static.json`, which can then be copied to `<install dir>/localized_data/`.
