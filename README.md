This project aims to translate *Uma Musume Pretty Derby* through (mainly) Unity asset edits.  
The intent is to be an all-in-one toolset/patch but right now it is focused on any dialogues with a few extras.  

Translation progress and credits can be checked in [tl-progress]. Guides can be found below.  
For troubleshooting, please open an issue or ask in the [translation discord](https://discord.gg/HpMRFNvsMv).

This is based on the DMM version of the game. If you can figure out how to run it on other versions, it should work with some edits, but no support is provided right now.  
Please consider [supporting the project](https://ko-fi.com/noccyu).  

# Features
Translates (or *can* translate):
- Character stories
- Main & Event stories
    - Race segments
    - Event prologues
- Training stories
- Home screen interactions
- Lyrics
- Planned: images

Deepl/fairseq integration for automatic machine translation.  
Provides text strings and related tools for UI translation using [umamusume-localify].

Included translations: [tl-progress]  
Toolset: [scripts](#script-info)

# Disclaimer

This tool collection only changes text to translate it and it is *my belief* this is harmless and unlikely to be an issue. [^1]  
**Nonetheless such edits are of course against cygames/Umamusu TOS so proceed at your own risk!**

[^1]: cygames has a relatively good track record in leaving non-cheating, non-damaging tools and users alone in my experience. any possible crackdown is also likely to start with announcements and warnings before bans.

# Install 
### Requirements
1. Install [Python](https://www.python.org/downloads/) 3.9+
    - During install, check the `Add to PATH` option.
1. Download this project
1. Open the (extracted) folder and double click `install.bat`
1. (Optional but recommended) Download all game data through the game menu
    - Only files existing in your game data will be updated. You can simply rerun the import for new content.

### Basic Usage
1. **Dialogue**: double click `run.bat` 
1. **UI**: Open the game's *install folder* (where the `Umamusume.exe` is)
    1. Download [localify][umamusume-localify]'s `release.7z` from [here](https://github.com/GEEKiDoS/umamusume-localify/releases/tag/test6) and extract the `version.dll` inside to the *install folder*
    1. Copy the *contents* of the [localify folder](localify) to the *install folder*
        - If it doesn't work when you start the game, try renaming the `version.dll` file to `uxtheme.dll`
        - In rare cases when a story overlay pops up in the main menus, your UI may blur and get stuck that way. Temporarily remove the dll and restart the game to do the action. (may only affect uxtheme.dll naming?)
1. **Skills and other variable text**: See the [db-translate project] and follow its guide.

### Updating
1. Download the project again and overwrite
    - Any files you've added yourself through the deepl integration should stay intact, or at worst be overridden with the same (deepl) or better (manual translation) versions. If you've made your own edits to anything though, those would be lost! You could keep a backup of any edits at the moment you make them, or try picking up git or other version control software.
1. Double click `run.bat` 

### Advanced Usage
In general, check out the [scripts](#script-info).
1. **Dialogue**
    - To install specific things, see [id-structure.md](id-structure.md) and use: `py src/import.py -O -g <group> -id <id>`
    - To add additional translations through deepl, or contribute your own, see [translating.md](translating.md)
1. **UI**
    - To update yourself when the translations are jumbled, see [here](updating-ui.md)
1. **Skills and other variable text**: See the [db-translate project]

# Script info

All scripts are made to be run from the root dir, i.e: `py src/script.py -arg val`  
Arguments can be given to all and it is recommended you do so, processing the smallest amount of files you're comfortable with at a time.  
For detailed info and args, run a script with the `-h` arg. See also [id-structure.md]() for `g`, `id`, and `idx`.

script | desc
---|---
filecopy | Simply copies files from the game dir to the project dir for backup.
restore | Restores original game files from earlier backup or cygames servers.
extract | Reads game files and writes relevant data to a local folder, ready to be translated. Creates *Translation Files*.
import | The reverse; loads *Translation Files* and writes them back to game assets for importing into the game.
machinetl + deepl-translator.user.js | In tandem, provide a way to translate *Translation Files* with deepl or fairseq-compatible trained neural net models. See [details](translating.md#mtl-using-deepl).
names | Translates name fields in *Translation Files* using data from the [db-translate project][].
textprocess | Processes dialogue text in *Translation Files* in various ways. Main use is adjusting lengths of lines for game display.
subtransfer | Imports ASS, SRT or TXT subtitle files into *Translation Files*. A few conventions must be followed, see -h.
edit_story | GUI for editing *Translation Files* by [KevinVG207](https://github.com/KevinVG207).
manage | Small tool to manage localify's data for translating static strings. Requires use of [umamusume-localify][].
common/helpers | Not scripts. Holds shared functions and data for other scripts.


# Contribute

To contribute translations, see [translating.md](translating.md) (deepl dumps are accepted!)  
For dev contributions, open a PR or Issue.  
**Both are extremely welcome!**

# Thanks to

[UnityPy][]  
[The original umamusume-db-translate](https://github.com/FabulousCupcake/umamusume-db-translate)  
[umamusume-localify][]  
[Unofficial Umamusume Discord server](https://discord.gg/umamusume)  
[All the translators][tl-progress]

[UnityPy]: https://github.com/K0lb3/UnityPy
[umamusume-localify]: https://github.com/GEEKiDoS/umamusume-localify
[db-translate project]: https://github.com/noccu/umamusume-db-translate

[tl-progress]: tl-progress.md