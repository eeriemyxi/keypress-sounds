# Keypress Sounds

A project that lets you use play custom sounds when you press keys on any
website you let it to.

## How It Works

It is done via a custom file format I call KPS (Keypress Sounds), which is
structured as follows:

```
// Numbers are little-endian.

[ number of files: uint32 ]
[ file1...fileN's start, end nframe offset: uint32[2][N] ]
[ concatenated wav file dump ]
```

`run.py` is provided which reads the `sounds/` folder in the script
directory. `sounds/` is expected to contain subdirectories under which each
would contain a number of WAV files. The name of the subdirectory will be
accepted as the name of the sound pack.

When `run.py` is ran with the expected directory structure, it will upload
the generated KPS file to Catbox. This program expects `USER_HASH` environment
variable which should contain the hash code of their Catbox account (retrievable
from Catbox' account settings).

After uplading them, it saves them to the local SQLite3 database and caches the
byte count of each KPS file to detect if the contents changed.

At the end, it will print something like this:
```
* Update the user script with ONE of these templates:
Template Name: typewriter
// @resource    PACK https://files.catbox.moe/---.kps
Template Name: nk-creams
// @resource    PACK https://files.catbox.moe/---.kps
```

The user is expected to do as instructed and replace the relevant line in the
`keypress-sounds.user.js` file.

The userscript will parse the KPS file and listen for any `keydown` event. When
such an event is dispatched, the userscript randomly selects a file in the sound
pack and plays the sound.

To listen for arbitrary websites, the user is expeced to add a new `@match`
directive/header to the userscript for that website. For example:
```
// @match https://google.com/*
```
