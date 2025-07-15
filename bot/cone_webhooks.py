import discord
import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ConeWebhookManager:
    def __init__(self):
        """Initialize webhook manager for coned users."""
        self.user_webhooks = {}  # user_id: webhook
        self.webhook_channels = {}  # channel_id: [user_ids using webhooks in this channel]
        
    async def get_webhook_for_user(self, channel: discord.TextChannel, user: discord.Member) -> Optional[discord.Webhook]:
        """Get or create a webhook for a coned user."""
        try:
            user_id = str(user.id)
            
            # Check if we already have a webhook for this user
            if user_id in self.user_webhooks:
                webhook = self.user_webhooks[user_id]
                
                # Verify webhook still exists and update it
                try:
                    await webhook.edit(name=user.display_name, avatar=await self._get_avatar_bytes(user))
                    return webhook
                except discord.NotFound:
                    # Webhook was deleted, remove from our cache
                    await self._cleanup_user_webhook(user_id)
                except Exception as e:
                    logger.warning(f"Failed to update webhook for user {user_id}: {e}")
            
            # Check webhook limits before creating new one
            if not await self._check_webhook_limits(channel):
                logger.warning(f"Webhook limit reached for channel {channel.id}, cleaning up oldest")
                await self._cleanup_oldest_webhook(channel)
            
            # Create new webhook
            avatar_bytes = await self._get_avatar_bytes(user)
            webhook = await channel.create_webhook(
                name=user.display_name,
                avatar=avatar_bytes,
                reason=f"Cone effect for {user.display_name}"
            )
            
            # Store webhook
            self.user_webhooks[user_id] = webhook
            
            # Track channel usage
            channel_id = str(channel.id)
            if channel_id not in self.webhook_channels:
                self.webhook_channels[channel_id] = []
            self.webhook_channels[channel_id].append(user_id)
            
            logger.info(f"Created cone webhook for user {user.display_name} in channel {channel.name}")
            return webhook
            
        except discord.Forbidden:
            logger.error(f"No permission to create webhooks in channel {channel.name}")
            return None
        except Exception as e:
            logger.error(f"Error creating webhook for user {user.display_name}: {e}")
            return None
    
    async def send_cone_message(self, user: discord.Member, channel: discord.TextChannel, content: str) -> bool:
        """Send a message as a coned user via webhook."""
        try:
            webhook = await self.get_webhook_for_user(channel, user)
            if not webhook:
                return False
            
            # Send message via webhook
            await webhook.send(
                content=content,
                username=user.display_name,
                avatar_url=user.avatar.url if user.avatar else None,
                wait=False
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending cone message for user {user.display_name}: {e}")
            return False
    
    async def cleanup_user_webhook(self, user_id: str) -> bool:
        """Clean up webhook when user is unconed."""
        return await self._cleanup_user_webhook(user_id)
    
    async def _cleanup_user_webhook(self, user_id: str) -> bool:
        """Internal method to clean up a user's webhook."""
        try:
            if user_id in self.user_webhooks:
                webhook = self.user_webhooks[user_id]
                
                # Find and remove from channel tracking
                for channel_id, user_list in self.webhook_channels.items():
                    if user_id in user_list:
                        user_list.remove(user_id)
                        break
                
                # Delete webhook
                try:
                    await webhook.delete(reason="User unconed")
                except discord.NotFound:
                    pass  # Already deleted
                
                # Remove from cache
                del self.user_webhooks[user_id]
                
                logger.info(f"Cleaned up webhook for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error cleaning up webhook for user {user_id}: {e}")
            
        return False
    
    async def _check_webhook_limits(self, channel: discord.TextChannel) -> bool:
        """Check if we can create more webhooks in this channel."""
        try:
            existing_webhooks = await channel.webhooks()
            
            # Discord allows 10 webhooks per channel, leave some buffer
            return len(existing_webhooks) < 8
            
        except Exception as e:
            logger.error(f"Error checking webhook limits for channel {channel.name}: {e}")
            return False
    
    async def _cleanup_oldest_webhook(self, channel: discord.TextChannel):
        """Clean up the oldest webhook in a channel to make room."""
        try:
            channel_id = str(channel.id)
            if channel_id not in self.webhook_channels or not self.webhook_channels[channel_id]:
                return
            
            # Get oldest user (first in list)
            oldest_user_id = self.webhook_channels[channel_id][0]
            await self._cleanup_user_webhook(oldest_user_id)
            
        except Exception as e:
            logger.error(f"Error cleaning up oldest webhook in channel {channel.name}: {e}")
    
    async def _get_avatar_bytes(self, user: discord.Member) -> Optional[bytes]:
        """Get user avatar as bytes for webhook creation."""
        try:
            if user.avatar:
                return await user.avatar.read()
            else:
                # Use default Discord avatar
                return None
        except Exception as e:
            logger.warning(f"Failed to get avatar for user {user.display_name}: {e}")
            return None
    
    async def send_fallback_message(self, channel: discord.TextChannel, user: discord.Member, content: str) -> bool:
        """Send fallback message using embeds when webhooks fail."""
        try:
            embed = discord.Embed(
                description=content,
                color=user.color or discord.Color.default()
            )
            embed.set_author(
                name=user.display_name,
                icon_url=user.avatar.url if user.avatar else None
            )
            embed.set_footer(text="👻 Message transformed by Ghost")
            
            await channel.send(embed=embed)
            return True
            
        except Exception as e:
            logger.error(f"Error sending fallback message: {e}")
            return False
    
    async def cleanup_all_webhooks(self):
        """Clean up all webhooks (call when bot shuts down)."""
        logger.info("Cleaning up all cone webhooks...")
        
        user_ids = list(self.user_webhooks.keys())
        for user_id in user_ids:
            await self._cleanup_user_webhook(user_id)
            
        logger.info(f"Cleaned up {len(user_ids)} cone webhooks")
    
    def get_stats(self) -> Dict[str, int]:
        """Get webhook statistics."""
        return {
            "active_webhooks": len(self.user_webhooks),
            "channels_with_webhooks": len(self.webhook_channels)
        } 