# hails.nds-Patcher

Patches `.nds` ROMs that won't load in [Pokemon DS Widescreen](https://github.com/mamesj/pokemon-ds-widescreen) and other programs without a DS BIOS, usually with `Secure area decryption failed` in the log. It decrypts the ROM's 2 KB secure area and changes nothing else. ROMs that are already decrypted are left alone.

This repository contains no ROMs and no Nintendo data. You need your own ROMs.

## Use

Needs [Python 3](https://www.python.org/downloads/). It gets the key table it needs by itself (see [Key table](#key-table)).

Drag `.nds` files or a folder onto `Patch ROMs.bat`. Close the game first.

From a command line:

```
python hails_patcher.py "path\to\roms"                               fix a folder
python hails_patcher.py --dry-run "path\to\roms"                     report only
python hails_patcher.py --restore "path\to\game.nds"                 undo
python hails_patcher.py --key "path\to\bios7.bin" "path\to\game.nds" choose the key file
```

## Backups

The original 2 KB of each fixed ROM goes in `backups\`, named after the ROM. `--restore` needs that file and the ROM's name unchanged, and deletes the backup once it has restored the ROM.

## Key table

Decrypting needs the DS KEY1 table. The patcher uses the first one it finds:

1. `key1.bin` in this folder
2. `biosnds7.rom` or `bios7.bin` in this folder
3. `..\desmume*\*.exe`
4. The latest [DeSmuME](https://github.com/TASEmulators/desmume) release, downloaded from GitHub and saved here as `key1.bin`

You can also make `key1.bin` yourself. Every source is checked by hash, and these won't replace an existing `key1.bin` unless you add `--force`:

```
python get_key1.py                           download DeSmuME, extract, delete the download
python extract_key1.py                       from ..\desmume*\*.exe
python extract_key1.py "path\to\bios7.bin"   from a file you choose
```

`key1.bin` and `backups\` hold Nintendo's data. `.gitignore` keeps them out of this repository, so don't add them to a fork or a release.

## License

[MIT](LICENSE). This covers the code in this repository, not the key table or any Nintendo data.

## Disclaimer

Pokemon is a trademark of Nintendo, Creatures and GAME FREAK. This project is not affiliated with or endorsed by them.
