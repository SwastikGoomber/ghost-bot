"""
Twitch bot — thin platform adapter (TwitchIO v3).

Responsibilities:
- Receive Twitch channel messages via EventSub WebSocket (channel.chat.message).
- Call process_message() for LLM responses.
- Handle !confirm_link and !ping commands.
- Format and send responses within Twitch's 500-character limit.

Explicitly NOT responsible for:
- Any LLM logic, prompt building, or routing.
- Cone state (Twitch users cannot be coned — cone system is Discord-only).

Authentication notes (TwitchIO v3):
- Bot requires a User Access Token with scopes: user:read:chat, user:write:chat, user:bot.
- Broadcaster channel must have granted channel:bot scope (or bot is a mod).
- On first run, visit http://localhost:4343/oauth?scopes=user:read:chat+user:write:chat+user:bot
  in your browser and authorise. TwitchIO will save the token to .tio.tokens.json.
- Required env vars:
    TWITCH_CLIENT_ID       - App client ID from Twitch Dev Console
    TWITCH_CLIENT_SECRET   - App client secret from Twitch Dev Console
    TWITCH_BOT_ID          - Numeric User ID of the bot account (lillen_gh0st)
    TWITCH_OWNER_ID        - Numeric User ID of the channel to join (LillyYenVT)
"""

from __future__ import annotations

import logging
import os
import traceback
import typing

import twitchio
from twitchio import eventsub
from twitchio.ext import commands

from bot.utils.config import get_config
from bot.utils.models import Platform
from bot.memory.state import StateManager
from bot.cone.manager import ConeManager
from bot.pipeline.context import ContextBuilder
from bot.pipeline.handler import process_message

logger = logging.getLogger(__name__)

_NON_INTERACTION_RESPONSES = {
    "Mom says I gotta sleep. Whatever.",
    "I'm done for today, peace.",
    "Gonna go blast some music and sleep",
    "That's enough social interaction for one day",
    "Calling it. See ya tomorrow I guess",
    "Done with today. Later.",
    "Ugh, whatever. I'm not in the mood right now.",
    "Can't be bothered right now.",
    "I'm not in the mood right now.",
    "Bother me later.",
    "Can't it wait? I'm busy.",
}


class GhostTwitchBot(commands.Bot):
    def __init__(
        self,
        state_manager: StateManager,
        cone_manager: ConeManager,
        context_builder: ContextBuilder,
    ) -> None:
        cfg = get_config()

        bot_id = os.environ.get("TWITCH_BOT_ID", "")
        broadcaster_id = os.environ.get("TWITCH_OWNER_ID", "")
        client_id = os.environ.get("TWITCH_CLIENT_ID", "")
        client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "")

        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            bot_id=bot_id,
            # owner_id here means the bot-developer's personal account (optional).
            # We intentionally leave it unset; the broadcaster channel is stored separately.
            prefix="!",
        )

        self._cfg = cfg
        self._state = state_manager
        self._cone = cone_manager
        self._ctx_builder = context_builder
        # The broadcaster's numeric ID (LillyYenVT) — channel the bot reads/writes in.
        self._broadcaster_id: str = broadcaster_id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def event_oauth_authorized(self, payload: typing.Any) -> None:
        """Called automatically when the user completes the OAuth flow."""
        # The parent class handles saving the token to .tio.tokens.json
        await super().event_oauth_authorized(payload)
        logger.info("OAuth authorization successful! Retrying chat subscription...")
        
        # Now that we have a user token, retry the subscription
        sub_payload = eventsub.ChatMessageSubscription(
            broadcaster_user_id=self._broadcaster_id,
            user_id=self.bot_id,
        )
        try:
            await self.subscribe_websocket(payload=sub_payload)
            logger.info("Successfully subscribed to Twitch chat messages!")
        except Exception as exc:
            logger.error("Failed to subscribe to Twitch chat after OAuth: %s", exc)

    async def event_ready(self) -> None:
        logger.info("Twitch bot ready | user=%s | bot_id=%s | channel=%s",
                    self.user, self.bot_id, self._broadcaster_id)

        broadcaster_id = self._broadcaster_id
        bot_id = self.bot_id

        if not broadcaster_id or not bot_id:
            logger.warning(
                "TWITCH_OWNER_ID or TWITCH_BOT_ID not set — "
                "Twitch bot will not subscribe to chat events."
            )
            return

        payload = eventsub.ChatMessageSubscription(
            broadcaster_user_id=broadcaster_id,
            user_id=bot_id,
        )

        try:
            await self.subscribe_websocket(payload=payload)
            logger.info("Subscribed to Twitch chat messages for channel %s.", broadcaster_id)
        except twitchio.HTTPException as exc:
            if exc.status == 403:
                logger.warning(
                    "Twitch bot failed to subscribe to chat (403 Forbidden). "
                    "This usually means the bot needs a User Access Token.\n"
                    "👉 Visit http://localhost:4343/oauth?scopes=user:read:chat+user:write:chat+user:bot "
                    "in your browser, log in as %s, and authorize the app.",
                    self.user.name if self.user else "your bot account"
                )
            else:
                logger.error("Failed to subscribe to Twitch chat: %s", exc)

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def event_message(self, message: twitchio.ChatMessage) -> None:
        # Ignore messages sent by the bot itself
        if message.chatter.id == self.bot_id:  # ignore own messages
            return

        # Ignore shared-chat re-broadcasts from other channels
        if message.source_broadcaster is not None:
            return

        try:
            await self._handle_message(message)
        except Exception:
            logger.error("Unhandled exception in event_message:\n%s", traceback.format_exc())

    async def _handle_message(self, message: twitchio.ChatMessage) -> None:
        cfg = self._cfg
        text: str = message.text
        chatter_name: str = message.chatter.name
        chatter_id: str = message.chatter.id

        # ------------------------------------------------------------------
        # Commands — handle !prefix commands first
        # ------------------------------------------------------------------
        if text.startswith(("!", "/")):
            cmd = text[1:].strip().lower()
            cmd = "".join(ch for ch in cmd if ch.isprintable())
            if await self._handle_command(message, cmd, chatter_name, chatter_id):
                return

        # ------------------------------------------------------------------
        # Determine if Ghost should respond
        # ------------------------------------------------------------------
        message_lower = text.lower()
        bot_name = (self.user.name if self.user else "ghost").lower()
        should_respond = (
            any(trigger in message_lower for trigger in cfg.bot.name_triggers)
            or f"@{bot_name}" in message_lower
        )

        if not should_respond:
            return

        # ------------------------------------------------------------------
        # Get or create user state
        # ------------------------------------------------------------------
        platform_key = f"twitch_{chatter_id}"
        user_state, _link_notification = await self._state.get_user_state(
            user_id=chatter_id,
            username=chatter_name,
            platform="twitch",
        )

        # ------------------------------------------------------------------
        # Get response from pipeline
        # ------------------------------------------------------------------
        response = await process_message(
            platform=Platform.TWITCH,
            user_state=user_state,
            message=text,
            state_manager=self._state,
            context_builder=self._ctx_builder,
        )

        # ------------------------------------------------------------------
        # Send response immediately to minimize perceived latency
        # ------------------------------------------------------------------
        reply = f"@{chatter_name} {response}"
        # Twitch has a 500-char hard limit
        if len(reply) > 500:
            reply = reply[:497] + "..."

        try:
            # message.broadcaster is a PartialUser for the channel owner.
            # send_message(sender=...) uses the Helix Chat API — no IRC needed.
            await message.broadcaster.send_message(
                sender=self.bot_id,
                message=reply,
            )
        except Exception as exc:
            logger.error("Failed to send Twitch message: %s", exc)

        # ------------------------------------------------------------------
        # Persist conversation (after sending response to avoid blocking user)
        # ------------------------------------------------------------------
        if response not in _NON_INTERACTION_RESPONSES:
            await self._state.add_message(platform_key, text, False, chatter_name)
            await self._state.add_message(platform_key, response, True, cfg.bot.name)

            if self._state.needs_summary_update(platform_key):
                success, msg = await self._state.update_summaries(platform_key)
                if not success:
                    logger.warning("Summary update failed for %s: %s", platform_key, msg)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def _handle_command(
        self, message: twitchio.ChatMessage, cmd: str, chatter_name: str, chatter_id: str
    ) -> bool:
        """Handle !commands. Returns True if the command was consumed."""
        platform_key = f"twitch_{chatter_id}"

        async def reply(text: str) -> None:
            try:
                await message.broadcaster.send_message(
                    sender=self.bot_id,  # bot's numeric ID string
                    message=f"@{chatter_name} {text}",
                )
            except Exception as exc:
                logger.error("Failed to send command reply: %s", exc)

        if cmd == "ping":
            await reply("pong!")
            return True

        if cmd == "update_summary":
            success, msg = await self._state.update_summaries(platform_key)
            await reply(msg)
            return True

        if cmd == "confirm_link":
            success, msg = await self._state.confirm_link_request(chatter_id, chatter_name)
            await reply(msg)
            return True

        return False
