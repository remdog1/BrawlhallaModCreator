"""
Automatic Sprite Placement System for Brawlhalla Mod Loader

This module automatically places newly created sprites on character timelines
by copying placement patterns from reference characters.
"""

import os
import shutil
from typing import Optional, Dict, List, Tuple
from ..swf.swf import Swf, GetElementId, SetElementId
from ..ffdec.classes import (
    DefineSpriteTag, 
    PlaceObject2Tag, 
    PlaceObject3Tag,
    SymbolClassTag
)
from .basedispatch import SendNotification
from ..notifications import NotificationType


class SpritePlacer:
    """
    Automatically places sprites on character timelines using reference characters.
    """
    
    def __init__(self, gameSwf: Swf):
        self.gameSwf = gameSwf
        self.placedSprites: Dict[str, int] = {}  # sprite_name -> depth
        self.backupCreated = False
        
    def createBackup(self) -> bool:
        """
        Create a backup of the SWF file before making changes.
        """
        try:
            backup_path = self.gameSwf.swfPath + ".placement_backup"
            if not os.path.exists(backup_path):
                shutil.copy2(self.gameSwf.swfPath, backup_path)
                self.backupCreated = True
                SendNotification(NotificationType.Debug, f"Created backup: {backup_path}")
                return True
            return True
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Failed to create backup: {str(e)}")
            return False
    
    def restoreBackup(self) -> bool:
        """
        Restore the SWF file from backup.
        """
        try:
            backup_path = self.gameSwf.swfPath + ".placement_backup"
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, self.gameSwf.swfPath)
                SendNotification(NotificationType.Debug, f"Restored from backup: {backup_path}")
                return True
            return False
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Failed to restore backup: {str(e)}")
            return False
    
    def findMainCharacterSprite(self) -> Optional[DefineSpriteTag]:
        """
        Find the main character sprite (the one that contains the timeline).
        """
        try:
            # Look for the main character sprite
            # It's usually the first DefineSprite or has a specific naming pattern
            for element in self.gameSwf.elementsList:
                if isinstance(element, DefineSpriteTag):
                    sprite_id = GetElementId(element)
                    sprite_name = self.gameSwf.symbolClass.getTag(sprite_id) if sprite_id else 'Unknown'
                    
                    # The main character sprite is usually the largest or first one
                    # We'll take the first DefineSprite we find
                    return element
            
            return None
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error finding main character sprite: {str(e)}")
            return None
    
    def getReferencePlacement(self, spriteType: str) -> Optional[Dict]:
        """
        Get placement information from a reference character.
        
        Args:
            spriteType: Type of sprite ('eyes', 'mouth', etc.)
            
        Returns:
            Dict with placement info or None
        """
        try:
            # Use Arbiter as reference character
            arbiter_path = r"C:\Program Files (x86)\Steam\steamapps\common\Brawlhalla\Gfx_Arbiter.swf"
            
            if not os.path.exists(arbiter_path):
                SendNotification(NotificationType.Debug, f"Reference character not found: {arbiter_path}")
                return None
            
            # Load Arbiter SWF
            arbiter_swf = Swf(arbiter_path)
            
            # Find the main character sprite
            main_sprite = None
            for element in arbiter_swf.elementsList:
                if isinstance(element, DefineSpriteTag):
                    main_sprite = element
                    break
            
            if not main_sprite:
                arbiter_swf.close()
                return None
            
            # Look for PlaceObject tags for the sprite type
            placement_info = None
            
            for tag in main_sprite.getTags().iterator():
                if isinstance(tag, (PlaceObject2Tag, PlaceObject3Tag)):
                    char_id = tag.characterId if hasattr(tag, 'characterId') else 0
                    if char_id > 0:
                        char_name = arbiter_swf.symbolClass.getTag(char_id) if char_id else 'Unknown'
                        
                        if spriteType.lower() in char_name.lower():
                            # Found matching sprite, extract placement info
                            placement_info = {
                                'depth': tag.depth if hasattr(tag, 'depth') else 1,
                                'characterId': char_id,
                                'tagType': 'PlaceObject2' if isinstance(tag, PlaceObject2Tag) else 'PlaceObject3',
                                'originalTag': tag
                            }
                            break
            
            arbiter_swf.close()
            return placement_info
            
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error getting reference placement: {str(e)}")
            return None
    
    def placeSpriteOnTimeline(self, spriteName: str, spriteId: int, spriteType: str) -> bool:
        """
        Place a sprite on the main character timeline.
        
        Args:
            spriteName: Name of the sprite to place
            spriteId: Character ID of the sprite
            spriteType: Type of sprite ('eyes', 'mouth', etc.)
            
        Returns:
            bool: True if placement was successful
        """
        try:
            # Find the main character sprite
            main_sprite = self.findMainCharacterSprite()
            if not main_sprite:
                SendNotification(NotificationType.Debug, "Could not find main character sprite")
                return False
            
            # Get reference placement info
            ref_info = self.getReferencePlacement(spriteType)
            if not ref_info:
                SendNotification(NotificationType.Debug, f"No reference placement found for {spriteType}")
                return False
            
            # Create a new PlaceObject tag
            if ref_info['tagType'] == 'PlaceObject2':
                place_tag = PlaceObject2Tag()
            else:
                place_tag = PlaceObject3Tag()
            
            # Set the placement properties
            place_tag.characterId = spriteId
            place_tag.depth = ref_info['depth']
            
            # Copy other properties from reference if available
            if hasattr(ref_info['originalTag'], 'placeFlagHasCharacter'):
                place_tag.placeFlagHasCharacter = True
            
            # Add the PlaceObject tag to the main sprite's first frame
            # This is a simplified approach - we add it to the timeline
            main_sprite.addTag(place_tag)
            
            # Track the placement
            self.placedSprites[spriteName] = ref_info['depth']
            
            SendNotification(NotificationType.Debug, f"Placed {spriteName} at depth {ref_info['depth']}")
            return True
            
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error placing sprite {spriteName}: {str(e)}")
            return False
    
    def placeAllCreatedSprites(self, createdSprites: Dict[str, int]) -> bool:
        """
        Place all created sprites on the timeline.
        
        Args:
            createdSprites: Dict of sprite_name -> sprite_id from SpriteCreator
            
        Returns:
            bool: True if all placements were successful
        """
        try:
            success_count = 0
            total_count = len(createdSprites)
            
            for sprite_name, sprite_id in createdSprites.items():
                # Determine sprite type from name
                sprite_type = 'unknown'
                if 'eyes' in sprite_name.lower() or 'eye' in sprite_name.lower():
                    sprite_type = 'eyes'
                elif 'mouth' in sprite_name.lower():
                    sprite_type = 'mouth'
                elif 'hair' in sprite_name.lower():
                    sprite_type = 'hair'
                
                if self.placeSpriteOnTimeline(sprite_name, sprite_id, sprite_type):
                    success_count += 1
            
            SendNotification(NotificationType.Debug, f"Placed {success_count}/{total_count} sprites on timeline")
            return success_count == total_count
            
        except Exception as e:
            SendNotification(NotificationType.Debug, f"Error placing sprites: {str(e)}")
            return False
    
    def getPlacedSprites(self) -> Dict[str, int]:
        """
        Get dictionary of placed sprites (name -> depth).
        """
        return self.placedSprites.copy()
    
    def cleanup(self) -> None:
        """
        Clean up any temporary data.
        """
        self.placedSprites.clear()


def placeSpritesAutomatically(gameSwf: Swf, createdSprites: Dict[str, int]) -> bool:
    """
    Automatically place created sprites on the character timeline.
    
    Args:
        gameSwf: The target game SWF file
        createdSprites: Dict of sprite_name -> sprite_id from SpriteCreator
        
    Returns:
        bool: True if placement was successful
    """
    try:
        placer = SpritePlacer(gameSwf)
        
        # Create backup first
        if not placer.createBackup():
            SendNotification(NotificationType.Debug, "Failed to create backup, skipping placement")
            return False
        
        # Place all sprites
        success = placer.placeAllCreatedSprites(createdSprites)
        
        if success:
            placed = placer.getPlacedSprites()
            if placed:
                SendNotification(NotificationType.Debug, f"Successfully placed sprites: {list(placed.keys())}")
        else:
            SendNotification(NotificationType.Debug, "Some sprite placements failed")
        
        placer.cleanup()
        return success
        
    except Exception as e:
        SendNotification(NotificationType.Debug, f"Error in automatic sprite placement: {str(e)}")
        return False



