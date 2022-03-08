The UI translations work by mapping hashes to text strings.
Some updates change the hashes, causing the translations to be jumbled.
Here's how to fix this yourself if you don't want to wait on an update:

## Updating

1. Open the `config.json` file in your game folder (`DMMgames\Umamusume\config.json`)
1. Change the following
    > "enableLogger": false,  
    > "dumpStaticEntries": false,  
    > "dicts": ["localized_data/static.json"] (or whatever it says between the [] here)
    
    to
    
    > "enableLogger": true,  
    > "dumpStaticEntries": true,  
    > "dicts": []
1. Delete `dump.txt` if it exists in the same (game) folder. (Remember this file and where it is, you'll need it in a bit.)
1. Start the game
1. Navigate through a few screens, especially those that cause loading  
   Useful rotation is circle -> uma list -> race/practice -> training if one is open
1. Close the game and open a cmd prompt to run the following
1. `py -m src.static.manage -I -O -src path/to/dump.txt` (see step 3 and point it to that file)  
   `py -m src.static.manage -upd`
1. The UI translation file in the `localify` folder should now be updated and can be copied over to your game folder
    - Basically follow [the usual step](README.md#basic-usage)
1. Revert the changes from step 2.

## Translating

Based on the previous steps
1. Follow steps 1-4 above
1. For step 5 move through the screens you wish to translate
1. Close the game and open a cmd prompt to run the following
1. `py -m src.static.manage -new -add -src path/to/dump.txt` (see step 1+3 [above](#updating) and point it to that file)  
1. Open the `src/static/data/static_en.json` file, search for your text, translate it, and save the file:  
   "日本語": "**tl goes here**"
1. `py -m src.static.manage -upd`
1. See steps 8-9 above.
1. If you wish to contribute (especially on github), run `py -m src.static.manage -clean both` first