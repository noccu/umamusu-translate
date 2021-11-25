This assumes you want to translate new content.  
If the content is already present in [translations](translations/) or you are TLCing/editing, [skip to Translating](#Translating)

# Prerequisites

Needed:
- UmaMusu (DMM)
    - Possibly works on other versions but you're on your own then...
- All game data downloaded (likely)
- Install [python](https://www.python.org/downloads/) 3.6+
- Install dependencies
    - From project root: `pip install -r src\requirements.txt`

Recommended:    
- [Git](https://git-scm.com/downloads) or a GUI client like [GitHub Desktop](https://desktop.github.com/)
    - git comes with git-gui
    - fork the project on github and clone that fork to work in

# Extracting text

- Open a shell in the project root (the `umamusu-translate` folder)
    - tip: type cmd in explorer's address bar on windows
- Run `python src/extract.py -g <group> -id <id>`
    - See [id-structure.md](id-structure.md) for help choosing what to extract
- Files will be created in the [translations folder](translations/)

# Translating
## Manual
Simply open the files in a text editor or edit them on github and write the translations in the provided enText or enName fields. There is a script for names which you probably want to run first for QoL, [see below](#further-processing). BlockIdx is sequential and can help you follow a route through choices

**Don't change anything else. It's there so text can be put back in the right place.**  (Except title, you can translate that for completion if you want but it isn't currently used.)

`\n` and `\r\n` are line breaks. Both essentially mean the same thing.
As you can see, the game uses both. It doesn't seem to make a difference so just use \n.  
[Unity Rich Text](https://docs.unity3d.com/Packages/com.unity.ugui@1.0/manual/StyledText.html) should be supported but I advice against adding custom markup at the current time.

> "jpText": "日本語",  
> "enText": "\<**tl goes here**\>",

## MTL using DeepL

- Install the [deepl-translator.user.js](https://cdn.jsdelivr.net/gh/noccu/umamusu-translate@master/src/deepl-translator.user.js) script in your browser
    - This requires a userscript manager with menu support, like [Violentmonkey](https://violentmonkey.github.io/)
- Run `python src\machinetl.py` with any options you want (refer to main readme)
- Navigate your browser to [deepl's site](https://www.deepl.com/en/translator)
- Open the userscript menu and click `Connect WebSocket`
- If all is well translation will automatically start and the python script will exit when done
    - This will take some time

## Further processing    
- When done with either method, run any extra processing on the file
    - `python src\textprocess.py` to apply some automatic formatting (line length in particular) and edits
        - This is run by the translation script (if you used that), but you can rerun it with custom settings if you like
    - `python src\names.py -n <path/to/db-translate/data/uma-name.csv>` to translate many names automatically

## Finishing up

Use the import script to get your translations in the game. See the main readme or the scripts themselves for details.

# Sharing

If you used git; commit your changes (in organized chunks) and make a Pull Request once all done.  
If not; upload your new files somewhere and open an Issue. ~~Or DM me on discord.~~
