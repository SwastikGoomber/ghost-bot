from twitchio.ext import commands
import os
import asyncio
from typing import Optional
from datetime import datetime, timedelta
import json
import traceback
import logging

# Import our custom classes
from state_manager import StateManager
from ai_handler import AIHandler
from config import (
    TWITCH_TOKEN,
    TWITCH_CLIENT_ID,
    TWITCH_CLIENT_SECRET,
    TWITCH_CHANNEL_NAME,
    TWITCH_BOT_NAME,
    RATE_LIMIT_MESSAGES,
    RATE_LIMIT_PERIOD,
    BOT_NAME,
    PLATFORM_SETTINGS,
    BOT_PERSONA
)

class TwitchBot(commands.Bot):
    def __init__(self, state_manager: StateManager = None, ai_handler: AIHandler = None):
        super().__init__(
            token=TWITCH_TOKEN,
            client_id=TWITCH_CLIENT_ID,
            nick=TWITCH_BOT_NAME,
            prefix='!',
            initial_channels=[TWITCH_CHANNEL_NAME]
        )
        self.state_manager = state_manager or StateManager()
        self.ai_handler = ai_handler or AIHandler()
        self.message_count = 0

    async def event_ready(self):
        """Called once when the bot goes online."""
        print("\n=== Twitch Bot Authorization Info ===")
        print(f"Bot Username: {self.nick}")
        print(f"Channel: {TWITCH_CHANNEL_NAME}")
        
        try:
            # Initialize state manager if using MongoDB
            if os.environ.get('MONGODB_URI') and not self.state_manager._initialized:
                await self.state_manager.load_states()
                self.state_manager._initialized = True
            
            # Send test message
            channel = self.get_channel(TWITCH_CHANNEL_NAME)
            await channel.send("Bot connected and testing permissions...")
            print("✓ Successfully sent test message")
        except Exception as e:
            print(f"❌ Failed during initialization: {e}")
            traceback.print_exc()

    async def handle_command(self, message, cmd):
        """Handle commands separately from chat messages"""
        platform_key = f"twitch_{message.author.id}"
        
        if cmd == 'ping':
            await message.channel.send(f"@{message.author.name} pong!")
            return True
            
        elif cmd == 'update_summary':
            success, msg = await self.state_manager.update_user_state(platform_key)
            await message.channel.send(f"@{message.author.name} {msg}")
            return True
            
        if cmd == 'confirm_link':
            try:
                success, msg = await self.state_manager.confirm_link_request(
                    str(message.author.id),
                    message.author.name
                )
                await message.channel.send(f"@{message.author.name} {msg}")
                return True
            except Exception as e:
                logging.error(f"Error in confirm_link: {e}")
                traceback.print_exc()
                await message.channel.send(f"@{message.author.name} Failed to link accounts")
                return True
                
        return False

    async def event_message(self, message):
        """Called when a message is received in the channel."""
        if message.echo:
            return

        try:
            # Handle commands first (both ! and / prefixes)
            if message.content.startswith(('!', '/')):
                cmd = message.content[1:].strip().lower()
                cmd = ''.join(char for char in cmd if char.isprintable())
                if await self.handle_command(message, cmd):
                    return

            platform_key = f"twitch_{message.author.id}"
            
            # Get user state with potential link notification
            user_state, link_notification = await self.state_manager.get_user_state(
                str(message.author.id),
                message.author.name,
                "twitch"
            )

            # Store user's message
            await self.state_manager.add_message(
                platform_key,
                message.content,
                False,
                message.author.name
            )

            # Get AI response
            response = await self.ai_handler.get_chat_response(user_state.to_dict())

            # Store bot's response
            await self.state_manager.add_message(
                platform_key,
                response,
                True,
                BOT_NAME
            )

            # Check if we need to update summaries
            if user_state.needs_summary_update():
                success, msg = await self.state_manager.update_user_state(platform_key)
                if not success:
                    print(f"Summary update failed: {msg}")

            # Send response
            await message.channel.send(f"@{message.author.name} {response}")

        except Exception as e:
            print(f"Error in event_message: {e}")
            traceback.print_exc()
            await message.channel.send(f"@{message.author.name} I'm having trouble processing that request right now.")
