import os
import io
import shutil
from typing import Dict, List, Optional

from .variables import MODLOADER_CACHE_PATH, MODLOADER_CACHE_FILES_FOLDER
from .brawlhalla import BRAWLHALLA_FILES, BRAWLHALLA_PATH
from .basedispatch import SendNotification
from ..notifications import NotificationType
from ..utils.hash import HashFile

# Import DecodeLang functionality
import zlib
import re
import codecs


class ByteReader:
    @staticmethod
    def ReadUint32BE(data: io.BytesIO) -> int:
        byte = data.read(4)
        return int.from_bytes(byte, byteorder="big")

    @staticmethod
    def ReadUint16BE(data: io.BytesIO) -> int:
        byte = data.read(2)
        return int.from_bytes(byte, byteorder="big")


class UTF8String:
    # ctor
    def __init__(self, length: int, string: str):
        self.length = length
        self.string = string

    # static class methods
    @classmethod
    def FromBytesIO(cls, data: io.BytesIO):
        length = ByteReader.ReadUint16BE(data)
        string = data.read(length).decode('utf-8')
        return cls(length, string)

    @classmethod
    def FromString(cls, string: str):
        return cls(len(string.encode('utf-8')), string)

    # public
    def WriteBytesIO(self, data: io.BytesIO) -> None:
        data.write(self.length.to_bytes(2, byteorder="big"))
        data.write(self.string.encode('utf-8'))


class Entry:
    # ctor
    def __init__(self, key: UTF8String, value: UTF8String):
        self.key: UTF8String = key
        self.value: UTF8String = value

    # public
    def WriteBytesIO(self, data: io.BytesIO) -> None:
        self.key.WriteBytesIO(data)
        self.value.WriteBytesIO(data)

    def SetValue(self, value: str) -> None:
        self.value = UTF8String.FromString(value)

    # static class methods
    @classmethod
    def FromBytesIO(cls, data: io.BytesIO):
        return cls(UTF8String.FromBytesIO(data), UTF8String.FromBytesIO(data))

    @classmethod
    def FromKeyValuePair(cls, key: str, value: str):
        return cls(UTF8String.FromString(key), UTF8String.FromString(value))


class LangFile:
    # ctor
    def __init__(self, filename: str):
        with open(filename, "rb") as fd:
            self.entries = []
            self.inflated_size = fd.read(4)
            self.zlibdata = fd.read()
            self.__ParseFile()

    # public
    def Save(self, filename: str) -> None:
        data: io.BytesIO = io.BytesIO()
        data.write(self.__WriteUint32BE(self.entry_count))
        for entry in self.entries:
            entry.WriteBytesIO(data)

        with open(filename, "wb") as fd:
            self.inflated_size = data.getbuffer().nbytes
            fd.write(self.inflated_size.to_bytes(4, byteorder="little"))
            self.zlibdata = zlib.compress(data.getbuffer())
            fd.write(self.zlibdata)

    def Dump(self, filename: str) -> None:
        with codecs.open(filename, "w", "utf-8") as fd:
            for entry in self.entries:
                fd.write(f"{entry.key.string}={entry.value.string}\n")

    def FromTextFile(self, filename: str) -> None:
        with codecs.open(filename, "r", "utf-8") as fd:
            data = fd.read()
            regex = re.compile(r"((?:.*_).*)=(.*(?:[^=]*\n)*)")
            matches = regex.findall(data)
            for match in matches:
                self[match[0]] = match[1].strip()

    # private
    def __ParseFile(self) -> None:
        self.data: io.BytesIO = io.BytesIO(zlib.decompress(self.zlibdata))
        self.entry_count: int = ByteReader.ReadUint32BE(self.data)

        while len(self.entries) < self.entry_count:
            self.entries.append(Entry.FromBytesIO(self.data))

    def __WriteUint32BE(self, number: int) -> bytes:
        return number.to_bytes(4, byteorder="big")

    # overrides
    def __setitem__(self, key: str, value: str) -> None:
        # Check if entry exists and update if it does
        for entry in self.entries:
            if entry.key.string == key:
                entry.SetValue(value)
                return
        
        # Add new entry if not found
        self.entries.append(Entry.FromKeyValuePair(key, value))
        self.entry_count += 1

    def __getitem__(self, key: str) -> Optional[str]:
        for entry in self.entries:
            if entry.key.string == key:
                return entry.value.string
        return None


class LangBinHandler:
    """
    Handles language.bin files for the Brawlhalla modloader
    """
    def __init__(self):
        self.language_file_paths = []
        self.language_original_paths = {}
        self.language_backed_up = {}
        self.cache_path = os.path.join(MODLOADER_CACHE_PATH, MODLOADER_CACHE_FILES_FOLDER)
        
        # Find language files
        for file_name, file_path in BRAWLHALLA_FILES.items():
            if file_name.startswith("language.") and file_name.endswith(".bin"):
                self.language_file_paths.append(file_path)
                self.language_original_paths[file_name] = file_path
                self.language_backed_up[file_name] = False
    
    def backup_original_files(self):
        """Back up original language.bin files"""
        for file_name, file_path in self.language_original_paths.items():
            if not self.language_backed_up[file_name]:
                backup_file_path = os.path.join(self.cache_path, file_name)
                
                if not os.path.exists(backup_file_path):
                    os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
                    shutil.copy2(file_path, backup_file_path)
                
                self.language_backed_up[file_name] = True
    
    def apply_mod_language_changes(self, mod_lang_file_path: str, mod_hash: str) -> bool:
        """
        Apply language changes from a mod language.bin file
        
        Args:
            mod_lang_file_path: Path to the mod's language.bin file
            mod_hash: Hash of the mod
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Determine which game language file to modify
            target_file_name = os.path.basename(mod_lang_file_path)
            target_game_file_path = self.language_original_paths.get(target_file_name)
            
            if not target_game_file_path:
                SendNotification(NotificationType.Error, f"Language file {target_file_name} not found in game directory")
                return False
                
            # Check if the target file exists in the game directory
            if not os.path.exists(target_game_file_path):
                SendNotification(NotificationType.Error, f"Language file {target_file_name} not found at path: {target_game_file_path}")
                return False
            
            # Back up the original files before modifying
            self.backup_original_files()
            
            # Load the mod language file
            mod_lang_file = LangFile(mod_lang_file_path)
            
            # Load the original game language file
            game_lang_file = LangFile(target_game_file_path)
            
            # Apply only the changes from the mod file to the game file
            modified = False
            
            # Log what we're about to do
            SendNotification(NotificationType.Debug, f"Applying language changes from mod {mod_hash}")
            
            # Apply each change in the mod file to the game file
            for mod_entry in mod_lang_file.entries:
                key = mod_entry.key.string
                value = mod_entry.value.string
                
                # Check if this key exists in the game file and has a different value
                original_value = game_lang_file[key]
                if original_value is not None and original_value != value:
                    # Only apply the change if the value is different
                    game_lang_file[key] = value
                    modified = True
                    SendNotification(NotificationType.Debug, f"Changed language key: {key}")
            
            # Save the modified game file if changes were made
            if modified:
                game_lang_file.Save(target_game_file_path)
                SendNotification(NotificationType.Success, f"Applied language changes from mod {mod_hash}")
            else:
                SendNotification(NotificationType.Warning, f"No language changes to apply from mod {mod_hash}")
            
            return True
            
        except Exception as e:
            SendNotification(NotificationType.Error, f"Error applying language changes: {str(e)}")
            return False
    
    def restore_original_file(self, file_name: str) -> bool:
        """
        Restore an original language file
        
        Args:
            file_name: The language file name to restore
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if file_name not in self.language_original_paths:
                return False
                
            original_path = os.path.join(self.cache_path, file_name)
            target_path = self.language_original_paths[file_name]
            
            if os.path.exists(original_path):
                shutil.copy2(original_path, target_path)
                return True
            
            return False
        except Exception:
            return False
    
    def restore_all_original_files(self) -> bool:
        """
        Restore all original language files
        
        Returns:
            bool: True if successful, False otherwise
        """
        success = True
        for file_name in self.language_original_paths.keys():
            if not self.restore_original_file(file_name):
                success = False
        return success


# Singleton instance
lang_bin_handler = LangBinHandler()


























