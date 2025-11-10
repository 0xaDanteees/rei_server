from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

router = APIRouter(prefix="/avatars", tags=["avatars"])

class AvatarCustomization(BaseModel):
    partner_id: str
    customization: Dict[str, Any]
    pose: str = "Idle"

class EmotionReaction(BaseModel):
    partner_id: str
    emotion: str
    intensity: float = 1.0
    message: Optional[str] = None

class AvatarAsset(BaseModel):
    id: str
    name: str
    url: str
    category: str
    thumbnail: Optional[str] = None

# Default avatar configuration
DEFAULT_AVATAR_CONFIG = {
    "Head": {
        "asset": {
            "id": "head-001",
            "name": "Default Head",
            "url": "/Assets/Head.001.glb",
            "category": "Head"
        },
        "color": "#f5c6a5"
    },
    "Hair": {
        "asset": {
            "id": "hair-001", 
            "name": "Default Hair",
            "url": "/Assets/Hair.001.glb",
            "category": "Hair"
        },
        "color": "#8B4513"
    },
    "Eyes": {
        "asset": {
            "id": "eyes-001",
            "name": "Default Eyes", 
            "url": "/Assets/Eyes.001.glb",
            "category": "Eyes"
        },
        "color": "#4169E1"
    },
    "Outfit": {
        "asset": {
            "id": "outfit-001",
            "name": "Default Outfit",
            "url": "/Assets/Outfit.001.glb", 
            "category": "Outfit"
        },
        "color": "#FF69B4"
    }
}

@router.get("/{partner_id}")
async def get_avatar_config(partner_id: str):
    """Get avatar configuration for a partner"""
    try:
        # TODO: Replace with actual database query
        # For now, return default configuration
        return {
            "partner_id": partner_id,
            "customization": DEFAULT_AVATAR_CONFIG,
            "pose": "Idle",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get avatar config: {str(e)}")

@router.put("/{partner_id}")
async def update_avatar_config(partner_id: str, config: AvatarCustomization):
    """Update avatar configuration"""
    try:
        # TODO: Save to database
        # For now, just validate and return the config
        return {
            "partner_id": partner_id,
            "customization": config.customization,
            "pose": config.pose,
            "updated_at": datetime.now().isoformat(),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update avatar config: {str(e)}")

@router.post("/{partner_id}/reaction")
async def trigger_avatar_reaction(partner_id: str, reaction: EmotionReaction):
    """Trigger avatar reaction (for testing or manual triggers)"""
    try:
        # TODO: Broadcast reaction via WebSocket
        # For now, just return success
        return {
            "partner_id": partner_id,
            "emotion": reaction.emotion,
            "intensity": reaction.intensity,
            "message": reaction.message,
            "triggered_at": datetime.now().isoformat(),
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger reaction: {str(e)}")

@router.get("/{partner_id}/assets")
async def get_available_assets(partner_id: str, category: Optional[str] = None):
    """Get available avatar assets, optionally filtered by category"""
    try:
        # TODO: Replace with actual asset database
        available_assets = {
            "Hair": [
                {"id": "hair-001", "name": "Short Hair", "url": "/Assets/Hair.001.glb", "category": "Hair"},
                {"id": "hair-002", "name": "Long Hair", "url": "/Assets/Hair.002.glb", "category": "Hair"},
                {"id": "hair-003", "name": "Curly Hair", "url": "/Assets/Hair.003.glb", "category": "Hair"},
            ],
            "Eyes": [
                {"id": "eyes-001", "name": "Blue Eyes", "url": "/Assets/Eyes.001.glb", "category": "Eyes"},
                {"id": "eyes-002", "name": "Green Eyes", "url": "/Assets/Eyes.002.glb", "category": "Eyes"},
                {"id": "eyes-003", "name": "Brown Eyes", "url": "/Assets/Eyes.003.glb", "category": "Eyes"},
            ],
            "Outfit": [
                {"id": "outfit-001", "name": "Casual Outfit", "url": "/Assets/Outfit.001.glb", "category": "Outfit"},
                {"id": "outfit-002", "name": "Formal Outfit", "url": "/Assets/Outfit.002.glb", "category": "Outfit"},
                {"id": "outfit-003", "name": "Sport Outfit", "url": "/Assets/Outfit.003.glb", "category": "Outfit"},
            ]
        }
        
        if category:
            return available_assets.get(category, [])
        
        return available_assets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get assets: {str(e)}")

@router.get("/{partner_id}/poses")
async def get_available_poses(partner_id: str):
    """Get available avatar poses"""
    try:
        poses = [
            "Idle",
            "Chill", 
            "Cool",
            "Punch",
            "Ninja",
            "King",
            "Busy"
        ]
        return {"poses": poses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get poses: {str(e)}")

@router.post("/{partner_id}/randomize")
async def randomize_avatar(partner_id: str):
    """Randomize avatar appearance"""
    try:
        import random
        
        # Get available assets
        assets = await get_available_assets(partner_id)
        
        # Randomize configuration
        randomized_config = {}
        colors = ["#f5c6a5", "#d4a574", "#8b4513", "#654321", "#000000", "#daa520", "#ff6347", "#4169e1", "#228b22", "#8b008b", "#ff1493", "#ff69b4", "#00ced1", "#ffd700", "#ff4500"]
        
        for category, category_assets in assets.items():
            if category_assets:
                random_asset = random.choice(category_assets)
                random_color = random.choice(colors)
                randomized_config[category] = {
                    "asset": random_asset,
                    "color": random_color
                }
        
        # Update avatar with randomized config
        config = AvatarCustomization(
            partner_id=partner_id,
            customization=randomized_config,
            pose=random.choice(["Idle", "Chill", "Cool", "Punch", "Ninja", "King", "Busy"])
        )
        
        return await update_avatar_config(partner_id, config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to randomize avatar: {str(e)}")
