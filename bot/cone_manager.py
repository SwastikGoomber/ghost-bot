from datetime import datetime, timedelta
import re
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ConeManager:
    def __init__(self, state_manager=None):
        """Initialize cone manager with state manager integration."""
        self.state_manager = state_manager
        self.active_cones = {}  # user_id: cone_data for quick access
        
    async def add_cone(self, user_id: str, effect: str, duration: str = "5 minutes", condition: Optional[str] = None) -> bool:
        """Add a cone effect to a user."""
        try:
            # Parse duration
            expires_at = self._parse_duration(duration)
            
            cone_data = {
                "effect": effect,
                "expires_at": expires_at,
                "condition": condition,
                "created_at": datetime.utcnow()
            }
            
            # Store in state manager
            if self.state_manager:
                # Find user in state manager and add cone data
                for stored_user_id, user_state in self.state_manager.users.items():
                    if stored_user_id == user_id or any(
                        platform_data.get('user_id') == user_id 
                        for platform_data in user_state.identifiers.values()
                    ):
                        user_state.cone = cone_data
                        await self.state_manager.save_states()
                        break
            
            # Cache locally
            self.active_cones[user_id] = cone_data
            
            logger.info(f"Added cone '{effect}' to user {user_id} until {expires_at}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding cone to user {user_id}: {e}")
            return False
    
    async def remove_cone(self, user_id: str, reason: str = "manual") -> bool:
        """Remove cone effect from a user."""
        try:
            # Remove from state manager
            if self.state_manager:
                # Find user in state manager and remove cone data
                for stored_user_id, user_state in self.state_manager.users.items():
                    if stored_user_id == user_id or any(
                        platform_data.get('user_id') == user_id 
                        for platform_data in user_state.identifiers.values()
                    ):
                        if hasattr(user_state, 'cone'):
                            delattr(user_state, 'cone')
                        await self.state_manager.save_states()
                        break
            
            # Remove from cache
            if user_id in self.active_cones:
                effect = self.active_cones[user_id]["effect"]
                del self.active_cones[user_id]
                logger.info(f"Removed cone '{effect}' from user {user_id} - {reason}")
                return True
                
        except Exception as e:
            logger.error(f"Error removing cone from user {user_id}: {e}")
            
        return False
    
    async def is_coned(self, user_id: str) -> bool:
        """Check if a user is currently coned."""
        # Check cache first
        if user_id in self.active_cones:
            cone_data = self.active_cones[user_id]
            
            # Check if expired
            if datetime.utcnow() > cone_data["expires_at"]:
                await self.remove_cone(user_id, "expired")
                return False
                
            return True
            
        # Check state manager if not in cache
        if self.state_manager:
            # Find user in state manager and check cone data
            for stored_user_id, user_state in self.state_manager.users.items():
                if stored_user_id == user_id or any(
                    platform_data.get('user_id') == user_id 
                    for platform_data in user_state.identifiers.values()
                ):
                    cone_data = getattr(user_state, 'cone', None)
                    
                    if cone_data and datetime.utcnow() <= cone_data["expires_at"]:
                        # Add back to cache
                        self.active_cones[user_id] = cone_data
                        return True
                    elif cone_data:
                        # Expired, remove it
                        await self.remove_cone(user_id, "expired")
                    break
                
        return False
    
    async def get_cone_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cone data for a user."""
        if await self.is_coned(user_id):
            return self.active_cones.get(user_id)
        return None
    
    async def check_conditions(self, user_id: str, message_content: str) -> bool:
        """Check if cone conditions are met and remove if so."""
        cone_data = await self.get_cone_data(user_id)
        if not cone_data or not cone_data.get("condition"):
            return False
            
        condition = cone_data["condition"].lower()
        message_lower = message_content.lower()
        
        # Parse different condition types
        if condition.startswith("until they say"):
            # Extract the phrase they need to say
            match = re.search(r'until they say[:\s]*["\']?([^"\']+)["\']?', condition)
            if match:
                required_phrase = match.group(1).strip().lower()
                if required_phrase in message_lower:
                    await self.remove_cone(user_id, f"said '{required_phrase}'")
                    return True
                    
        elif "sorry" in condition:
            # Look for apology words
            apology_words = ["sorry", "apologize", "my bad", "forgive me", "i'm sorry"]
            if any(word in message_lower for word in apology_words):
                await self.remove_cone(user_id, "apologized")
                return True
                
        elif "please" in condition:
            # Look for politeness
            if "please" in message_lower:
                await self.remove_cone(user_id, "said please")
                return True
                
        return False
    
    async def cleanup_expired(self):
        """Clean up expired cones (call periodically)."""
        current_time = datetime.utcnow()
        expired_users = []
        
        for user_id, cone_data in self.active_cones.items():
            if current_time > cone_data["expires_at"]:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            await self.remove_cone(user_id, "expired")
            
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired cones")
    
    def _parse_duration(self, duration_str: str) -> datetime:
        """Parse duration string into datetime."""
        duration_str = duration_str.lower().strip()
        current_time = datetime.utcnow()
        
        # Handle "permanent" or "forever"
        if any(word in duration_str for word in ["permanent", "forever", "indefinite"]):
            return current_time + timedelta(days=365 * 10)  # 10 years
        
        # Extract number and unit
        match = re.search(r'(\d+)\s*(minute|min|hour|hr|day|week|month)s?', duration_str)
        if not match:
            # Default to 5 minutes if can't parse
            return current_time + timedelta(minutes=5)
            
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit in ['minute', 'min']:
            return current_time + timedelta(minutes=amount)
        elif unit in ['hour', 'hr']:
            return current_time + timedelta(hours=amount)
        elif unit == 'day':
            return current_time + timedelta(days=amount)
        elif unit == 'week':
            return current_time + timedelta(weeks=amount)
        elif unit == 'month':
            return current_time + timedelta(days=amount * 30)
        else:
            return current_time + timedelta(minutes=5)
    
    async def get_all_active_cones(self) -> Dict[str, Dict[str, Any]]:
        """Get all active cones for debugging/admin purposes."""
        await self.cleanup_expired()
        return self.active_cones.copy() 