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

- Open a shell in the project root (the `umamusu-story-translate` folder)
    - protip: type cmd in explorer's address bar on windows
- Run `python extract.py -g <group> -id <id>`
    - See [id-structure.md](id-structure.md) for help choosing what to extract
- Files will be created in the [translations folder](translations/)

# Translating

Simply open the files in a text editor or edit them on github and write the translations in the provided enText or enName fields. BlockIdx is sequential and can help you follow a route through choices

**Don't change anything else. It's there so text can be put back in the right place.**  
**Please do not add global size markup to every line, but only when needed. Global size will be done in code if required later.**

`\n` and `\r\n` are line breaks. Both essentially mean the same thing.
As you can see, the game uses both. I don't know what difference it makes in game, if any.  
[Unity Rich Text](https://docs.unity3d.com/Packages/com.unity.ugui@1.0/manual/StyledText.html) should be supported.

> "jpText": "日本語",  
> "enText": "\<**tl goes here**\>",

TODO: Integrate machine-tl. 

# Sharing

If you used git; commit your changes (in organized chunks preferably) and make a Pull Request once all done.  
If not; upload your new files somewhere and open an Issue.
