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

            if should_respond:
                try:
                    user_state, link_msg = await self.state_manager.get_user_state(
                        str(message.author.id),
                        message.author.name,
                        "discord",
                        message.author.nick
                    )

                    # Only store messages that trigger a response
                    await self.state_manager.add_message(
                        platform_key,
                        message.content,
                        False,
                        message.author.name
                    )

                    response = await self.ai_handler.get_chat_response(user_state.to_dict())

                    await self.state_manager.add_message(
                        platform_key,
                        response,
                        True,
                        BOT_NAME
                    )

                    if user_state.needs_summary_update():
                        success, msg = await self.state_manager.update_user_state(platform_key)
                        if not success:
                            print(f"Summary update failed: {msg}")

                    await self.state_manager.save_states()
                    await message.reply(response)
                except Exception as e:
                    print(f"Error processing message: {e}")
                    traceback.print_exc()
            # No else clause to store messages that don't trigger a response
        except Exception as e:
            print(f"Error in on_message: {e}")
            traceback.print_exc()

def run_bot():
    bot = CustomBot()
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    run_bot()

