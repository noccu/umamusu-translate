An overview of the full translation process.

For [existing content](translations/) you only wish to translate, TLC, or edit, skip to [Translating](#Translating).  
**For details on how github and git work, there are good guides and docs to be found through any search engine. Please refer to those. They're too complex to explain here or for me to help out with.**  
I also suggest you look over all of the process before starting.

# Prerequisites
Needed:
- If you haven't read the main [readme](readme.md), please check and follow that first.
- Install additional  dependencies
    - From project root: `py -m pip install -r src\devreqs.txt`
-  If you want to contribute through github: fork the project and clone that fork to work in

Recommended for easy updates or contributing:    
- [Git](https://git-scm.com/downloads) or a GUI client like [GitHub Desktop](https://desktop.github.com/)
    - git comes with git-gui so you don't *need* a separate client

# Extracting text
- Open a shell in the project root (the `umamusu-translate` folder)
    - tip: type cmd in explorer's address bar on windows when in said folder
- Run `py src/extract.py -g <group> -id <id>`
    - See [id-structure.md](id-structure.md) for help choosing what to extract
- Files will be created in the [translations folder](translations/)

# Translating
## Manual
Open the files in a text editor or edit them on github and write the translations in the provided enText or enName fields. There is a script for names which you probably want to run first for QoL, [see below](#further-processing). BlockIdx is sequential and can help you follow a route through choices.

> "jpText": "日本語",  
> "enText": "\<**tl goes here**\>",

**Don't change anything else. It's there so text can be put back in the right place.**   
[Unity Rich Text](https://docs.unity3d.com/Packages/com.unity.ugui@1.0/manual/StyledText.html) is supported but I advice against using it for global markup like making all the text smaller. Use it sparingly where needed.

> For those unfamiliar; `\n` and `\r\n` are line breaks. Both essentially mean the same thing.  
> As you can see, the game uses both (\r\n is old, they changed to \n). It doesn't make a difference so just use `\n`.  
> If you see `\\n` please use that in your english text as well. It means the game expects to see the `\n` literally in the text, rather than it being turned into a linebreak immediately.  


## MTL using DeepL
- Install the [deepl-translator.user.js](https://cdn.jsdelivr.net/gh/noccu/umamusu-translate@master/src/deepl-translator.user.js) script in your browser
    - This requires a userscript manager with menu support, like [Violentmonkey](https://violentmonkey.github.io/)
- Run `py src\machinetl.py` with any options you want (refer to main readme)
    - This script automatically uses `textprocess.py` and accepts most of the same arguments. (-ll is useful)
- Navigate your browser to [deepl's site](https://www.deepl.com/en/translator)
- Open the userscript menu and click `Connect WebSocket`
- If all is well translation will automatically start and the python script will exit when done
    - This will take some time. Press ctrl+c in your terminal to force quit. Progress will be saved per file.

## Further processing    
- When done with either method, run any extra processing on the file. **Remember to use the -g and -id options (likely those you used for extract) or you will process all the files!**
    - `py src\textprocess.py` to apply some automatic formatting (line length in particular) and edits
        - This is run by the translation script (if you used that), but you can rerun it with custom settings if you like
        - Recommended line length for vertical screens is 45, and for horizontal 65.
        - This uses the [replacer.json](src/data/replacer.json) file. You can add your own entries here, useful for names in particular.
    - `py src\names.py -n <path/to/db-translate/data/uma-name.csv>` to translate many names automatically
        - This file is from the db-translate project. Download it [here](https://github.com/noccu/umamusume-db-translate/blob/playtest/src/data/uma-name.csv) if you don't have it and point the -n argument to its location.
        - Translates the namecards, not the dialogue!

## Finishing up
Use the `import.py` script to get your translations in the game. See the main readme or the scripts themselves for details.

## Translating UI
See [here](updating-ui.md#translating)

# Sharing
If you used git; commit your changes (in organized chunks) and make a Pull Request once all done.  
If not; upload your new files somewhere and open an Issue. ~~Or DM me on discord.~~
