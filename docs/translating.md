An overview of the full translation process.

For [existing content](translations/) you only wish to translate, TLC, or edit, skip to [Translating](#Translating).  
**For details on how github and git work, there are good guides and docs to be found through any search engine. Please refer to those. They're too complex to explain here or for me to help out with.**  
I also suggest you look over all of the process before starting.

# Prerequisites
- If you haven't read the main [readme](../README.md), please check and follow that first.
- Open a shell in the project root (the 'base' `umamusu-translate` folder)
    - tip: type cmd in explorer's address bar on windows when in said folder
- Install additional  dependencies: `py -m pip install -r src\devreq.txt`
- (info) Check [id-structure.md](id-structure.md) for help choosing your *targets*.
    - All scripts take the following target arguments: `-g <group> -id <id> (-idx <idx>)`
    - To know other options use `-h`
- (optional) Recommended for easy updates: [Git](https://git-scm.com/downloads) and optionally one of its GUI clients.

# Extracting text
- Run `py src/extract.py -g <group> etc…` with your targets.
- Files will be created in the [translations folder](../translations/)

# Translating
## Manual
Run `py src/names.py <targets>` to translate many `enName` fields automatically. (see [text processing](#further-processing))  
Run `py src/story_editor.py <targets>` to start the GUI story editor. The textbox is sized close to the game's useful text display area, so you can use it for reference.
Text duration is automatically adjusted and doesn't usually need to be changed, but you can edit the base value if desired.
Some files with complex choices can have multiple paths and groups of text, make sure to check the block list.
[Unity Rich Text](https://docs.unity3d.com/Packages/com.unity.ugui@1.0/manual/StyledText.html) is supported but don't use it for global markup like making all the text smaller, but sparingly where needed.

You can also open the files in a text editor or edit existing ones on github and write the translations in the provided `enText` or `enName` fields.
If you don't want to care about line breaks, [see below](#further-processing) for a script which automatically line breaks text to fit a given length.  
> "jpText": "日本語",  
> "enText": "\<**tl goes here**\>",

**Don't change anything else. It's there so text can be put back in the right place.**   

If you want to add line breaks yourself, leave a space before the `\n` so it won't concatenate words together in the log view, which breaks differently and automatically.
Without the `-nl` flag, [text processing](#further-processing) will not touch line breaks present as long as all lines fit the length constraints.
You can also add a `skip` key to any block to have the text processing completely ignore it, for the very occasional special case:  
> "enText": "\<**tl goes here**\>",  
> "skip": true,

## MTL using DeepL
- Install the [deepl-translator.user.js](https://cdn.jsdelivr.net/gh/noccu/umamusu-translate@master/src/deepl-translator.user.js) script in your browser
    - This requires a userscript manager with menu support, like [Violentmonkey](https://violentmonkey.github.io/)
- Run `py src\machinetl.py` with any options you want (refer to main readme)
    - This script automatically uses `textprocess.py` and accepts most of the same arguments.
- Navigate your browser to [deepl's site](https://www.deepl.com/en/translator)
- Open the userscript menu and click `Connect WebSocket`
- If all is well translation will automatically start and the python script will exit when done
    - This will take some time. Press ctrl+c in your terminal to force quit. Progress will be saved per file.

# Further processing    
**Remember to provide targets (likely those you used for extract) or you will process all the files!**
- `py src\textprocess.py` to apply automatic formatting and edits.
    - This is run by the translation script (if you used that), but you can rerun it with custom settings if you like.
    - This uses the [replacer.json](src/data/replacer.json) file. You can add your own entries here, useful for names in particular.
        - If you're doing machine translation, add `-rep all` to make a bit more aggressive edits.
- `py src\names.py -n <path/to/db-translate/data/uma-name.csv>` to translate many names automatically
    - The csv file is from the db-translate project. Download it [here](https://github.com/noccu/umamusume-db-translate/blob/playtest/src/data/uma-name.csv) if you don't have it and point the `-n` argument to its location.
        - The file will be auto-detected if `db-translate` is in the same parent directory as `umamusu-translate`.
    - You can add other possibly reoccurring names to the `names.json` file.
    - Translates the namecards, not the names in dialogue!

# Finishing up
Use the `import.py` script to get your translations in the game. See the main readme or the scripts themselves for details.

# Translating UI
The UI translations work by mapping hashes to text strings.
Some updates change the hashes, causing the translations to be jumbled.
[Here](#updating)'s how to fix this yourself if you don't want to wait on an update.

## Translating
1. Open the `config.json` file in your game folder (`DMMgames\Umamusume\config.json`)
1. Change the following
    > "enableLogger": false,  
    > "dumpStaticEntries": false,
    > ⇩⇩⇩  
    > "enableLogger": true,  
    > "dumpStaticEntries": true,
1. Delete `dump.txt` if it exists in the same (game) folder
1. (re)Start the game
1. Move through the screens you wish to translate
1. Open a cmd prompt to run the following
1. `py src/manage.py -new -add -src`
   - If autodetect fails, point it to the file from step 3 `-src …/dump.txt`
   - This will update `src/data/static_dump.json` with any new hash to JP text mappings, and add those JP text entries to `translations/localify/ui.json`.
1. Open the `translations/localify/ui.json` file, search for your text, translate it, and save the file:  
   "日本語": "**tl goes here**"
1. `py src/manage.py -upd`
1. The UI translation files in the `localify` folder should now be updated and can be copied over to your game folder
    - Basically follow [the usual step](../README.md#basic-usage) or simply run `py src/manage.py -M`
1. Revert the changes from step 2.
1. If you wish to contribute (especially through github), run `py src/manage.py -clean both` first

## Updating
1. Follow [translating](#translating) steps 1-4 above
1. Navigate through a few screens, especially those that cause loading or had jumbled text (the more the better)  
   Useful rotation is circle -> uma list -> race/practice -> training if one is open
1. Open a cmd prompt to run the following
1. `py src/manage.py -I -O -src`  
1. Same as steps 9-11 above

# Sharing
If you used git; commit your changes (in organized chunks) and make a Pull Request once all done.  
If not; upload your new files somewhere and open an Issue. ~~Or DM me on discord.~~
