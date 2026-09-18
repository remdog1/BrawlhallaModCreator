import os
import re
import shutil
import threading
import time
import subprocess
import sys
import tempfile
import traceback
import requests
from requests.exceptions import SSLError
from typing import List, Dict, Tuple, Union

try:
    import certifi
except ImportError:
    certifi = None

from .vartypes import ModDataSwfsTyped
from .variables import (MODS_PATH,
                        MODS_SOURCES_PATH,
                        MOD_FILE_FORMAT,
                        METADATA_FORMAT_MOD,
                        METADATA_FORMAT_CACHE_MOD,
                        METADATA_FORMAT_VERSION,
                        METADATA_FORMAT_CACHE_MODS_HASH_SUM,
                        METADATA_CACHE_MODS_HASH_SUM_FILE,
                        METADATA_CACHE_MOD_PREVIEWS_FOLDER,
                        METADATA_CACHE_MOD_FILE,
                        MODS_SOURCES_CACHE_FILE,
                        MODS_SOURCES_CACHE_PREVIEW,
                        MODLOADER_CACHE_PATH)
from .dataversion import DataClass, DataVariable
from .gameswf import GetGameFileClass
from .gamefiles import GameFiles
from .brawlhalla import (BRAWLHALLA_SWFS,
                         BRAWLHALLA_FILES,
                         BRAWLHALLA_VERSION,
                         NormalizeGameFileKey,
                         ResolveBrawlhallaFileKey)
from .basedispatch import SendNotification
from .bnkhandler import bnk_handler
from .langbin import LangFile

from ..utils.hash import RandomHash, HashFile

from ..swf.swf import Swf, GetElementId, SetElementId, GetShapeBitmapId, SetShapeBitmapId
from ..ffdec.classes import (CSMTextSettingsTag,
                             DefineFontNameTag,
                             DefineFontAlignZonesTag,
                             DefineBitsLosslessTags,
                             DefineFontTags,
                             DefineEditTextTag,
                             DefineTextTag,
                             DefineSoundTag,
                             DefineShapeTags,
                             DefineSpriteTag,
                             PlaceObject2Tag,
                             PlaceObject3Tag)
from ..notifications import NotificationType

__all__ = ["BaseModClass", "ModSource", "ModClass"]


LOCK = threading.Lock()


def _resourcePath(*parts):
    basePath = getattr(sys, "_MEIPASS", os.getcwd())
    return os.path.join(basePath, *parts)


class BaseModClass(DataClass):
    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 0, "formatVersion")
    formatVersion: int = METADATA_FORMAT_VERSION

    DataVariable(METADATA_FORMAT_MOD, 0, "formatType")
    formatType: str = METADATA_FORMAT_MOD

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "gameVersion")
    gameVersion: str

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "name")
    name: str

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "author")
    author: str

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "version")
    version: str

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "description")
    description: str

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "tags")
    tags: List[str]

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "previewsIds")
    previewsIds: Dict[int, str]

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "hash")
    hash: str

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "swfs")
    swfs: Dict[str, ModDataSwfsTyped]

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "files")
    files: Dict[int, str]

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 2, "authorId")
    authorId: int

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 2, "modId")
    modId: int

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 2, "platform")
    platform: str

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 2, "modUrl")
    modUrl: str

    DataVariable([METADATA_FORMAT_MOD, METADATA_FORMAT_CACHE_MOD], 1, "features")
    features: List[str]

    def loadModData(self):
        pass

    def getGameVersion(self):
        return self.gameVersion

    def getName(self):
        return self.name

    def getAuthor(self):
        return self.author

    def getVersion(self):
        return self.version

    def getDescription(self):
        return self.description

    def getTags(self):
        return self.tags

    def getFeatures(self):
        return self.features

    def getPreviewsPaths(self) -> List[str]:
        pass

    def getPreviewsContent(self) -> List[Tuple[bytes, str]]:
        pass


class ModSource(BaseModClass):
    _compile_lock = threading.Lock()
    regexSpriteFile = re.compile(r"DefineSprite_(\d+)_?(.+|)?")
    regexSoundFile = re.compile(r"\d+_([^.]+)")
    regexAsFile = re.compile(r"([^.]+)\.as")

    def __init__(self, modSourcesPath: str):
        SendNotification(NotificationType.LoadingModSource, modSourcesPath)

        self.modSourcesPath = modSourcesPath
        self.folderName = os.path.basename(modSourcesPath)
        self.cachePath = os.path.join(self.modSourcesPath, MODS_SOURCES_CACHE_FILE)
        self.previewsPath = os.path.join(self.modSourcesPath, MODS_SOURCES_CACHE_PREVIEW)
        if MODS_PATH:
            self.modPath = os.path.join(MODS_PATH[0], f"{self.folderName}.{MOD_FILE_FORMAT}")
        else:
            self.modPath = os.path.join(MODS_SOURCES_PATH[0], f"{self.folderName}.{MOD_FILE_FORMAT}")

        # Initialize required attributes with default values
        if not hasattr(self, 'gameVersion'):
            self.gameVersion = ""
        if not hasattr(self, 'name'):
            self.name = ""
        if not hasattr(self, 'author'):
            self.author = ""
        if not hasattr(self, 'version'):
            self.version = ""
        if not hasattr(self, 'description'):
            self.description = ""
        if not hasattr(self, 'tags'):
            self.tags = []
        if not hasattr(self, 'previewsIds'):
            self.previewsIds = {}
        if not hasattr(self, 'swfs'):
            self.swfs = {}
        if not hasattr(self, 'files'):
            self.files = {}
        if not hasattr(self, 'hash'):
            self.hash = ""
        if not hasattr(self, 'authorId'):
            self.authorId = 0
        if not hasattr(self, 'modId'):
            self.modId = 0
        if not hasattr(self, 'platform'):
            self.platform = ""
        if not hasattr(self, 'modUrl'):
            self.modUrl = ""
        if not hasattr(self, 'features'):
            self.features = []

        self.loadModData()

    def loadModData(self):
        loaded = self.loadJsonFile(self.cachePath, ignoredVars=["formatVersion", "swfs", "files", "previewsIds"])

        if not loaded:
            #print(f"New mod source '{self.folderName}' detected")
            self.saveModData()

        self.ensureDataDefaults(ignoredVars=["formatVersion", "swfs", "files", "previewsIds"])
        
        # Ensure features attribute exists after loading (with default empty list)
        if not hasattr(self, 'features') or self.features is None:
            self.features = []

    def saveModData(self):
        if not self.hash:
            self.hash = RandomHash()
        
        # Ensure features attribute exists before saving (with default empty list)
        if not hasattr(self, 'features') or self.features is None:
            self.features = []

        self.saveJsonFile(self.cachePath)

    def setGameVersion(self, gameVersion: str):
        self.gameVersion = gameVersion

    def setName(self, name: str):
        self.name = name

    def setAuthor(self, author: str):
        self.author = author

    def setVersion(self, version: str):
        self.version = version

    def setDescription(self, description: str):
        self.description = description

    def setTags(self, tags: list):
        self.tags = tags

    def setFeatures(self, features: list):
        self.features = features

    def setPreviewsPaths(self, previewsPaths: list):
        if not os.path.exists(self.previewsPath):
            os.mkdir(self.previewsPath)

        removePreviewPath = self.getPreviewsPaths()

        for n, previewPath in enumerate(previewsPaths):
            previewFormat = os.path.splitext(previewPath)[1]
            if previewPath and os.path.exists(previewPath):
                cachePreviewPath = os.path.join(self.previewsPath, f"preview{n}{previewFormat}")

                if cachePreviewPath in removePreviewPath:
                    removePreviewPath.remove(cachePreviewPath)

                with open(previewPath, "rb") as orig:
                    image = orig.read()
                with open(cachePreviewPath, "wb") as new:
                    new.write(image)
                del image

        for previewPath in removePreviewPath:
            os.remove(previewPath)

    def getPreviewsPaths(self) -> List[str]:
        previewsPaths = []
        if os.path.exists(self.previewsPath):
            for previewPath in os.listdir(self.previewsPath):
                previewsPaths.append(os.path.join(self.previewsPath, previewPath))

        return previewsPaths

    def getPreviewsContent(self) -> List[Tuple[bytes, str]]:
        previews = []

        if os.path.exists(self.previewsPath):
            for previewPath in self.getPreviewsPaths():
                previewFormat = os.path.splitext(previewPath)[1][1:]
                with open(previewPath, "rb") as preview:
                    previews.append((preview.read(), previewFormat))

        return previews

    def getElementsCount(self):
        return max(0, sum(len(files) for _, _, files in os.walk(self.modSourcesPath)) -
                   len(self.getPreviewsPaths()) - 1)

    def _getTargetFileKey(self, sourcePath: str, fallbackName: str = None):
        relativePath = NormalizeGameFileKey(os.path.relpath(sourcePath, self.modSourcesPath))
        return ResolveBrawlhallaFileKey(relativePath) or ResolveBrawlhallaFileKey(fallbackName or "")

    def compile(self):
        if not self._compile_lock.acquire(blocking=False):
            SendNotification(NotificationType.CompileModSourcesSaveError, self.hash,
                             'Another mod build is already running. Wait for it to finish.')
            return
        previous = self.swfs, self.previewsIds, self.files
        modSwf = None
        openSprites = []
        try:
            output_dir = os.path.dirname(os.path.abspath(self.modPath))
            os.makedirs(output_dir, exist_ok=True)
            # Keep the last successful package until its replacement is fully saved.
            with tempfile.TemporaryDirectory(prefix='.bmod-build-', dir=output_dir) as staging:
                staged_path = os.path.join(staging, 'package.bmod')
                try:
                    modSwf = Swf(staged_path)
                    self._compileInto(modSwf, openSprites)
                    modSwf.metaData.set(self.getDict())
                    modSwf.save()
                finally:
                    for sprite in openSprites:
                        sprite.close()
                    if modSwf is not None:
                        modSwf.close()
                os.replace(staged_path, self.modPath)
        except Exception as error:
            self.swfs, self.previewsIds, self.files = previous
            traceback.print_exc()
            SendNotification(NotificationType.CompileModSourcesSaveError, self.hash,
                             f'{type(error).__name__}: {error}')
        else:
            SendNotification(NotificationType.CompileModSourcesFinished, self.hash)
        finally:
            self._compile_lock.release()

    def _compileInto(self, modSwf, openSprites):
        SendNotification(NotificationType.CompileElementsCount, self.hash, self.getElementsCount())
        self.swfs = {}
        self.previewsIds = {}
        self.files = {}

        for folder in os.listdir(self.modSourcesPath):
            folderPath = os.path.join(self.modSourcesPath, folder)

            # Check for full .swf files in the root of the mod folder
            if os.path.isfile(folderPath) and folder.endswith(".swf"):
                # This is a full SWF file to be packaged and installed as-is
                if folder in BRAWLHALLA_SWFS:
                    SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, folder)
                    print(f"Found full .swf file in root: {folder}")
                    binaryTag = modSwf.importBinaryFile(folderPath)
                    self.files[GetElementId(binaryTag)] = folder
                else:
                    SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, 
                                    f"Unknown SWF file: {folder}. Only game SWF files can be replaced.")
                continue

            if os.path.isfile(folderPath):
                if folder != MODS_SOURCES_CACHE_FILE:
                    target = self._getTargetFileKey(folderPath, folder)
                    if target:
                        binaryTag = modSwf.importBinaryFile(folderPath)
                        self.files[GetElementId(binaryTag)] = target
                        SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, target)
                    else:
                        SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, folder)
                continue

            # Import game elements
            if folder.endswith(".swf") and folder in BRAWLHALLA_SWFS:
                gameSwfName: str = folder
                elementsMap = {}
                self.swfs[gameSwfName] = {}
                self.swfs[gameSwfName]["scripts"] = {}
                self.swfs[gameSwfName]["sounds"] = []
                self.swfs[gameSwfName]["sprites"] = []

                for category in os.listdir(folderPath):
                    categoryPath = os.path.join(folderPath, category)

                    if not os.path.isdir(categoryPath):
                        SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash,
                                         os.path.relpath(categoryPath, self.modSourcesPath))
                        continue

                    for elementPath in os.listdir(categoryPath):
                        if category == "scripts":
                            if script := self.regexAsFile.findall(elementPath):
                                scriptAnchor = script[0]
                                #print("Import ActionScript", scriptAnchor)
                                SendNotification(NotificationType.CompileModSourcesImportActionScripts,
                                                 self.hash, scriptAnchor)

                                with open(os.path.join(categoryPath, elementPath), "r") as actionScript:
                                    self.swfs[gameSwfName]["scripts"][scriptAnchor] = actionScript.read()

                        elif category == "sounds":
                            if sound := self.regexSoundFile.findall(elementPath):
                                soundAnchor = sound[0]
                                #print("Import Sound", soundAnchor)
                                SendNotification(NotificationType.CompileModSourcesImportSound, self.hash, soundAnchor)

                                self.swfs[gameSwfName]["sounds"].append(soundAnchor)

                                soundTag = modSwf.importSoundFile(os.path.join(categoryPath, elementPath))
                                modSwf.symbolClass.addTag(GetElementId(soundTag), soundAnchor)

                        elif category == "sprites":
                            if sprite := self.regexSpriteFile.findall(elementPath):
                                _, spriteAnchor = sprite[0]

                                SendNotification(NotificationType.CompileModSourcesImportSprite,
                                                 self.hash, spriteAnchor)

                                if not spriteAnchor:
                                    SendNotification(NotificationType.CompileModSourcesSpriteHasNoSymbolclass,
                                                     self.hash, elementPath)
                                    continue

                                self.swfs[gameSwfName]["sprites"].append(spriteAnchor)

                                framesPath = os.path.join(categoryPath, elementPath, "frames.swf")
                                if not os.path.isfile(framesPath):
                                    raise FileNotFoundError(f'Sprite source is missing frames.swf: {framesPath}')
                                spriteSwf = Swf(framesPath)
                                openSprites.append(spriteSwf)
                                try:
                                    spriteAS3 = spriteSwf.getAS3(spriteAnchor)
                                    if spriteAS3:
                                        self.swfs[gameSwfName]["scripts"][spriteAnchor] = spriteAS3
                                except Exception:
                                    pass

                                spriteElement = None
                                spriteId = 0
                                for element in spriteSwf.elementsList[::-1]:
                                    if isinstance(element, DefineSpriteTag):
                                        spriteElement = element
                                        spriteId = GetElementId(element)
                                        break
                                else:
                                    #print("Not found sprite in:", elementPath)
                                    spriteSwf.close()
                                    openSprites.remove(spriteSwf)
                                    SendNotification(NotificationType.CompileModSourcesSpriteNotFoundInFolder,
                                                     self.hash, elementPath)
                                    continue

                                cloneSprites = []
                                cloneShapes = []

                                for element in sorted(spriteSwf.elementsList, key=lambda x: GetElementId(x)):
                                    if not isinstance(element,
                                                      (CSMTextSettingsTag, DefineFontNameTag,
                                                       DefineFontAlignZonesTag, PlaceObject2Tag)):

                                        if GetElementId(element) in elementsMap:
                                            if element == spriteElement:
                                                for _element in spriteSwf.elementsList:
                                                    if isinstance(_element, (*DefineShapeTags, DefineEditTextTag,
                                                                             DefineSpriteTag,
                                                                             *DefineBitsLosslessTags)) or \
                                                            element == spriteElement:

                                                        elementsMap.pop(GetElementId(_element), None)
                                            else:
                                                continue

                                        newElId = modSwf.getNextCharacterId()
                                        cloneEl = modSwf.cloneAndAddElement(element, newElId)
                                        elementsMap[GetElementId(element)] = GetElementId(cloneEl)

                                        if isinstance(cloneEl, DefineShapeTags):
                                            if GetShapeBitmapId(cloneEl) is not None:
                                                cloneShapes.append(cloneEl)

                                        elif isinstance(cloneEl, DefineSpriteTag):
                                            cloneSprites.append(cloneEl)

                                        elif isinstance(element, DefineFontTags):
                                            for dependentElement in spriteSwf.getElementById(GetElementId(element),
                                                                                             (DefineFontNameTag,
                                                                                              DefineFontAlignZonesTag)):
                                                modSwf.cloneAndAddElement(dependentElement, newElId)

                                        elif isinstance(element, DefineEditTextTag):
                                            if dependentElement := spriteSwf.getElementById(GetElementId(element),
                                                                                            CSMTextSettingsTag):
                                                modSwf.cloneAndAddElement(dependentElement[0], newElId)
                                            # Only update fontId if it exists in elementsMap
                                            if hasattr(element, 'fontId') and element.fontId in elementsMap:
                                                cloneEl.fontId = elementsMap[element.fontId]

                                        elif isinstance(element, DefineTextTag):
                                            if dependentElement := spriteSwf.getElementById(GetElementId(element),
                                                                                            CSMTextSettingsTag):
                                                modSwf.cloneAndAddElement(dependentElement[0], newElId)

                                            for textRecord in cloneEl.textRecords:
                                                if textRecord.styleFlagsHasFont:
                                                    # Only update fontId if it exists in elementsMap
                                                    if hasattr(textRecord, 'fontId') and textRecord.fontId in elementsMap:
                                                        textRecord.fontId = elementsMap[textRecord.fontId]

                                for cloneSprite in cloneSprites:
                                    for sEl in cloneSprite.getTags().iterator():
                                        if isinstance(sEl, PlaceObject2Tag) and sEl.characterId > 0:
                                            # Only update if the character ID exists in elementsMap
                                            # Some character IDs might reference elements that weren't cloned
                                            # (e.g., already exist in target SWF or are external references)
                                            if sEl.characterId in elementsMap:
                                                SetElementId(sEl, elementsMap[sEl.characterId])
                                            # else: Character ID not in map - might be a reference to existing element
                                            #       or an invalid reference, keeping original ID
                                        elif isinstance(sEl, PlaceObject3Tag) and sEl.characterId > 0:
                                            # Only update if the character ID exists in elementsMap
                                            if sEl.characterId in elementsMap:
                                                SetElementId(sEl, elementsMap[sEl.characterId])
                                            # else: Character ID not in map - might be a reference to existing element
                                            #       or an invalid reference, keeping original ID

                                for cloneShape in cloneShapes:
                                    bitmapId = GetShapeBitmapId(cloneShape)
                                    # Only update if the bitmap ID exists in elementsMap
                                    if bitmapId is not None and bitmapId in elementsMap:
                                        SetShapeBitmapId(cloneShape, elementsMap[bitmapId])
                                    # else: Bitmap ID not in map - might be a reference to existing element
                                    #       keeping original ID

                                if cloneSprites:
                                    modSwf.symbolClass.addTag(elementsMap[spriteId], spriteAnchor)
                                else:
                                    SendNotification(NotificationType.CompileModSourcesSpriteEmpty,
                                                     self.hash, spriteAnchor)
                                spriteSwf.close()
                                openSprites.remove(spriteSwf)

                        else:
                            #print(f"Error: Unsupported category '{category}'")
                            SendNotification(NotificationType.CompileModSourcesUnsupportedCategory, self.hash, category)

            # Import previews
            elif folder.startswith("_"):
                if folder == MODS_SOURCES_CACHE_PREVIEW:
                    for n, preview in enumerate(os.listdir(folderPath)):
                        #print("Import Preview", n)
                        SendNotification(NotificationType.CompileModSourcesImportPreview, self.hash, n)

                        binaryTag = modSwf.importBinaryFile(os.path.join(folderPath, preview))
                        previewFormat = os.path.splitext(preview)[1][1:]
                        self.previewsIds[GetElementId(binaryTag)] = previewFormat

            # Import .bnk folders containing .wem files
            elif folder.endswith(".bnk") and os.path.isdir(folderPath):
                bnk_file_name = folder  # e.g., "VOX_Announcer.bnk"
                target_bnk_name = self._getTargetFileKey(folderPath, bnk_file_name)
                if not target_bnk_name:
                    SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, bnk_file_name)
                    continue

                print(f"Found .bnk folder: {bnk_file_name}")
                SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, target_bnk_name)
                
                wem_files = []
                for path, dirs, files in os.walk(folderPath):
                    for file in files:
                        if file.endswith(".wem"):
                            wem_files.append(os.path.join(path, file))
                
                if not wem_files:
                    SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, 
                                    f"No .wem files found in {bnk_file_name}")
                    continue

                for wem_path in wem_files:
                    wem_relative_path = NormalizeGameFileKey(os.path.relpath(wem_path, folderPath))
                    target_wem_name = NormalizeGameFileKey(os.path.join(target_bnk_name, wem_relative_path))

                    binaryTag = modSwf.importBinaryFile(wem_path)
                    self.files[GetElementId(binaryTag)] = target_wem_name
                    SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, target_wem_name)

            # Import images, music, and other files
            elif os.path.isdir(folderPath):
                for path, folders, files in os.walk(folderPath):
                    for file in files:
                        # Prioritize handling of language files (.bin and .txt) - check this first
                        if (file.startswith("language.") and file.endswith(".bin")) or (file.startswith("language.") and file.endswith(".txt")):
                            SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, file)

                            # Log that we found a language file to help with debugging
                            print(f"Found language file in mod: {file}")
                            
                            # Handle different language file types
                            actual_file = file
                            file_path = os.path.join(path, file)
                            
                            if file.endswith(".txt"):
                                # Convert .txt to .bin for proper Mod Loader processing
                                actual_file = file.replace(".txt", ".bin")
                                print(f"Converting .txt language file to .bin: {file} -> {actual_file}")
                                
                                # Convert the .txt file to .bin format using LangFile
                                try:
                                    # Create a temporary .bin file
                                    temp_bin_path = os.path.join(MODLOADER_CACHE_PATH, f"temp_{actual_file}")
                                    os.makedirs(os.path.dirname(temp_bin_path), exist_ok=True)
                                    
                                    # Create LangFile instance and load from text file
                                    lang_file = LangFile.__new__(LangFile)  # Create instance without calling __init__
                                    lang_file.entries = []
                                    lang_file.entry_count = 0
                                    lang_file.inflated_size = b''
                                    lang_file.zlibdata = b''
                                    
                                    # Load from text file using FromTextFile method
                                    lang_file.FromTextFile(file_path)
                                    
                                    # Save as properly formatted .bin file
                                    lang_file.Save(temp_bin_path)
                                    
                                    # Import the converted .bin file
                                    binaryTag = modSwf.importBinaryFile(temp_bin_path)
                                    
                                    # Clean up temporary file
                                    os.remove(temp_bin_path)
                                    
                                    print(f"Successfully converted and imported {file} as {actual_file}")
                                    
                                except Exception as e:
                                    raise ValueError(f'Cannot convert language file {file_path}: {e}') from e
                                    
                            else:
                                # Import .bin file directly
                                binaryTag = modSwf.importBinaryFile(file_path)
                            
                            # If the file is just "language.bin" but the game uses numbered language files,
                            # we need to rename it to match what's installed on the system - use language.1.bin
                            if actual_file == "language.bin" and any(f.startswith("language.") and f.endswith(".bin") and f != actual_file for f in BRAWLHALLA_FILES.keys()):
                                # Find the first numbered language file in the game directory
                                for possible_file in sorted(BRAWLHALLA_FILES.keys()):
                                    if possible_file.startswith("language.") and possible_file.endswith(".bin") and possible_file != actual_file:
                                        actual_file = possible_file
                                        print(f"Renaming language file to match game format: {file} -> {actual_file}")
                                        break
                            
                            # Calculate relative path from mod sources root to preserve folder structure
                            relative_path = os.path.relpath(path, self.modSourcesPath)
                            relative_path = relative_path.replace("\\", "/")
                            
                            # For language files, we need to ensure they have the correct path structure
                            # The Mod Loader expects language files to be in a 'languages/' folder
                            if relative_path and relative_path != ".":
                                # If the file is already in a languages folder, keep that structure
                                if "languages" in relative_path:
                                    final_file_name = f"{relative_path}/{actual_file}"
                                else:
                                    # If not in languages folder, add it
                                    final_file_name = f"languages/{actual_file}"
                            else:
                                # If no folder path, put in languages folder
                                final_file_name = f"languages/{actual_file}"
                            
                            target_file_name = self._getTargetFileKey(file_path, final_file_name)
                            if not target_file_name:
                                SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, final_file_name)
                                continue

                            print(f"Packaging language file with path: {file} -> {target_file_name}")
                            
                            # Store the file mapping with the correct path
                            self.files[GetElementId(binaryTag)] = target_file_name
                            
                            # Debug notification to confirm language file import
                            SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, f"Successfully imported {file} as {actual_file}")
                        
                        # Handle .bnk files
                        elif file.endswith(".bnk"):
                            file_path = os.path.join(path, file)
                            target_file_name = self._getTargetFileKey(file_path, file)
                            SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, target_file_name or file)
                            
                            # Log that we found a .bnk file
                            print(f"Found .bnk file in mod: {file}")
                            
                            # Verify the .bnk file exists in the game
                            if not target_file_name:
                                SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, file)
                                continue
                                
                            # Import the .bnk file
                            binaryTag = modSwf.importBinaryFile(file_path)
                            self.files[GetElementId(binaryTag)] = target_file_name

                            # Debug notification to confirm .bnk file import
                            SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, f"Successfully imported {file}")

                        elif file.endswith(".wem"):
                            file_path = os.path.join(path, file)
                            relative_file = NormalizeGameFileKey(os.path.relpath(file_path, self.modSourcesPath))
                            path_parts = relative_file.split("/")
                            bnk_index = next((i for i, part in enumerate(path_parts) if part.lower().endswith(".bnk")), None)

                            if bnk_index is None:
                                SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, relative_file)
                                continue

                            target_bnk_candidate = NormalizeGameFileKey("/".join(path_parts[:bnk_index + 1]))
                            target_bnk_name = ResolveBrawlhallaFileKey(target_bnk_candidate) or ResolveBrawlhallaFileKey(path_parts[bnk_index])
                            if not target_bnk_name:
                                SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, target_bnk_candidate)
                                continue

                            wem_relative_path = NormalizeGameFileKey("/".join(path_parts[bnk_index + 1:]))
                            target_file_name = NormalizeGameFileKey(os.path.join(target_bnk_name, wem_relative_path))

                            binaryTag = modSwf.importBinaryFile(file_path)
                            self.files[GetElementId(binaryTag)] = target_file_name
                            SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, target_file_name)
                        
                        elif target_file_name := self._getTargetFileKey(os.path.join(path, file), file):
                            #print("Import File", file)
                            SendNotification(NotificationType.CompileModSourcesImportFile, self.hash, target_file_name)

                            binaryTag = modSwf.importBinaryFile(os.path.join(path, file))
                            self.files[GetElementId(binaryTag)] = target_file_name
                        else:
                            #print("Error: Unknown file:", file)
                            relative_file = NormalizeGameFileKey(os.path.relpath(os.path.join(path, file), self.modSourcesPath))
                            SendNotification(NotificationType.CompileModSourcesUnknownFile, self.hash, relative_file)

    def delete(self):
        shutil.rmtree(self.modSourcesPath)


class ModsHashSumCache(DataClass):
    DataVariable(METADATA_FORMAT_CACHE_MODS_HASH_SUM, 0, "formatVersion")
    formatVersion: str = METADATA_FORMAT_VERSION

    DataVariable(METADATA_FORMAT_CACHE_MODS_HASH_SUM, 0, "formatType")
    formatType: str = METADATA_FORMAT_CACHE_MODS_HASH_SUM

    DataVariable(METADATA_FORMAT_CACHE_MODS_HASH_SUM, 1, "hashes")
    hashes: Dict[str, str]  # {hashSum: modHash}

    def __init__(self, modsHashSumCachePath: str):
        self.path = os.path.join(modsHashSumCachePath, METADATA_CACHE_MODS_HASH_SUM_FILE)
        self.loadJsonFile(self.path)

    def save(self):
        self.saveJsonFile(self.path)

    def setHash(self, hashSum: str, modHash: str):
        self.hashes[hashSum] = modHash

    def getHash(self, hashSum) -> Union[str, None]:
        return self.hashes.get(hashSum, None)

    def getHashSum(self, modHash: str) -> Union[str, None]:
        for hashSum, _modHash in self.hashes.items():
            if modHash == _modHash:
                return hashSum

        return None

    def removeHash(self, hashSum: str):
        self.hashes.pop(hashSum)


class ModCache(BaseModClass):
    DataVariable(METADATA_FORMAT_CACHE_MOD, 0, "formatType")
    formatType: str = METADATA_FORMAT_CACHE_MOD

    DataVariable(METADATA_FORMAT_CACHE_MOD, 1, "hashSum")
    hashSum: str

    DataVariable(METADATA_FORMAT_CACHE_MOD, 1, "installed")
    installed: bool = False

    DataVariable(METADATA_FORMAT_CACHE_MOD, 1, "currentVersion")
    currentVersion: bool = True

    DataVariable(METADATA_FORMAT_CACHE_MOD, 1, "modFileExist")
    modFileExist: bool = True

    DataVariable([METADATA_FORMAT_CACHE_MOD], 1, "features")
    features: List[str]

    modCachePath: str

    def loadCache(self, allowedVars=None, ignoredVars=None):
        if self.modCachePath:
            self.loadJsonFile(os.path.join(self.modCachePath, METADATA_CACHE_MOD_FILE),
                              allowedVars=allowedVars,
                              ignoredVars=ignoredVars)
            self.ensureDataDefaults(ignoredVars=ignoredVars)

    def saveCache(self):
        if self.modCachePath:
            self.saveJsonFile(os.path.join(self.modCachePath, METADATA_CACHE_MOD_FILE))


class ModClass(ModCache):
    def __init__(self, modsCachePath: str = None, modPath: str = None, modHash: str = None, 
                 gameVersion: str = "", name: str = "", author: str = "", version: str = "", 
                 description: str = "", tags: List[str] = None, features: List[str] = None,
                 previewsPaths: List[str] = None, hash: str = "", platform: str = "",
                 installed: bool = False, currentVersion: bool = True, modFileExist: bool = True,
                 modSourcesPath: str = "", **kwargs):
        
        # Handle both old and new initialization patterns
        if modsCachePath is not None:
            # Old pattern: loading from cache
            self.modPath = modPath
            self.modsHashSumCache = ModsHashSumCache(modsCachePath)
            
            # Initialize features attribute if not present (with default empty list)
            if not hasattr(self, 'features') or self.features is None:
                self.features = []
        else:
            # New pattern: creating from parameters
            self.gameVersion = gameVersion
            self.name = name
            self.author = author
            self.version = version
            self.description = description
            self.tags = tags or []
            self.features = features or []
            self.previewsPaths = previewsPaths or []
            self.hash = hash
            self.platform = platform
            self.installed = installed
            self.currentVersion = currentVersion
            self.modFileExist = modFileExist
            self.modSourcesPath = modSourcesPath
            self.modPath = None
            self.modsHashSumCache = None
            return

        SendNotification(NotificationType.LoadingMod, modPath)

        if self.modPath is not None and os.path.exists(self.modPath):
            self.modFileExist = True

            self.modSwf = Swf(self.modPath, autoload=False)
            modHashSum = HashFile(self.modPath)

            _cache = False

            if modHash := self.modsHashSumCache.getHash(modHashSum):
                self.modCachePath = os.path.join(modsCachePath, modHash)
                if os.path.exists(self.modCachePath):
                    self.loadCache(ignoredVars=["modFileExist"])
                else:
                    _cache = True
            else:
                _cache = True

            if _cache:
                SendNotification(NotificationType.LoadingModData, modPath)
                self.loadModData()

                self.hashSum = modHashSum
                self.modCachePath = os.path.join(modsCachePath, self.hash)

                if oldHashSum := self.modsHashSumCache.getHashSum(self.hash):
                    self.modsHashSumCache.removeHash(oldHashSum)
                else:
                    if not os.path.exists(self.modCachePath):
                        os.mkdir(self.modCachePath)

                self.cachePreviews()

                self.modsHashSumCache.setHash(modHashSum, self.hash)
                self.modsHashSumCache.save()

                self.loadCache(allowedVars=["installed"])
        elif modHash is not None:
            self.modFileExist = False
            self.modSwf = None
            self.modCachePath = os.path.join(modsCachePath, modHash)
            self.hash = modHash
            # if modHashSum := self.modsHashSumCache.getHashSum(modHash):
            #    self.modsHashSumCache.removeHash(modHashSum)
            #    self.modsHashSumCache.save()
            if os.path.exists(self.modCachePath):
                self.loadCache(ignoredVars=["modFileExist"])
            else:
                self.removeCache()
                raise Exception("Not found mods cache")
        else:
            SendNotification(NotificationType.LoadingModIsEmpty, None, modPath)

        if BRAWLHALLA_VERSION is not None and BRAWLHALLA_VERSION == self.gameVersion:
            self.currentVersion = True
        else:
            self.currentVersion = False

        if self.modPath is not None:
            self.saveCache()

    def open(self):
        self.modSwf.open()

    def close(self):
        self.modSwf.close()

    def removeCache(self):
        if modHashSum := self.modsHashSumCache.getHashSum(self.hash):
            self.modsHashSumCache.removeHash(modHashSum)
            self.modsHashSumCache.save()

        shutil.rmtree(self.modCachePath)

    def loadModData(self):
        modOpen = self.modSwf.isOpen()

        if not modOpen:
            self.open()

        self.loadFromJson(self.modSwf.metaData.get(), ignoredVars=["formatType", "hashSum", "installed",
                                                                   "currentVersion", "modFileExist"])
        self.ensureDataDefaults(ignoredVars=["formatType", "hashSum", "installed",
                                             "currentVersion", "modFileExist"])

        if not modOpen:
            self.close()

    def cachePreviews(self):
        SendNotification(NotificationType.LoadingModCachePreviews, self.hash)

        modOpen = self.modSwf.isOpen()
        modCachePreviewsPath = os.path.join(self.modCachePath, METADATA_CACHE_MOD_PREVIEWS_FOLDER)

        if not os.path.exists(modCachePreviewsPath):
            os.mkdir(modCachePreviewsPath)

        if not modOpen:
            self.open()

        for file in os.listdir(modCachePreviewsPath):
            os.remove(os.path.join(modCachePreviewsPath, file))

        for n, (elId, previewFormat) in enumerate(self.previewsIds.items()):
            self.modSwf.exportBinaryFile(os.path.join(modCachePreviewsPath, f"preview{n}.{previewFormat}"),
                                         elId=elId)

        if not modOpen:
            self.close()

    def getPreviewsPaths(self) -> List[str]:
        previewsPaths = []

        modCachePreviewsPath = os.path.join(self.modCachePath, METADATA_CACHE_MOD_PREVIEWS_FOLDER)
        if os.path.exists(modCachePreviewsPath):
            for file in os.listdir(modCachePreviewsPath):
                previewsPaths.append(os.path.join(modCachePreviewsPath, file))

        return previewsPaths

    def getPreviewsContent(self) -> List[Tuple[bytes, str]]:
        previewsContent = []

        for previewPath in self.getPreviewsPaths():
            previewFormat = os.path.splitext(previewPath)[1][1:]

            with open(previewPath, "rb") as file:
                previewsContent.append((file.read(), previewFormat))

        return previewsContent

    def getElementsCount(self):
        return len(self.files) + len([j for i in self.swfs.values() for n in i.values() for j in n])

    def getModConflict(self) -> List[str]:
        LOCK.acquire(True)

        SendNotification(NotificationType.ModElementsCount, self.hash, len(self.swfs))

        temp_gameFiles = []
        conflictMods = set(GameFiles.getModConflict(list(self.files.values()), self.hash))
        for swfName, swfMap in self.swfs.items():
            gameFile = GetGameFileClass(swfName)
            gameFile.open()

            SendNotification(NotificationType.ModConflictSearchInSwf, self.hash, swfName)

            temp_gameFiles.append(gameFile)

            for category, anchors in swfMap.items():
                if category in ("sounds", "sprites", "scripts"):
                    conflictAnchors = set(list(anchors)) & set(list(gameFile.modifiedAnchorsMap))

                    for anchor in conflictAnchors:
                        if modHash := gameFile.modifiedAnchorsMap.get(anchor, None):
                            conflictMods.add(modHash)

                    del conflictAnchors

            gameFile.close()

        if conflictMods:
            pass
            # print("Mod conflict:", list(conflictMods))
            SendNotification(NotificationType.ModConflict, self.hash, list(conflictMods))
        else:
            del temp_gameFiles
            SendNotification(NotificationType.ModConflictNotFound, self.hash)
            #del conflictMods

        LOCK.release()

        return list(conflictMods)

    def install(self, forceInstallation=False):
        LOCK.acquire(True)

        SendNotification(NotificationType.ModElementsCount, self.hash, self.getElementsCount())

        self.open()

        # Check conflict mods
        if not forceInstallation:
            conflictMods = self.getModConflict()
            if conflictMods:
                SendNotification(NotificationType.ModConflict, self.hash, list(conflictMods))
                return conflictMods

        else:
            pass
            #SendNotification(NotificationType.ForceInstallation, self.hash)

        for elId, fileName in self.files.items():
            fileElement = self.modSwf.getElementById(elId)
            if fileElement:
                fileElement = fileElement[0]
            else:
                #print(f"Error: Not found element '{[elId]}'", fileElement)
                SendNotification(NotificationType.InstallingModNotFoundFileElement, self.hash, elId)
                continue

            GameFiles.installFile(fileName, self.modSwf.exportBinaryData(fileElement), self.hash)

        for swfName, swfMap in self.swfs.items():
            gameFile = GetGameFileClass(swfName)
            gameFile.open()

            if gameFile is None:
                #print(f"Error: Not found swf '{swfName}'!")
                SendNotification(NotificationType.InstallingModNotFoundGameSwf, self.hash, swfName)
                continue

            if self.hash in gameFile.installed:
                #print(f"Mod '{self.name}' in '{swfName}' is already installed")
                SendNotification(NotificationType.InstallingModInFileAlreadyInstalled, self.hash, swfName)
                continue
            else:
                #print(f"Installing '{self.name}' in '{swfName}'")
                SendNotification(NotificationType.InstallingModSwf, self.hash, swfName)

            for category, elements in swfMap.items():
                if category == "scripts":
                    for scriptAnchor, content in elements.items():
                        SendNotification(NotificationType.InstallingModSwfScript, self.hash, scriptAnchor)

                        success = gameFile.importScript(content, scriptAnchor, self.hash)

                        if not success:
                            SendNotification(NotificationType.InstallingModSwfScriptError, self.hash, scriptAnchor)

                elif category == "sounds":
                    for soundAnchor in elements:
                        #print("Install Sound", soundAnchor)
                        SendNotification(NotificationType.InstallingModSwfSound, self.hash, soundAnchor)

                        soundId = self.modSwf.symbolClass.getTagByName(soundAnchor)
                        if soundId is None:
                            #print(f"Error: Sound {soundAnchor} does not exist")
                            SendNotification(NotificationType.InstallingModSwfSoundSymbolclassNotExist,
                                             self.hash, soundAnchor, swfName)
                            continue

                        sound = self.modSwf.getElementById(soundId, DefineSoundTag)
                        if sound:
                            sound = sound[0]
                        else:
                            #print(f"Error: Sound {soundId} {soundAnchor} does not exist")
                            SendNotification(NotificationType.InstallingModSoundNotExist,
                                             self.hash, soundAnchor, soundId, swfName)
                            continue

                        gameFile.importSound(sound, soundAnchor, self.hash)
                elif category == "sprites":
                    elementsMap = {}
                    for spriteAnchor in elements:
                        #print("Install Sprite", spriteAnchor)
                        SendNotification(NotificationType.InstallingModSwfSprite, self.hash, spriteAnchor)

                        spriteId = self.modSwf.symbolClass.getTagByName(spriteAnchor)
                        if spriteId is None:
                            #print(f"Error: Sprite {spriteAnchor} does not exist")
                            SendNotification(NotificationType.InstallingModSwfSpriteSymbolclassNotExist,
                                             self.hash, spriteAnchor, swfName)
                            continue

                        sprite = self.modSwf.getElementById(spriteId, DefineSpriteTag)
                        if sprite:
                            sprite = sprite[0]
                        else:
                            #print(f"Error: Sprite {spriteId} {spriteAnchor} does not exist")
                            SendNotification(NotificationType.InstallingModSpriteNotExist,
                                             self.hash, spriteAnchor, spriteId, swfName)
                            continue

                        gameFile.importSprite(sprite, spriteAnchor, self.hash, elementsMap)

            gameFile.addInstalledMod(self.hash)
            #print(gameFile.getJson(formatJson=True))
            gameFile.save()
            gameFile.close()

        SendNotification(NotificationType.InstallingModFinished, self.hash)

        self.installed = True
        self.saveCache()

        LOCK.release()

    def uninstall(self):
        LOCK.acquire(True)

        SendNotification(NotificationType.ModElementsCount, self.hash, self.getElementsCount())

        GameFiles.uninstallMod(self.hash)

        for swfName in self.swfs:
            gameFile = GetGameFileClass(swfName)
            gameFile.open()

            gameFile.uninstallMod(self.hash)

            gameFile.save()
            gameFile.close()

        SendNotification(NotificationType.UninstallingModFinished, self.hash)

        self.installed = False
        self.saveCache()

        LOCK.release()

    def reinstall(self):
        self.uninstall()
        self.install()

    def delete(self):
        self.removeCache()
        if self.modPath:
            os.remove(self.modPath)
