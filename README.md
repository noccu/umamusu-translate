[![Support me on Patreon](https://img.shields.io/badge/dynamic/json?color=%23ff424d&label=Patreon&query=data.attributes.patron_count&suffix=%20trainers&url=https%3A%2F%2Fwww.patreon.com%2Fapi%2Fcampaigns%2F2559100&style=flat-square&logo=patreon&logoColor=%23ff424d)](https://patreon.com/noccu)
[![Support me on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-%2300aff1?logo=kofi&logoColor=%2300aff1)](https://ko-fi.com/noccyu)
[![Discord](https://img.shields.io/discord/980222697151807488?logo=discord&logoColor=4bba35&label=Discord)](https://discord.gg/xBMgwh6hHY)

This project is a toolset to translate *Uma Musume Pretty Derby* to English. A few included scripts also let it function as a game patch using these tools.  
It accomplishes this by modifying the master.mdb file and Unity assets, aided additionally with dll hijacking through [TLG].

> [!CAUTION]
> For those looking to play the game translated:  
> UmaTL translations have transitioned to [a separate translation repository](https://github.com/UmaTL/hachimi-tl-en), in a format useable by Hachimi. Check out the install instructions on that page instead!  
> Development of translation tools will continue, patching functionality will not.

> [!TIP]
> This project takes a lot of time and effort, the vast majority of which my own.  
> Please consider [supporting](#supporting-the-project) and receive some small bonuses.

**[Translation progress and credits][tl-progress].**  
If you encounter problems, check the troubleshooting section with each guide step first. Open an issue or ask in the Discord server if this doesn't solve it.

UmaTL and the patching functionality is aimed at the DMM (Windows) version of the game. The toolset itself *should* work on linux and mac too, with some limitations.

# Features
Supports translating:
- Tutorials
- Character stories
- Main & Event stories, incl. race segments and event prologues
- Special events
- Training & Scenario stories
- Home interactions (lobby characters)
- System text, which is mostly speech balloons (home screen, training, …)
- Lyrics in lives/concerts
- Most of the UI through [tlg]
- Skills, names, missions, and other such "dynamic" texts
- Images through [tlg]

Other:
- Deepl/fairseq integration for automatic machine translation
- Story editor for easy translating with audio support (or simply reading along without patching)
- Support for syncing with arbitrary framerates
- Adjustable reading speed
- Basic file/asset management tools (wip)
- Auto-updates

Included translations & credits: [tl-progress]  
Toolset info: [scripts](#script-info)

# Supporting the project
This project has taken a lot of time and effort since 2021 that I can't afford to keep providing freely.  
Work is continued, to the degree affordable and with a focus on translations, through the help of donations and supporters.  
Monthly supporters gain the following benefits (based on tier & when available):
- Polls
- Translation notes (expanding upon some terms, culture, and translations)

If you'd like to donate or contribute as a supporter, please check the links at the top of this readme or at the right of the page.

# Disclaimer
UmaTL is not affiliated with Cygames and is purely a fan-community effort.  
Assets are edited only for the purpose of translation and it is *the maintainer's belief* this is harmless and unlikely to be an issue. [^1]  
Nonetheless, such edits are against the relevant TOS so **proceed at your own risk**!  
No maintainer nor contributor will be responsible for any issues encountered as a result of use.

[^1]: cygames has a relatively good track record in leaving non-cheating, non-damaging tools and users alone in my experience. Any possible crackdown is also likely to start with announcements and warnings before bans.

# Install
1. Download & install Python 3.11 from the files at the bottom of [this page](https://www.python.org/downloads/release/python-3116/).
    - The defaults should work fine. If you want to customize; you need pip, the py launcher, and tcl/tk. *Do not* select "add to path" if you don't understand it.
    - [Direct link to download](https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe).
1. Make sure you opened and logged in to the game at least once before.
1. Download the [install script from releases](../../releases/latest) and run it (double click).
    - This creates a new folder named "UmaTL" in the folder that you save the script to. 
    - You can move that folder later if you wish. The script can be deleted.

~~[An alternative guide with images by CryDuringItAll](https://docs.google.com/document/d/1_Ze8oez90d3Ic1rJhbK4F3wWe7hAIB_j2vJFjmcHfkY)~~ Very outdated but could still be useful for some extra info.

### Troubleshooting (help, errors!)
- [Something about building wheels…?](https://github.com/noccu/umamusu-translate/issues/56)
- Errors about "pip not found"?
    - This is uncommon as pip is an integral part of python. [Check here](https://pip.pypa.io/en/stable/installation/#ensurepip) for solutions.
    - If you still get errors, delete the .venv folder first.

## Config
The `umatl.json` file, created in the folder upon install, holds user config for the various tools used by the patch.  
This file can be opened in any text editor and you can change or add any settings in it as you like at any time.  
Some config changes only apply to new/updated files by default. To forcefully update all files, (temporarily) set `import -> update` to false.

For advanced users: The format of this file is `relative script path (no ext) -> argument -> value`.  
For a list of arguments, run the scripts with -h or check near the bottom of the relevant .py files.  

# Patching
The patching process consists of three parts that are intended to be used together.
The patch as a whole assume this is the case and works optimally that way.
However, they can be used independently if so wished, with relatively minor downsides.

Double click `patch.bat` and choose which parts to patch.  
**Patching UI translations requires that you chose to install TLG**.  
You can run this at any time to patch other parts or apply new translations.
- This can take a few minutes because there are many files, especially the first time.


UmaTL will automatically update to its newest version before patching.  
If you only want to update UmaTL without applying the patch, you can run `update.bat`. This should not usually be needed.

More info (read first!) and troubleshooting for each part below.

## UI (menus, buttons, ...)
TLG itself can be updated by running the install script again from UmaTL's parent folder and choosing update mode, or by simply overwriting its 2 `.dll` files with the new one manually.

### Troubleshooting
- If you get **errors** when starting the game:
    - Make sure your `version.dll` is not 0kb (it should be ~7MB).
    - [Install vc++ X64](https://learn.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170) ([alterative link](https://github.com/abbodi1406/vcredist)) (you might need the X86 version as well)
- If the game UI is **not translated**:
    - Double check everything is in the right place.
    - Rename the `version.dll` file to `xinput1_3.dll` or `umpdc.dll`
- If your UI looks the wrong size afterwards:
    - Open the `config.json` in Uma's install dir and play with the uiScale value (0.8-1.2 usually).

## Skills and other variable text
Change `skill_data` to true in the config if you want to see [the skill's raw requirements and effects](docs/guide_skilldata.png).  
**Make sure the game is closed when patching mdb.**
- The mdb file that this modifies updates regularly (with banners usually), undoing changes. You will need to rerun this .bat.
- There is also [a web version](https://noccu.github.io/umamusume-db-translate/) for mobile or other usecases but it is not maintained anymore.

## Dialogue
Change `skip_mtl` to `false` in the config if you'd like to import machine translations to fill in parts the community hasn't done yet. Note UmaTL itself no longer updates MTL.  
If you use tlg to change fps, follow the cfg file's format to add `"fps": 60` (or whatever your fps is) on a new line under it.  
- You can close this at any time and resume later, or play the game while this runs.
- Changes apply without game restart.
- At the end, it will remove outdated backups. This can take a long time and isn't important so you can close the window at this point.

### Troubleshooting
- If you see [commit/merge errors](docs/guide_git_update.png):
    - Open a cmdline in the folder and paste `.mingit\mingw64\bin\git.exe reset --hard`, enter.
    - This will happen if you (or something on your PC) edited any non-config file, including if you're using a test/bugfix file someone sent you.
- If that doesn't help, reinstall UmaTL.

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
[TLG][tlg] & [umamusume-localify]  
[The original umamusume-db-translate](https://github.com/FabulousCupcake/umamusume-db-translate)  
[Umamusume Translation Discord](https://discord.gg/HpMRFNvsMv)  
Various dataminers  
UmaTL's gracious supporters

[UnityPy]: https://github.com/K0lb3/UnityPy
[umamusume-localify]: https://github.com/GEEKiDoS/umamusume-localify
[tlg]: https://github.com/MinamiChiwa/Trainers-Legend-G
[db-translate project]: https://github.com/noccu/umamusume-db-translate

<!-- [tl-progress]: docs/tl-progress.md -->
[tl-progress]: https://github.com/UmaTL/hachimi-tl-en/wiki/Translation-Progress
[translating]: docs/translating.md
[id-structure]: docs/id-structure.md
