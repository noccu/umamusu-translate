This project is a toolset to translate *Uma Musume Pretty Derby* to English. Includes a patch function using these tools.  
It accomplishes this by modifying the master.mdb file and Unity assets, aided additionally with dll hijacking through [TLG].

Translation progress and credits can be checked in [tl-progress]. Guides can be found below.  
For troubleshooting, please open an issue or ask in the [Umamusume Translation Discord][].

This is based on the DMM version of the game and *should* work on linux too.  
Please consider [supporting the project](https://ko-fi.com/noccyu) and its contributors.

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
Provides text strings and related tools for UI translation using [tlg].

Included translations: [tl-progress]  
Toolset: [scripts](#script-info)

# Disclaimer

This toolset only changes text to translate it and it is *my belief* this is harmless and unlikely to be an issue. [^1]  
**Nonetheless such edits are of course against cygames/Umamusu TOS so proceed at your own risk!**

[^1]: cygames has a relatively good track record in leaving non-cheating, non-damaging tools and users alone in my experience. any possible crackdown is also likely to start with announcements and warnings before bans.

# Install 
Make sure you satisfied the *requirements* first, then follow the steps in *usage*.

## Requirements
1. Install [Python](https://www.python.org/downloads/) 3.9+
    - During install, check the `Add to PATH` option.
1. Pull or download this project
1. Open the (extracted) folder and double click `install.bat` (This downloads the needed python libs)
1. (Optional but recommended *for dialogue*) Download all game data [through the game menu](guide_batch_download.jpg)
    - The patch will only edit files existing in your game data. You can simply rerun the dialogue import below for new content.

## Basic Usage
Each part is separate and can be used independently if so wished.

1. **UI** (menus, buttons, ...): Open the game's *install folder* (where the `Umamusume.exe` is)
    1. Copy the **contents** of this project's `localify` folder to the *install folder*
    1. Download [tlg]'s latest [release zip](https://github.com/MinamiChiwa/Trainers-Legend-G/releases), extract **only the `version.dll`** from it and put that in the game's *install folder*
        - *0xc000012f* error when starting game: [Install vc++ X64](https://learn.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170) ([alterative link](https://github.com/abbodi1406/vcredist))
        - If the game *won't start* or the *UI is not translated*, try renaming the `version.dll` file to `uxtheme.dll` (*errors* mean the issue is elsewhere and this will not help)
    1. It should look [like this](guide_localify.jpg).
1. **Skills and other variable text**: Run either of the `mdb import.bat` files
    - `(replace skill desc with data).bat` will use [the skill's raw requirements and effects](guide_skilldata.png).
    - The mdb file that this modifies updates often, you will need to rerun this .bat every time it does. Usually when there is an in-game update.
    - Requires restarting the game after applying.
    - There is also [a web version](https://noccu.github.io/umamusume-db-translate/) for mobile or other usecases.
1. **Dialogue**: double click `run.bat` 
    - This can take a long time (few hours) because there are many files.
    - You can close this at any time and resume later, or play the game while this runs.

## Updating
1. Pull or download the project again and overwrite
    - Any files you've added yourself through the deepl integration should stay intact, or at worst be overridden with the same (deepl) or better (manual translation) versions. If you've made your own edits to anything though, those would be lost! You could keep a backup of any edits at the moment you make them, or try picking up git or other version control software. Or best of all, please contribute them so everybody can enjoy them!
1. Double click `run.bat` and/or `mdb*.bat` as required.
    - `run.bat` also updates the UI-related files after you've followed the UI step above.

## Advanced Usage
In general, check out the [scripts](#script-info). You probably also want to `pip install -r src/devreq.txt`
1. **Dialogue**
    - To install specific things, see [id-structure.md](id-structure.md) and use: `py src/import.py -O -g <group> -id <id>`
    - To add additional translations through deepl, or contribute your own, see [translating.md](translating.md)
2. **UI**
    - To update yourself when the translations are jumbled, see [here](translating.md#updating)
3. **Skills and other variable text**: See the [db-translate project]

# Script info

See [data-layout.md](data-layout.md) for an overview of the game's data files and how this repo maps translation files to them.

All scripts are made to be run from the root dir, i.e: `py src/script.py -arg val`  
Arguments can be given to all and it is recommended you do so, processing the smallest amount of files you're comfortable with at a time.  
For detailed info and args, run a script with the `-h` arg. See also [id-structure.md](id-structure.md) for `g`, `id`, and `idx`.

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
common/helpers | Not scripts. Hold shared functions and data for other scripts.


# Contribute

To contribute translations, see [translating.md](translating.md) (deepl dumps are accepted!)  
For dev contributions, open a PR or Issue.  
**Both are extremely welcome!**

# Thanks to

[All the translators][tl-progress]  
[UnityPy][]  
[tlg]  
[The original umamusume-db-translate](https://github.com/FabulousCupcake/umamusume-db-translate)  
[umamusume-localify][]  
[Umamusume Translation Discord][]  
[Unofficial Umamusume Discord](https://discord.gg/umamusume)  

[UnityPy]: https://github.com/K0lb3/UnityPy
[umamusume-localify]: https://github.com/GEEKiDoS/umamusume-localify
[tlg]: https://github.com/MinamiChiwa/Trainers-Legend-G
[db-translate project]: https://github.com/noccu/umamusume-db-translate
[Umamusume Translation Discord]: https://discord.gg/HpMRFNvsMv

[tl-progress]: tl-progress.md
