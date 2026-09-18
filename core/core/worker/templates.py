"""
Mod Templates System for Brawlhalla Mod Creator
Provides pre-configured templates for common mod types
"""

import os
import json
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ModTemplate:
    """Represents a mod template with its configuration"""
    name: str
    description: str
    category: str
    files: List[Dict[str, str]]  # List of files with their paths and content
    metadata: Dict[str, Any]  # Mod metadata (name, author, etc.)
    folder_structure: List[str]  # Required folder structure


class ModTemplateManager:
    """Manages mod templates and their creation"""
    
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, ModTemplate]:
        """Load all available mod templates"""
        templates = {}
        
        # Character Skin Template
        templates["character_skin"] = ModTemplate(
            name="Character Skin",
            description="Template for creating character skin mods",
            category="Character",
            files=[
                {
                    "path": "Gfx_Character.swf",
                    "content": "# Character Graphics SWF file\n# Replace with your character's graphics SWF"
                },
                {
                    "path": "Bones_Character.swf", 
                    "content": "# Character Bones SWF file\n# Replace with your character's bones SWF"
                },
                {
                    "path": "SFX_Character.swf",
                    "content": "# Character Sound Effects SWF file\n# Replace with your character's SFX SWF"
                },
                {
                    "path": "UI_Icons.swf",
                    "content": "# UI Icons SWF file\n# Replace with your character's UI icons SWF"
                }
            ],
            metadata={
                "name": "My Character Skin",
                "author": "Your Name",
                "version": "1.0.0",
                "description": "A custom character skin mod",
                "tags": ["character", "skin", "custom"],
                "gameVersion": "7.0.0"
            },
            folder_structure=[
                "Sound",
                "_previews",
                "languages"
            ]
        )
        
        # Audio Mod Template
        templates["audio_mod"] = ModTemplate(
            name="Audio Mod",
            description="Template for creating audio modification mods",
            category="Audio",
            files=[
                {
                    "path": "Sound/VOX_Announcer.bnk/130.wem",
                    "content": "# Announcer voice file\n# Replace with your custom announcer audio"
                },
                {
                    "path": "Sound/SPC_Character.bnk/175910.wem",
                    "content": "# Character voice file\n# Replace with your custom character audio"
                }
            ],
            metadata={
                "name": "My Audio Mod",
                "author": "Your Name", 
                "version": "1.0.0",
                "description": "Custom audio modifications",
                "tags": ["audio", "voice", "sound"],
                "gameVersion": "7.0.0"
            },
            folder_structure=[
                "Sound",
                "Sound/VOX_Announcer.bnk",
                "Sound/SPC_Character.bnk",
                "_previews"
            ]
        )
        
        # Language Mod Template
        templates["language_mod"] = ModTemplate(
            name="Language Mod",
            description="Template for creating language modification mods",
            category="Language",
            files=[
                {
                    "path": "languages/language.1.txt",
                    "content": "# English language file\n# Modify the text entries below\n\n# Character names\nCHARACTER_NAME_1=My Custom Character\n\n# UI text\nUI_TEXT_EXAMPLE=Custom UI Text\n"
                },
                {
                    "path": "languages/language.2.txt",
                    "content": "# Spanish language file\n# Modify the text entries below\n\n# Character names\nCHARACTER_NAME_1=Mi Personaje Personalizado\n\n# UI text\nUI_TEXT_EXAMPLE=Texto de UI Personalizado\n"
                }
            ],
            metadata={
                "name": "My Language Mod",
                "author": "Your Name",
                "version": "1.0.0", 
                "description": "Custom language modifications",
                "tags": ["language", "text", "localization"],
                "gameVersion": "7.0.0"
            },
            folder_structure=[
                "languages",
                "_previews"
            ]
        )
        
        # Complete Character Mod Template
        templates["complete_character"] = ModTemplate(
            name="Complete Character Mod",
            description="Template for creating complete character mods with graphics, audio, and language changes",
            category="Character",
            files=[
                {
                    "path": "Gfx_Character.swf",
                    "content": "# Character Graphics SWF file\n# Replace with your character's graphics SWF"
                },
                {
                    "path": "Bones_Character.swf",
                    "content": "# Character Bones SWF file\n# Replace with your character's bones SWF"
                },
                {
                    "path": "SFX_Character.swf",
                    "content": "# Character Sound Effects SWF file\n# Replace with your character's SFX SWF"
                },
                {
                    "path": "UI_Icons.swf",
                    "content": "# UI Icons SWF file\n# Replace with your character's UI icons SWF"
                },
                {
                    "path": "Sound/VOX_Announcer.bnk/130.wem",
                    "content": "# Announcer voice file\n# Replace with your character's announcer audio"
                },
                {
                    "path": "Sound/SPC_Character.bnk/175910.wem",
                    "content": "# Character voice file\n# Replace with your character's voice audio"
                },
                {
                    "path": "languages/language.1.txt",
                    "content": "# English language file\n# Modify the text entries below\n\n# Character names\nCHARACTER_NAME_1=My Custom Character\n\n# UI text\nUI_TEXT_EXAMPLE=Custom UI Text\n"
                }
            ],
            metadata={
                "name": "My Complete Character",
                "author": "Your Name",
                "version": "1.0.0",
                "description": "A complete character mod with graphics, audio, and language changes",
                "tags": ["character", "complete", "graphics", "audio", "language"],
                "gameVersion": "7.0.0"
            },
            folder_structure=[
                "Sound",
                "Sound/VOX_Announcer.bnk",
                "Sound/SPC_Character.bnk",
                "languages",
                "_previews"
            ]
        )
        
        return templates
    
    def get_template(self, template_id: str) -> ModTemplate:
        """Get a specific template by ID"""
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> Dict[str, ModTemplate]:
        """Get all available templates"""
        return self.templates
    
    def get_templates_by_category(self, category: str) -> Dict[str, ModTemplate]:
        """Get templates filtered by category"""
        return {k: v for k, v in self.templates.items() if v.category == category}
    
    def create_mod_from_template(self, template_id: str, mod_name: str, mod_path: str, 
                                custom_metadata: Dict[str, Any] = None) -> bool:
        """Create a new mod from a template"""
        template = self.get_template(template_id)
        if not template:
            return False
        
        try:
            # Create mod directory
            os.makedirs(mod_path, exist_ok=True)
            
            # Create folder structure
            for folder in template.folder_structure:
                folder_path = os.path.join(mod_path, folder)
                os.makedirs(folder_path, exist_ok=True)
            
            # Create template files
            for file_info in template.files:
                file_path = os.path.join(mod_path, file_info["path"])
                file_dir = os.path.dirname(file_path)
                
                # Create directory if it doesn't exist
                if file_dir:
                    os.makedirs(file_dir, exist_ok=True)
                
                # Write file content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_info["content"])
            
            # Create cache file with metadata
            cache_data = template.metadata.copy()
            if custom_metadata:
                cache_data.update(custom_metadata)
            
            # Update name if provided
            if mod_name:
                cache_data["name"] = mod_name
            
            cache_path = os.path.join(mod_path, "_cache.json")
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error creating mod from template: {e}")
            return False
    
    def get_template_categories(self) -> List[str]:
        """Get all available template categories"""
        categories = set()
        for template in self.templates.values():
            categories.add(template.category)
        return sorted(list(categories))

























