This project aims to translate UmaMusume through Unity asset edits.

# Usage 

> Install python 3.6+ and UnityPy  
> Probably download all game data through the game menu...  
> `extract.py`  
> Add translations to files in `translations/`  
> `import.py`  
> Copy `dat` folder to game datafolder and overwrite (Usually `C:\Users\<name>\AppData\LocalLow\Cygames\umamusume`)

A premade `dat` folder might be released every so often. Ignore everything but the last step then.  
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

# Contribute

To contribute translations, see [translating.md](translating.md)  
For dev contributions, open a PR or Issue.

# Thanks to

[UnityPy](https://github.com/K0lb3/UnityPy)