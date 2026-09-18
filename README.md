# Brawlhalla ModCreator ![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)

This maintained version includes portable Java support, safer mod packaging,
folder-aware asset matching, and an optional GitHub updater. See
[Source and Build Instructions](SOURCE_BUILD.md) and [Updating](UPDATING.md).

**ModCreator** - tool for creating mods for Brawlhalla  
**[ModLoader](https://github.com/Farbigoz/BhModloader)** - tool for installing mods in Brawlhalla

![window](https://github.com/Farbigoz/BhModCreator/blob/main/wiki/readme/window.png)

## Download application
Published builds and prereleases are available in the [**releases section**](https://github.com/remdog1/BrawlhallaModCreator/releases).
Draft releases are for testing and are not offered by the updater.

## Wiki
* **[Formatting description text](https://github.com/Farbigoz/BhModCreator/wiki/Text-formatting)**

## Project

### Required libraries
    $ pip install JPype1
    $ pip install PySide6
    $ pip install psutil
    $ pip install pywin32   #If your system - Windows
    
### Build
    $ pip install pyinstaller  
    $ pyinstaller main.spec

## Licenses

Brawlhalla ModCreator is licensed with GNU GPL v3, see the [license.txt](license.txt).
It uses modified code of these libraries:

* [FFDec Library](https://github.com/jindrapetrik/jpexs-decompiler) - LGPLv3
