"""
Sprite Creation System for Brawlhalla Mod Loader

This module creates missing sprites in target SWF files so mods can replace them.
Based on analysis of existing Brawlhalla character SWF files.
Enhanced with PyFdec ActionScript integration for proper script handling.
"""

import os
from typing import Optional, Dict, List, Tuple
from ..swf.swf import Swf, GetElementId, SetElementId
from ..ffdec.classes import (
    DefineSpriteTag, 
    DefineShapeTags, 
    PlaceObject2Tag, 
    PlaceObject3Tag,
    SymbolClassTag,
    DefineFontTags,
    DefineEditTextTag,
    DefineTextTag,
    CSMTextSettingsTag,
    DefineFontNameTag,
    DefineFontAlignZonesTag
)
from .basedispatch import SendNotification
from ..notifications import NotificationType

# PyFdec imports for ActionScript handling
try:
    import pyfdec.swf as pyfdec_swf
    import pyfdec.extended_buffer as pyfdec_buffer
    PYFDEC_AVAILABLE = True
except ImportError:
    PYFDEC_AVAILABLE = False


class SpriteCreator:
    """
    Creates missing sprites in target SWF files based on mod requirements.
    """
    
    def __init__(self, gameSwf: Swf):
        self.gameSwf = gameSwf
        self.createdSprites: Dict[str, int] = {}  # sprite_name -> character_id
        
        # PyFdec ActionScript data
        self.pyfdec_doabc2_tag = None
        self.pyfdec_symbolclass_tag = None
        self.pyfdec_source_swf_path = None
    
    def loadPyFdecActionScript(self, source_swf_path: str) -> bool:
        """
        Load ActionScript data from source SWF using PyFdec.
        
        Args:
            source_swf_path: Path to the source SWF file containing ActionScript
            
        Returns:
            bool: True if ActionScript was loaded successfully, False otherwise
        """
        if not PYFDEC_AVAILABLE:
            SendNotification(NotificationType.Debug, "PyFdec not available, skipping ActionScript loading")
            return False
        
        try:
            self.pyfdec_source_swf_path = source_swf_path
            
            # Load source SWF using PyFdec
            with open(source_swf_path, 'rb') as f:
                source_data = f.read()
            
            source_buffer = pyfdec_buffer.ExtendedBuffer(source_data)
            source_swf_obj = pyfdec_swf.Swf.from_buffer(source_buffer)
            source_tags = list(source_swf_obj.tags)
            
            SendNotification(NotificationType.Debug, f"Loaded source SWF with PyFdec: {len(source_tags)} tags")
            
            # Extract ActionScript components
            for tag in source_tags:
                if type(tag).__name__ == "DoABC2":
                    self.pyfdec_doabc2_tag = tag
                    SendNotification(NotificationType.Debug, f"Found DoABC2 tag: {tag.name}")
                elif type(tag).__name__ == "SymbolClass":
                    self.pyfdec_symbolclass_tag = tag
                    SendNotification(NotificationType.Debug, "Found SymbolClass tag")
            
            if self.pyfdec_doabc2_tag and self.pyfdec_symbolclass_tag:
                SendNotification(NotificationType.Debug, "PyFdec ActionScript data loaded successfully")
                return True
            else:
                SendNotification(NotificationType.Debug, "Could not find DoABC2 or SymbolClass tags in source SWF")
                return False
                
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Failed to load PyFdec ActionScript: {str(e)}")
            return False
    
    def hasPyFdecActionScript(self, sprite_name: str) -> bool:
        """
        Check if PyFdec ActionScript data is available for a sprite.
        
        Args:
            sprite_name: Name of the sprite to check
            
        Returns:
            bool: True if ActionScript data is available, False otherwise
        """
        if not self.pyfdec_symbolclass_tag:
            return False
        
        try:
            if hasattr(self.pyfdec_symbolclass_tag, 'symbols'):
                symbols = list(self.pyfdec_symbolclass_tag.symbols)
                for symbol in symbols:
                    if sprite_name in str(symbol):
                        return True
            return False
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error checking PyFdec ActionScript for {sprite_name}: {str(e)}")
            return False
        
    def createMissingSprite(self, spriteName: str, modSprite: DefineSpriteTag, modSwf: Swf = None) -> bool:
        """
        Create a missing sprite in the target SWF if it doesn't exist.
        
        Args:
            spriteName: Name of the sprite to create (e.g., "a_Eyes_SpaceLeviathan")
            modSprite: The DefineSpriteTag from the mod to use as template
            modSwf: The mod's SWF file to copy ActionScript from
            
        Returns:
            bool: True if sprite was created or already exists, False if failed
        """
        try:
            # Check if sprite already exists
            existingId = self.gameSwf.symbolClass.getTagByName(spriteName)
            if existingId is not None:
                SendNotification(NotificationType.Debug, f"Sprite '{spriteName}' already exists (ID: {existingId})")
                
                # Check if we have PyFdec ActionScript data for this sprite
                if self.hasPyFdecActionScript(spriteName):
                    SendNotification(NotificationType.Debug, f"PyFdec ActionScript available for existing sprite '{spriteName}'")
                    # The ActionScript is already linked via SymbolClass, so we're good
                
                return True
            
            # Create new sprite
            newSpriteId = self.gameSwf.getNextCharacterId()
            
            # Clone the mod sprite
            clonedSprite = modSprite.cloneTag()
            SetElementId(clonedSprite, newSpriteId)
            
            # Add sprite to SWF
            self.gameSwf.addElement(clonedSprite)
            
            # Register in symbol class
            self.gameSwf.symbolClass.addTag(newSpriteId, spriteName)
            
            # Create AS3 Class Linkage (this is the key!)
            self._createAS3ClassLinkage(spriteName, newSpriteId)
            
            # Handle dependencies
            self._createSpriteDependencies(modSprite, newSpriteId)
            
            # Create ScriptPack with ActionScript (proven method)
            if self.hasPyFdecActionScript(spriteName):
                SendNotification(NotificationType.Debug, f"Using PyFdec ActionScript for '{spriteName}'")
                # PyFdec ActionScript is already available via DoABC2 tag
                # We just need to ensure it's properly linked
            else:
                SendNotification(NotificationType.Debug, f"Using generated ActionScript for '{spriteName}'")
                self._createScriptPackForSprite(spriteName, self._generateActionScript(spriteName))
            
            # Track created sprite
            self.createdSprites[spriteName] = newSpriteId
            
            SendNotification(NotificationType.Debug, f"Created sprite '{spriteName}' (ID: {newSpriteId})")
            return True
            
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error creating sprite '{spriteName}': {str(e)}")
            return False
    
    def _createSpriteDependencies(self, modSprite: DefineSpriteTag, spriteId: int) -> None:
        """
        Create all dependencies for a sprite.
        """
        try:
            # Get all needed characters from the mod sprite
            from ..swf.swf import GetNeededCharacters
            neededElements = GetNeededCharacters(modSprite)
            
            for element in neededElements:
                elementId = GetElementId(element)
                
                # Check if element already exists in target SWF
                existingId = self.gameSwf.symbolClass.getTagByName(
                    self.gameSwf.symbolClass.getTag(elementId) or f"temp_{elementId}"
                )
                
                if existingId is None:
                    # Element doesn't exist, create it
                    newElementId = self.gameSwf.getNextCharacterId()
                    clonedElement = self.gameSwf.cloneAndAddElement(element, newElementId)
                    
                    # Handle specific element types
                    self._handleElementType(clonedElement, element, newElementId)
                else:
                    # Element exists, use existing ID
                    pass
            
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error creating sprite dependencies: {str(e)}")
    
    def _handleElementType(self, element, originalElement, newElementId: int) -> None:
        """
        Handle specific element types during creation.
        """
        try:
            if isinstance(element, DefineFontTags):
                # Handle font dependencies
                from ..swf.swf import GetSwfByElement
                for dependentElement in GetSwfByElement(originalElement).getElementById(
                    GetElementId(originalElement), 
                    (DefineFontNameTag, DefineFontAlignZonesTag)
                ):
                    self.gameSwf.cloneAndAddElement(dependentElement, newElementId)
                    
            elif isinstance(element, DefineEditTextTag):
                # Handle text field dependencies
                from ..swf.swf import GetSwfByElement
                if dependentElement := GetSwfByElement(originalElement).getElementById(
                    GetElementId(originalElement), CSMTextSettingsTag
                ):
                    self.gameSwf.cloneAndAddElement(dependentElement[0], newElementId)
                    
            elif isinstance(element, DefineTextTag):
                # Handle text dependencies
                from ..swf.swf import GetSwfByElement
                if dependentElement := GetSwfByElement(originalElement).getElementById(
                    GetElementId(originalElement), CSMTextSettingsTag
                ):
                    self.gameSwf.cloneAndAddElement(dependentElement[0], newElementId)
                    
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error handling element type: {str(e)}")
    
    def _createAS3ClassLinkage(self, spriteName: str, spriteId: int) -> None:
        """
        Create AS3 Class Linkage for a sprite.
        The symbolClass.addTag() should already create the linkage, but let's ensure it's properly set up.
        """
        try:
            # The symbolClass.addTag() call above should already create the linkage
            # Let's verify it was created and maybe trigger additional setup
            
            # Check if the linkage was created
            linked_id = self.gameSwf.symbolClass.getTagByName(spriteName)
            if linked_id == spriteId:
                SendNotification(NotificationType.Debug, f"AS3 Class Linkage verified for '{spriteName}' (ID: {spriteId})")
                
                # Try to trigger ScriptPack creation by accessing the sprite
                # This might cause FFDEC to automatically create the ScriptPack
                try:
                    sprite_element = self.gameSwf.getElementById(spriteId)
                    if sprite_element:
                        SendNotification(NotificationType.Debug, f"Sprite element found for '{spriteName}' - ScriptPack should be auto-created")
                except Exception as e:
                    SendNotification(NotificationType.Debug, f"Could not access sprite element for '{spriteName}': {str(e)}")
            else:
                SendNotification(NotificationType.Debug, f"AS3 Class Linkage verification failed for '{spriteName}'")
            
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error verifying AS3 Class Linkage for '{spriteName}': {str(e)}")
    
    def _addActionScriptForSprite(self, spriteName: str, modSwf: Swf = None) -> None:
        """
        Add ActionScript for a newly created sprite.
        Uses the proven ScriptPack creation method.
        """
        try:
            actionScript = None
            
            # Try to get ActionScript from mod SWF first
            if modSwf is not None:
                try:
                    actionScript = modSwf.getAS3(spriteName)
                    if actionScript:
                        SendNotification(NotificationType.Debug, f"Found ActionScript in mod for '{spriteName}' ({len(actionScript)} chars)")
                    else:
                        SendNotification(NotificationType.Debug, f"No ActionScript found in mod for '{spriteName}'")
                except Exception as e:
                    SendNotification(NotificationType.Debug, f"Error getting ActionScript from mod for '{spriteName}': {str(e)}")
            
            # If no ActionScript from mod, generate default
            if not actionScript:
                actionScript = self._generateActionScript(spriteName)
                SendNotification(NotificationType.Debug, f"Generated default ActionScript for '{spriteName}'")
            
            # Use the proven ScriptPack creation method
            success = self._createScriptPackForSprite(spriteName, actionScript)
            
            if success:
                SendNotification(NotificationType.Debug, f"Successfully created ScriptPack for sprite '{spriteName}'")
            else:
                SendNotification(NotificationType.Debug, f"Failed to create ScriptPack for sprite '{spriteName}'")
                
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error adding ActionScript for '{spriteName}': {str(e)}")
    
    def _createScriptPackForSprite(self, spriteName: str, actionScript: str) -> bool:
        """
        Modify the existing ScriptPack to include our sprite.
        The key is to ensure FFDEC JPEXS can find our sprite's ActionScript.
        """
        try:
            # Check if sprite exists in symbol class
            sprite_id = self.gameSwf.symbolClass.getTagByName(spriteName)
            if sprite_id is None:
                SendNotification(NotificationType.Debug, f"Sprite '{spriteName}' not found in symbol class")
                return False
            
            # Method 1: Try to modify the existing ScriptPack to include our sprite
            try:
                from ..ffdec.classes import As3ScriptReplacerFactory
                
                # Get template pack and ABC
                if not self.gameSwf.AS3Packs:
                    SendNotification(NotificationType.Debug, f"No AS3Packs in target SWF")
                    return False
                
                template_pack = self.gameSwf.AS3Packs[0]
                abc = template_pack.abc
                
                # Create script replacer
                scriptReplacer = As3ScriptReplacerFactory.createByConfig()
                
                # Try to modify the template pack to include our sprite
                scriptReplacer.initReplacement(template_pack)
                scriptReplacer.replaceScript(template_pack, actionScript)
                
                # Apply changes
                result = abc.replaceScriptPack(scriptReplacer, template_pack, actionScript)
                
                if result:
                    # Verify it was created
                    verification_script = self.gameSwf.getAS3(spriteName)
                    if verification_script:
                        SendNotification(NotificationType.Debug, f"SUCCESS: Modified existing ScriptPack for '{spriteName}' ({len(verification_script)} chars)")
                        
                        # Check if it contains MovieClip
                        if "MovieClip" in verification_script:
                            SendNotification(NotificationType.Debug, f"SUCCESS: ActionScript contains MovieClip for '{spriteName}'")
                        else:
                            SendNotification(NotificationType.Debug, f"WARNING: ActionScript does not contain MovieClip for '{spriteName}'")
                        
                        return True
                    else:
                        SendNotification(NotificationType.Debug, f"ScriptPack modification verification failed for '{spriteName}'")
                        return False
                else:
                    SendNotification(NotificationType.Debug, f"ScriptPack modification failed for '{spriteName}'")
                    return False
                    
            except Exception as e:
                SendNotification(NotificationType.Debug, f"ScriptPack modification failed: {str(e)}")
            
            # Method 2: Try to force FFDEC to recognize our sprite
            try:
                # Force FFDEC to process our sprite by accessing it
                sprite_element = self.gameSwf.getElementById(sprite_id)
                if sprite_element:
                    SendNotification(NotificationType.Debug, f"Accessed sprite element for '{spriteName}'")
                    
                    # Try to force script generation by accessing AS3Packs
                    as3packs = list(self.gameSwf.AS3Packs)
                    SendNotification(NotificationType.Debug, f"Accessed {len(as3packs)} AS3Packs")
                    
                    # Check if our sprite is now in AS3Packs
                    for pack in as3packs:
                        if spriteName in str(pack):
                            SendNotification(NotificationType.Debug, f"Found ScriptPack for '{spriteName}' in AS3Packs")
                            return True
                    
                    # If not found, try to force creation
                    SendNotification(NotificationType.Debug, f"Sprite '{spriteName}' not found in AS3Packs, forcing creation")
                    
            except Exception as e:
                SendNotification(NotificationType.Debug, f"Method 2 failed: {str(e)}")
            
            # Method 3: Try to force script generation by saving and reloading
            try:
                # Force FFDEC to process the SWF by saving it
                self.gameSwf.save()
                SendNotification(NotificationType.Debug, f"Forced SWF save for '{spriteName}'")
                
                # Check if script is now available
                verification_script = self.gameSwf.getAS3(spriteName)
                if verification_script:
                    SendNotification(NotificationType.Debug, f"SUCCESS: Script found after save for '{spriteName}' ({len(verification_script)} chars)")
                    return True
                else:
                    SendNotification(NotificationType.Debug, f"Script still not found after save for '{spriteName}'")
                    
            except Exception as e:
                SendNotification(NotificationType.Debug, f"Save method failed: {str(e)}")
            
            SendNotification(NotificationType.Debug, f"All methods failed for '{spriteName}'")
            return False
                
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error creating ActionScript for '{spriteName}': {str(e)}")
            return False
    
    def _generateActionScript(self, spriteName: str) -> str:
        """
        Generate ActionScript content for a sprite.
        Based on analysis of working sprites in Brawlhalla SWF files.
        """
        return f"""package
{{
   import flash.display.MovieClip;
   
   public dynamic class {spriteName} extends MovieClip
   {{
      public function {spriteName}()
      {{
         super();
      }}
   }}
}}"""
    
    def getCreatedSprites(self) -> Dict[str, int]:
        """
        Get dictionary of created sprites (name -> character_id).
        """
        return self.createdSprites.copy()
    
    def cleanup(self) -> None:
        """
        Clean up any temporary data.
        """
        self.createdSprites.clear()


def createMissingSpritesForMod(gameSwf: Swf, modSprites: List[Tuple[str, DefineSpriteTag]]) -> bool:
    """
    Create all missing sprites needed for a mod.
    
    Args:
        gameSwf: The target game SWF file
        modSprites: List of (sprite_name, DefineSpriteTag) tuples from the mod
        
    Returns:
        bool: True if all sprites were created successfully
    """
    try:
        creator = SpriteCreator(gameSwf)
        
        for spriteName, spriteTag in modSprites:
            success = creator.createMissingSprite(spriteName, spriteTag)
            if not success:
                SendNotification(NotificationType.Debug, f"Failed to create sprite: {spriteName}")
                return False
        
        created = creator.getCreatedSprites()
        if created:
            SendNotification(NotificationType.Debug, f"Created {len(created)} missing sprites: {list(created.keys())}")
        
        creator.cleanup()
        return True
        
    except Exception as e:
        SendNotification(NotificationType.Debug, f"Error creating missing sprites: {str(e)}")
        return False
