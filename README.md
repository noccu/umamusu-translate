[![Support me on Patreon](https://img.shields.io/badge/dynamic/json?color=%23ff424d&label=Patreon&query=data.attributes.patron_count&suffix=%20trainers&url=https%3A%2F%2Fwww.patreon.com%2Fapi%2Fcampaigns%2F2559100&style=flat-square&logo=patreon&logoColor=%23ff424d)](https://patreon.com/noccu)
[![Support me on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-%2300aff1?logo=kofi&logoColor=%2300aff1)](https://ko-fi.com/noccyu)
[![Discord](https://img.shields.io/discord/980222697151807488?logo=discord&logoColor=4bba35&label=Discord)](https://discord.gg/xBMgwh6hHY)

This project is a toolset to translate *Uma Musume Pretty Derby* to English. It includes a few scripts to patch the game using these tools.  
It accomplishes this by modifying the master.mdb file and Unity assets, aided additionally with dll hijacking through [TLG].

[Current state](#current-state). Guides for install and use can be found [below](#setting-up--getting-started).
Translation progress and credits are in [tl-progress].  
If you encounter problems, check the troubleshooting section with each guide step first. Open an issue or ask in the Discord server if this doesn't solve it.

This is based on the DMM version of the game and *should* work on linux anc mac too, with some limitations.  

# Features
Supports translating:
- Tutorials
- Character stories
- Main & Event stories
    - Race segments
    - Event prologues
- Special events
- Training stories
- Home interactions (lobby characters)
- Speech balloons (home screen, training, …) 
- Lyrics
- Most of the UI through [tlg].
- Skills, names, missions, and other such "dynamic" texts. (Same as the old *mdb patch*)
- Planned: images

Other:
- Deepl/fairseq integration for automatic machine translation.  
- Story editor for easy translating with audio support (or simply reading along without patching).
- Support for syncing with arbitrary framerates 
- Adjustable reading speed.
- Basic file/asset management tools (wip)
- Auto-updates

Included translations & credits: [tl-progress]  
Toolset info: [scripts](#script-info)

# Disclaimer
UmaTL is not affiliated with Cygames and is purely a fan-community effort.  
Assets are edited only for the purpose of translation and it is *the maintainer's belief* this is harmless and unlikely to be an issue. [^1]  
Nonetheless such edits are of course against the relevant TOS so **proceed at your own risk**!  
No maintainer nor contributor will be responsible for any issues encountered as a result of use.

[^1]: cygames has a relatively good track record in leaving non-cheating, non-damaging tools and users alone in my experience. Any possible crackdown is also likely to start with announcements and warnings before bans.

# **Current state**
This project has taken a lot of time and effort that I can't afford to keep providing freely.  
Work is continued, to the degree affordable and with a focus on translations, through the help of monthly supporters. This work is available first to said supporters who make it possible, and later finds its way to the wider community.

This includes:
- New translations for various story contents
- Keeping up with the latest game updates
- (occasional) Patch improvements & QOL
- (occasional) Lyrics translations

Some extra work or benefits, when available, remain only for supporters:
- Polls & requests
- Additional content (pakatube tl, …)
- Translation spotlights; a series of small writeups expanding upon some terms, culture, and translations
- Priority tech support

Finally, some things will continue to be simultaneously updated for everyone:
- Critical bug fixes
- Integration of community translations (when permitted or submitted by the relevant contributor)
- Minor housekeeping
- Community-wide translation progress

All the work that has gone into since 2021 as well as the abilities it provides both to users and community contributors remain available.  
If you'd like to contribute as a supporter, please check the links at the top of this readme or at the right of the page.

# Setting up / Getting started
~~[An alternative guide with images by CryDuringItAll](https://docs.google.com/document/d/1_Ze8oez90d3Ic1rJhbK4F3wWe7hAIB_j2vJFjmcHfkY)~~ Outdated and not recommended anymore but could still be useful for images or extra guides.

## Requirements (get these first!)
1. Install Python 3.11 from the files at the bottom of [this page](https://www.python.org/downloads/release/python-3116/).
    - The defaults should work fine. To customize; you need pip, the py launcher, and tcl/tk. *Do not* select "add to path".
    - [Direct link to download](https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe).
1. Clone or [download a zip](https://github.com/noccu/umamusu-translate/archive/refs/heads/master.zip) (green "code" button) of this project and extract it.
1. Make sure you opened and logged in to the game at least once before.

## Install (do this once)
1. Open the (extracted) folder and double click `install.bat` 
    - This downloads a few technical requirements and sets UmaTL up for use.
1. (Optional, for dialogue) Download all game data [through the game menu](docs/guide_batch_download.jpg)
    - The patch will only edit files existing in your game data. If you don't do this you can simply rerun the dialogue import step below for new content.

### Troubleshooting (help, errors!)
- [Something about building wheels…?](https://github.com/noccu/umamusu-translate/issues/56)
- Errors about "pip not found"?
    - This is uncommon as pip is an integral part of python [Check here](https://pip.pypa.io/en/stable/installation/#ensurepip) for solutions.
    - If you still get errors, delete the .venv folder first.

## Config
The **first time** you run any of the `.bat` files mentioned in the Patching section below, an `umatl.json` file will be created in the folder **and the script will exit without doing anything else**.  
This file can be opened in any text editor and you can change any settings in this config file as you like at any time. Simply run the same .bat file again to have it start patching this first time.

For advanced users: The format of this file is `relative script path (no ext) -> argument -> value`.  
For a list of arguments, run the scripts with -h or check near the bottom of the relevant .py files.  
Some config changes only apply to new files by default. To forcefully update all files, (temporarily) set update to false.

# Patching
The following parts are intended to be used together, and the patch as a whole assumes this is the case.  
However, they can be used independently if so wished.

## UI (menus, buttons, ...)
1. Open the game's *install folder* (where the `Umamusume.exe` is)
1. Copy the **contents** (inside!) of this project's `localify` folder to the *install folder*
1. Download [tlg]'s latest [release zip](https://github.com/MinamiChiwa/Trainers-Legend-G/releases), extract **only the `version.dll`** from it and put that in the game's *install folder*
1. It should look [like this](docs/guide_localify.jpg).

This is a one-time procedure. To update TLG itself simply overwrite the `version.dll` with the new one.

### Troubleshooting
- If you get **errors** when starting game: 
    - Make sure your `version.dll` is not 0kb (it should be ~2MB).
    - [Install vc++ X64](https://learn.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170) ([alterative link](https://github.com/abbodi1406/vcredist)) (you might need the X86 version as well)
- If the game *UI is not translated*:
    - Double check everything is in the right place.
    - Rename the `version.dll` file to `uxtheme.dll`
- If your UI looks the wrong size afterwards:
    - Open the `config.json` you copied and play with the uiScale value (0.8-1.2 usually).

## Skills and other variable text
Change `skill_data` to true in the config if you want to see [the skill's raw requirements and effects](docs/guide_skilldata.png).  
Make sure the game is closed and double click the `mdb import.bat` file.
- The mdb file that this modifies updates regularly (with banners usually), undoing changes. You will need to rerun this .bat.
- There is also [a web version](https://noccu.github.io/umamusume-db-translate/) for mobile or other usecases but it is not maintained anymore.

## Dialogue
Change `skip_mtl` to `false` in the config if you'd like to import machine translations to fill in parts the community hasn't done yet.  
If you use tlg to change fps, add a comma to the above and `"fps": 60` (or whatever your fps is) on a new line under it.
Double click `run.bat` 
- This can take a few minutes because there are many files, especially the first time.
- You can close this at any time and resume later, or play the game while this runs.
- Changes apply without game restart.
- Should be run occasionally to apply updates or translate files you didn't have downloaded yet.
- At the end, it will remove outdated backups. This can take a long time and isn't important so you can close the window at this point.

# Updating
- Double click `run.bat` and/or `mdb import.bat` as required.  
    - `run.bat` also updates the UI-related files **if you've followed the UI step above**.

If you only want to use and update the UI, repeat step 1-2 of the [UI section](#ui-menus-buttons-) or use `py src\manage.py -M`  
If you want to update only the patch itself and not actually apply it, you can use the `update.bat`. This should not usually be needed.

### Troubleshooting
- If you see [commit/merge errors](docs/guide_git_update.png):
    - Open a cmdline in the folder and paste `.mingit\mingw64\bin\git.exe reset --hard`, enter.
    - This will happen if you (or something on your PC) edited any non-config file, including if you're using a test/bugfix file someone sent you.

# Advanced Usage
In general, check out the [scripts](#script-info). You probably also want to `pip install -r src/devreq.txt`
1. **Dialogue**
    - To install specific things, see [id-structure] and use: `py src/import.py -O -g <group> -id <id>`
    - To add additional translations through deepl, or contribute your own, see [translating]
2. **UI**
    - ~~To update yourself when the translations are jumbled, see [here](docs/translating.md#updating)~~
        - Should no longer be needed when using TLG.
3. **Skills and other variable text**: Check the `-h` help for scripts under `src/mdb/`

# Script info

See [data-layout.md](docs/data-layout.md) for an overview of the game's data files and how this repo maps translation files to them.

All scripts are made to be run from the root dir, i.e: `py src/script.py -arg val`  
Target arguments should almost always be given, processing the smallest amount of files you need at a time. See [id-structure].  
For detailed info and args, run a script with the `-h` arg.

script | desc
---|---
filecopy | Simply copies files from the game dir to the project dir for backup.
restore | Restores original game files from earlier backup or cygames servers.
extract | Reads game files and writes relevant data to a local folder, ready to be translated. Creates *Translation Files*.
import | The reverse; loads *Translation Files* and writes them back to game assets for importing into the game.
machinetl + deepl-translator.user.js | In tandem, provide a way to translate *Translation Files* with deepl or fairseq-compatible neural net models. See [details](docs/translating.md#mtl-using-deepl).
names | Translates name/speaker fields in *Translation Files*.
textprocess | Processes dialogue text in *Translation Files* in various ways. Main use is adjusting lengths of lines for game display.
subtransfer | Convert between ASS, SRT or TXT subtitle files and *Translation Files*. A few conventions must be followed, see its help.
edit_story | GUI for editing *Translation Files*, originally started by [KevinVG207](https://github.com/KevinVG207).
manage | Small tool to manage TLG's translation data. Requires use of [tlg].
common/helpers | Not scripts. Hold shared functions and data for other scripts.


# Contribute

To contribute translations, see [translating]  
For dev contributions, open a PR or Issue.  
You can support the project on [Patreon](https://patreon.com/noccu) & [Ko-fi](https://ko-fi.com/noccyu).

# Thanks to

[All translators][tl-progress]  
[Project contributors](https://github.com/noccu/umamusu-translate/graphs/contributors)  
[UnityPy]  
[TLG][tlg]  
[The original umamusume-db-translate](https://github.com/FabulousCupcake/umamusume-db-translate)  
[umamusume-localify]  
[Umamusume Translation Discord](https://discord.gg/HpMRFNvsMv)  
Various dataminers

[UnityPy]: https://github.com/K0lb3/UnityPy
[umamusume-localify]: https://github.com/GEEKiDoS/umamusume-localify
[tlg]: https://github.com/MinamiChiwa/Trainers-Legend-G
[db-translate project]: https://github.com/noccu/umamusume-db-translate

[tl-progress]: docs/tl-progress.md
[translating]: docs/translating.md
[id-structure]: docs/id-structure.md
