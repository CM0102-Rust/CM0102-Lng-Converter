# CM 01/02 .lng converter

*[Versão em português](README.pt.md) · [Türkçe](README.tr.md)*

Carries a translated names file (`Data\<language>.lng`) of **Championship Manager 01/02 (3.9.68)** from one database to another: the translation made for the 2001 database (or for any update) becomes usable on a newer one.

## The problem

The game reads the translated names of clubs, nations, cities, stadiums and competitions from `fra.lng`, `por.lng`, `ger.lng`... The records in these files have **no ids**: record *i* belongs to entity *i* of the database. When loading, the game checks the counts in the file header against the database. If one does not match, it shows **"v3.9.68 Database..cpp 7784"** and reads no names at all: everything stays in English. So a `.lng` made for one database does not fit another.

The game also reads **`eng.lng`**, whatever language is chosen, with the same check (the error is then **"Database..cpp 19953"**). So `eng.lng` has to be converted together with the language file.

## What the tool does

It matches each entity of the new database with the old one by its **English name**, using the nation, city or club short name to separate entries with the same name. It then copies the translation of everything that exists in both and leaves only the new or renamed entries in English. The game keeps the database name for an empty record. Because the translations are matched by name, nothing is copied by position: if a position was reused for another entity (a nation or award replaced by a different one), its old translation is not carried over.

It writes a report with, for each table, how many entries were translated and how many stayed in English, plus the lists for the translator: renamed entries and lost translations, with the old translation next to them.

Example: the original 2001 `fra.lng` carried to the CLZ 25-26 database kept 6/6 continents, 209/231 nations, 269 clubs, 134 cities and 229 awards translated. The game opened without errors and showed the translated names.

## Download

Get **`lng_converter.exe`** from the [Releases](../../releases) page. It is a single file, with Python embedded: nothing else to install.

## Use

1. Open `lng_converter.exe`.
2. Fill in the four fields:
   - **Translated .lng file:** the file to convert (e.g. `fra.lng`). Its folder is filled into the next field.
   - **Data folder of the database it was made for:** the `Data` folder that matches that file. `eng.lng` is also taken from here.
   - **Data folder of the new database:** the `Data` folder of the database you want to use.
   - **Output folder:** where to write. It can be the new game's `Data` folder: any file already there is kept as `.bak`.
3. Leave **"Also convert eng.lng"** checked.
4. Click **Convert**. The report appears in the window and is saved as `lng_converter_report.txt` in the output folder. The first line of each file says whether the game will accept it.

Keep a copy of the game folder before replacing files.

### Command line

With Python 3 installed, the same tools run without the window:

```
python lng_converter.py <input.lng> <old Data> <new Data> <output.lng> [--completar] [-v]
python lng_confere.py <file.lng> <Data>
```

- `--completar` is for `eng.lng`: entries with no match get the new database's own English text instead of an empty record, because the game does not fall back to the database name when reading `eng.lng`.
- `lng_confere.py` tells, without opening the game, whether it will accept a `.lng` with a given database.
- The command line messages are in Portuguese, like the rest of the project.

## Files

| File | What it is |
|---|---|
| `lng_converter_gui.py` | the window (the source of `lng_converter.exe`) |
| `lng_converter.py` | the conversion |
| `lng_confere.py` | the check the game makes when loading a `.lng` |
| `build.bat` | builds `lng_converter.exe` with PyInstaller |
| [`docs/LNG_FORMAT.en.md`](docs/LNG_FORMAT.en.md) | the `.lng` format, with the game's addresses |

Build: `pip install pyinstaller`, then `build.bat`. The exe comes out in `dist\`.

No game file is in this repository: the tool reads the `.dat` and `.lng` files from your own game folder.

## About

Part of the **CM 01/02 in Rust** project, which reverse engineers 3.9.68 and rewrites it routine by routine. The analysis of the game code was done with the help of artificial intelligence. Thanks to the champman0102 community, and to everyone keeping 01/02 alive.

Questions: open an issue, or message **lucastmpacheco** on the [champman0102 forum](https://champman0102.net).
