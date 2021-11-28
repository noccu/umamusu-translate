This project aims to translate UmaMusume through Unity asset edits.

# Disclaimer

This tool collection only changes text to translate it and it is my believe this is harmless and unlikely to be an issue.  
Nonetheless such edits are of course againt cygames/Umamusu TOS so proceed at your own risk!  
~~cygames has a relatively good track record in leaving non-cheating, non-damaging tools and users alone in my experience.~~

# Usage 

**If you just want to use the translations in your game with minimal fuss skip step 3, 4, 6 and use -O as arg in step 5: `import.py -O`**

1. Install python 3.6+ and [UnityPy][]
1. (Optional but recommended) Download all game data through the game menu
1. `python extract.py <args>`
1. Add translations to files in `translations/`
1. `python import.py <args>`
1. Dialogue: Copy `dat` folder to game datafolder and overwrite (Usually `C:\Users\<name>\AppData\LocalLow\Cygames\umamusume`)
1. UI: Copy the [localify folder](localify) to your Umamusu install dir (where the `Umamusume.exe` and *[localify][umamusume-localify]'s `version.dll`* are, `C:\DMM\Umamusu` or something similar, probably)

A premade archive might be released every so often. Ignore everything but step 6-7 then.  
Both scripts take similar arguments, given as `-arg <opt>`:

arg|desc
---|---
g | extract specific group
id | extract specific id
l | limit processing to given number of files
O | `extract.py`: overwrite files in extract folder `import.py`: (over)write directly to game dir instead of `dat/`
src | define umamusu game dir (defaults to the usual location in `LocalLow`)
dst | `import.py`: define root dir to save modified asset files in (defaults to `dat/`)

> for g and id see [id-structure.md](id-structure.md)

# Script info

All scripts are made to be run from the root dir, i.e: `py src/script.py -opt val`  
Arguments can be given to all and it is recommended you do so, processing the smallest amount of files you're comfortable with at a time.  
For arg info run a script with the `-h` arg or just look at the code. Most are very similar.

## Main / Stories

script | desc
---|---
filecopy | Simply copies files from the game dir to the project dir for backup. These will then be used by some other scripts for safety.
restore-files | Downloads fully fresh files from cygames servers, in case of mess ups
extract | Loads game data and writes relevant data to a local folder, ready to be translated. Creates *Translation Files*
import | The reverse; loads *Translation Files* and writes them back to game assets for importing into the game
machinetl + deepl-translator.user.js | In tandem, provide a way to translate *Translation Files* with deepl. Install the userscript in your browser. Run the python file first, then go to the deepl site and use your userscript manager's menu to connect and wait until python exits. This userscript setup is temporary (famous last words)
names | Simply translates names in *Translation Files* using data from the [db-translate project](https://github.com/noccu/umamusume-db-translate)
textprocess | Processes dialogue text in *Translation Files* in various ways. Most immediate manual use is adjusting lengths of lines for newline splits.
common | Not a script. Is used by the other files and holds shared functions and data.

## Others
script | desc
---|---
static/manage | Small tool to manage localify's data for translating static strings. Requires use of [umamusume-localify][]

# Contribute

To contribute translations, see [translating.md](translating.md)  
For dev contributions, open a PR or Issue.  
**Both are extremely welcome!**

# Thanks to

[UnityPy][]  
[The original umamusume-db-translate](https://github.com/FabulousCupcake/umamusume-db-translate)  
[umamusume-localify][]  
[Unofficial Umamusume Discord server](https://discord.gg/umamusume)

[UnityPy]: https://github.com/K0lb3/UnityPy
[umamusume-localify]: https://github.com/GEEKiDoS/umamusume-localify
