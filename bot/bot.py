import os
import discord
from discord.ext import commands
from typing import Optional
from config import *
from collections import deque
from datetime import datetime, timedelta
import random
from state_manager import StateManager
from ai_handler import AIHandler
import traceback

# Get the guild ID from environment or config
DISCORD_GUILD_ID = os.getenv('DISCORD_GUILD_ID')

class CustomBot(commands.Bot):
    def __init__(self, state_manager: StateManager = None, ai_handler: AIHandler = None):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        
        self.ai_handler = ai_handler or AIHandler()
        self.state_manager = state_manager or StateManager(self.ai_handler)
        self.daily_requests = 0
        self.minute_requests = deque(maxlen=20)
        self.nap_until = None

    def extract_image_urls(self, message):
        """Extract image URLs from Discord message attachments"""
        image_urls = []
        
        if message.attachments:
            for attachment in message.attachments:
                # Check if attachment is an image
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']):
                    image_urls.append(attachment.url)
                    print(f"Found image attachment: {attachment.filename} -> {attachment.url}")
        
        return image_urls

    async def setup_hook(self):
        # Initialize state manager if using MongoDB
        if os.environ.get('MONGODB_URI'):
            await self.state_manager.load_states()

        # Register commands
        @self.tree.command(name="limits", description="Check remaining API limits and bot's state")
        async def limits(interaction: discord.Interaction):
            daily_remaining = max(0, 200 - self.daily_requests)
            minute_remaining = max(0, 20 - len(self.minute_requests))
            
            current_time = datetime.now()
            
            if self.daily_requests >= 200:
                status = "Sleeping until tomorrow!"
            elif self.nap_until and current_time < self.nap_until:
                minutes_left = max(0, (self.nap_until - current_time).seconds // 60)
                status = f"Taking a {minutes_left} minute nap!"
            else:
                while self.minute_requests and (current_time - self.minute_requests[0]).seconds > 60:
                    self.minute_requests.popleft()
                status = "Awake and ready!"

            await interaction.response.send_message(
                f"Status: {status}\n"
                f"Daily requests remaining: {daily_remaining}/200\n"
                f"Requests available this minute: {minute_remaining}/20"
            )

        @self.tree.command(name="unlink_accounts", description="Unlink your Discord and Twitch accounts")
        async def unlink_accounts(interaction: discord.Interaction):
            try:
                platform_key = f"discord_{interaction.user.id}"
                success = await self.state_manager.unlink_accounts(platform_key)
                if success:
                    await interaction.response.send_message(
                        "Your Discord and Twitch accounts have been unlinked. You can link them again using /link_twitch"
                    )
                else:
                    await interaction.response.send_message(
                        "No linked accounts found or error unlinking accounts."
                    )
            except Exception as e:
                print(f"Error in unlink_accounts: {e}")
                traceback.print_exc()
                await interaction.response.send_message("Failed to unlink accounts.")

        @self.tree.command(name="link_twitch", description="Link your Discord account with your Twitch account")
        async def link_twitch(interaction: discord.Interaction, twitch_username: str):
            try:
                success = await self.state_manager.create_link_request(
                    str(interaction.user.id), 
                    twitch_username
                )
                if success:
                    await interaction.response.send_message(
                        f"Link request created! Please type '!confirm_link' in {twitch_username}'s Twitch chat to complete the link."
                    )
                else:
                    await interaction.response.send_message("Failed to create link request.")
            except Exception as e:
                print(f"Error in link_twitch: {e}")
                traceback.print_exc()
                await interaction.response.send_message("Failed to create link request.")

        @self.tree.command(
            name="update_summary",
            description="Force update user relationship and conversation summaries"
        )
        async def update_summary(interaction: discord.Interaction, username: Optional[str] = None):
            await interaction.response.defer()
            
            try:
                platform_key = f"discord_{interaction.user.id}"
                
                if username:
                    temp_key = None
                    for key, state in self.state_manager.users.items():
                        platform_info = next(iter(state.identifiers.values()))
                        if platform_info['username'].lower() == username.lower():
                            temp_key = key
                            break
                    
                    if temp_key:
                        platform_key = temp_key
                    else:
                        await interaction.followup.send(f"Could not find user '{username}'")
                        return
                
                user_state = self.state_manager.users.get(platform_key)
                if not user_state:
                    await interaction.followup.send("Could not find user state")
                    return
                
                success, message = await self.state_manager.update_user_state(platform_key)
                target_user = username if username else interaction.user.name
                
                await interaction.followup.send(
                    f"✓ {message} ({target_user})" if success else f"✗ {message} ({target_user})"
                )
                
            except Exception as e:
                print(f"Error in update_summary: {e}")
                traceback.print_exc()
                try:
                    await interaction.followup.send("Failed to update summaries")
                except Exception as e2:
                    print(f"Failed to send error message: {e2}")

        @self.tree.command(
            name="cone_status",
            description="Check cone status for yourself or another user"
        )
        async def cone_status(interaction: discord.Interaction, username: Optional[str] = None):
            try:
                target_username = username or interaction.user.name
                
                # Try different identifiers for the target user
                if username:
                    # Looking up another user
                    target_identifiers = [username.lower()]
                else:
                    # Looking up self
                    target_identifiers = [
                        str(interaction.user.id),
                        interaction.user.name.lower(),
                        interaction.user.display_name.lower()
                    ]
                    if interaction.user.global_name:
                        target_identifiers.append(interaction.user.global_name.lower())
                
                # Check cone status
                status_found = False
                for identifier in target_identifiers:
                    if identifier:
                        status = self.ai_handler.get_cone_status(identifier, self.state_manager)
                        if status['message'] != f'{identifier} has never been coned':
                            await interaction.response.send_message(
                                f"**Cone Status for {target_username}:**\n{status['message']}"
                            )
                            status_found = True
                            break
                
                if not status_found:
                    await interaction.response.send_message(f"{target_username} has never been coned.")
                    
            except Exception as e:
                print(f"Error in cone_status: {e}")
                traceback.print_exc()
                try:
                    await interaction.response.send_message("Failed to check cone status.")
                except:
                    pass

        # TEMPORARY: Cone commands for testing expanded vocabulary
        @self.tree.command(
            name="cone",
            description="[TEMP] Apply a cone effect to a user (Testing expanded vocabulary)"
        )
        async def cone_user(
            interaction: discord.Interaction,
            user: discord.Member,
            effect: str = "shakespeare",
            duration: Optional[str] = None,
            condition: Optional[str] = None
        ):
            try:
                # Check permissions (only for bot owner/authorized users)
                authorized_user_ids = [533342015660883968]  # Replace with your Discord ID
                if interaction.user.id not in authorized_user_ids:
                    await interaction.response.send_message("❌ You don't have permission to use cone commands.", ephemeral=True)
                    return
                
                # Validate effect
                valid_effects = ['uwu', 'pirate', 'shakespeare', 'bardify', 'valley', 'slayspeak', 'genz', 
                               'brainrot', 'corporate', 'scrum', 'caveman', 'unga', 'drunk', 'drunkard', 
                               'emoji', 'linkedin', 'existential', 'crisis', 'polite', 'canadian', 
                               'conspiracy', 'vsauce', 'british', 'bri', 'censor', 'oni']
                
                if effect.lower() not in valid_effects:
                    await interaction.response.send_message(f"❌ Invalid effect. Available: {', '.join(valid_effects)}", ephemeral=True)
                    return
                
                # Apply cone using the existing AI handler function
                result = self.ai_handler.cone_user(
                    str(user.id),  # Use Discord ID as identifier
                    effect.lower(),
                    duration=duration,
                    condition=condition,
                    admin_user=interaction.user.name,
                    state_manager=self.state_manager
                )
                
                if result['success']:
                    await interaction.response.send_message(f"✅ {result['message']}")
                else:
                    await interaction.response.send_message(f"❌ {result['message']}")
                    
            except Exception as e:
                print(f"Error in cone command: {e}")
                traceback.print_exc()
                await interaction.response.send_message("❌ Failed to apply cone effect.", ephemeral=True)

        @self.tree.command(
            name="uncone",
            description="[TEMP] Remove cone effect from a user"
        )
        async def uncone_user(interaction: discord.Interaction, user: discord.Member):
            try:
                # Check permissions (only for bot owner/authorized users)
                authorized_user_ids = [533342015660883968]  # Replace with your Discord ID
                if interaction.user.id not in authorized_user_ids:
                    await interaction.response.send_message("❌ You don't have permission to use cone commands.", ephemeral=True)
                    return
                
                # Remove cone using the existing AI handler function
                result = self.ai_handler.uncone_user(
                    str(user.id),  # Use Discord ID as identifier
                    admin_user=interaction.user.name,
                    state_manager=self.state_manager
                )
                
                if result['success']:
                    await interaction.response.send_message(f"✅ {result['message']}")
                else:
                    await interaction.response.send_message(f"❌ {result['message']}")
                    
            except Exception as e:
                print(f"Error in uncone command: {e}")
                traceback.print_exc()
                await interaction.response.send_message("❌ Failed to remove cone effect.", ephemeral=True)

        # Sync commands
        print("\n=== Syncing Discord Commands ===")
        try:
            print("Syncing commands globally...")
            global_synced = await self.tree.sync()
            print(f"Global commands: {[cmd.name for cmd in global_synced]}")
            
            if DISCORD_GUILD_ID:
                try:
                    guild_id = int(DISCORD_GUILD_ID)
                    dev_guild = discord.Object(id=guild_id)
                    guild_synced = await self.tree.sync(guild=dev_guild)
                    print(f"Guild commands: {[cmd.name for cmd in guild_synced]}")
                except ValueError:
                    print(f"Invalid guild ID: {DISCORD_GUILD_ID}")
                except Exception as e:
                    print(f"Error syncing to guild: {e}")
            
        except Exception as e:
            print(f"Error syncing commands: {e}")
            traceback.print_exc()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def on_message(self, message):
        if message.author == self.user:
            return

        try:
            platform_key = f"discord_{message.author.id}"

            if message.content.lower().startswith('!'):
                if message.content.lower() == "!update_summary":
                    try:
                        updated, msg = await self.state_manager.update_user_state(platform_key)
                        await message.reply(msg)
                    except Exception as e:
                        print(f"Error in update_summary command: {e}")
                        traceback.print_exc()
                        await message.reply("Failed to update summaries.")
                    return

            name_mentions = ['ghost', 'ghosty']
            message_lower = message.content.lower()
            contains_name = any(name in message_lower for name in name_mentions)

            should_respond = (
                isinstance(message.channel, discord.DMChannel) or
                self.user in message.mentions or
                contains_name
            )

            # Check if the user is coned BEFORE the should_respond check
            # This needs to happen for ALL messages, not just ones that trigger Ghost
            # ONLY use Discord ID for cone checking to avoid confusion with nicknames/display names
            user_discord_id = str(message.author.id)
            
            print(f"DEBUG: Checking cone status for Discord ID: {user_discord_id}")
            
            is_coned, effect = self.ai_handler.is_user_coned(user_discord_id, self.state_manager)
            if is_coned:
                print(f"DEBUG: Found cone for Discord ID '{user_discord_id}' with effect '{effect}'")
            
            # Store original message for potential reply before deletion
            original_message = message
            message_was_deleted = False
            
            # Handle coned user message replacement
            if is_coned:
                print(f"User {message.author.name} is coned with {effect} effect")
                
                # Check if cone condition is met (before transforming message)
                condition_met = self.ai_handler.check_cone_conditions(
                    str(message.author.id), message.content, self.state_manager
                )
                
                if condition_met:
                    print(f"Cone condition met for {message.author.name} - removing cone")
                    # Send a notification that the cone was removed
                    await message.channel.send(f"🎉 {message.author.mention} has met their cone condition and is now free!")
                    # Don't transform this message since they're now unconed
                    is_coned = False
                
                if is_coned:  # Still coned after condition check
                    # Delete the original message
                    try:
                        await message.delete()
                        message_was_deleted = True
                        print(f"Deleted original message from coned user {message.author.name}")
                    except discord.NotFound:
                        print("Message was already deleted")
                    except discord.Forbidden:
                        print("No permission to delete message")
                    except Exception as e:
                        print(f"Error deleting message: {e}")
                    
                    # Transform the message content
                    transformed_content = self.ai_handler.apply_cone_effect(message.content, effect)
                    
                    # Send transformed message using webhook to mimic the user
                    try:
                        webhook = await self.get_or_create_webhook(message.channel)
                        await webhook.send(
                            content=transformed_content,
                            username=message.author.display_name,
                            avatar_url=message.author.avatar.url if message.author.avatar else None
                        )
                        print(f"Sent transformed message: {transformed_content}")
                    except Exception as e:
                        print(f"Error sending webhook message: {e}")
                        # Fallback: just log the error
                    
                    # Don't continue processing if this was just a cone transformation
                    # Unless the message also triggers Ghost to respond
                    if not should_respond:
                        return

            if should_respond:
                try:
                    user_state, link_msg = await self.state_manager.get_user_state(
                        str(message.author.id),
                        message.author.name,
                        "discord",
                        message.author.nick
                    )

                    # Check for image attachments
                    image_urls = self.extract_image_urls(original_message)
                    
                    # Choose appropriate response method based on whether images are present
                    if image_urls:
                        print(f"Processing message with {len(image_urls)} images using vision model")
                        response = await self.ai_handler.get_vision_response(
                            user_state.to_dict(),
                            current_message=original_message.content,
                            image_urls=image_urls,
                            state_manager=self.state_manager
                        )
                    else:
                        # Use regular text model for text-only messages
                        response = await self.ai_handler.get_chat_response(
                            user_state.to_dict(),
                            current_message=original_message.content,
                            state_manager=self.state_manager
                        )
                    
                    # Only store messages if we got a real response
                    if response not in NON_INTERACTION_RESPONSES:
                        # Store the conversation pair
                        await self.state_manager.add_message(
                            platform_key,
                            original_message.content,
                            False,
                            message.author.name
                        )
                        
                        await self.state_manager.add_message(
                            platform_key,
                            response,
                            True,
                            BOT_NAME
                        )

                        print(f"DEBUG: User has {len(user_state.recent_messages)} messages, needs_summary: {user_state.needs_summary_update()}")

                        # Only check for summary updates on real conversations
                        if user_state.needs_summary_update():
                            success, msg = await self.state_manager.update_user_state(platform_key)
                            if not success:
                                print(f"Summary update failed: {msg}")

                        await self.state_manager.save_states()

                    # Fix reply issue: if message was deleted due to cone, send regular message instead of reply
                    if message_was_deleted:
                        await original_message.channel.send(f"{original_message.author.mention} {response}")
                    else:
                        await original_message.reply(response)
                except Exception as e:
                    print(f"Error processing message: {e}")
                    traceback.print_exc()
            # No else clause to store messages that don't trigger a response
        except Exception as e:
            print(f"Error in on_message: {e}")
            traceback.print_exc()

    async def get_or_create_webhook(self, channel):
        """Get or create a webhook for the channel."""
        try:
            # Check if we already have a webhook for this channel
            webhooks = await channel.webhooks()
            ghost_webhook = None
            
            for webhook in webhooks:
                if webhook.name == "Ghost-Cone-System":
                    ghost_webhook = webhook
                    break
            
            if not ghost_webhook:
                # Create a new webhook
                ghost_webhook = await channel.create_webhook(name="Ghost-Cone-System")
                print(f"Created new webhook for channel {channel.name}")
            
            return ghost_webhook
            
        except discord.Forbidden:
            print(f"No permission to manage webhooks in {channel.name}")
            return None
        except Exception as e:
            print(f"Error managing webhook: {e}")
            return None

def run_bot():
    bot = CustomBot()
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run_bot()
