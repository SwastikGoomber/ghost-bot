"""
Twitch bot — thin platform adapter.

Responsibilities:
- Receive Twitch channel messages and commands.
- Call process_message() for LLM responses.
- Handle !confirm_link and !ping commands.
- Format and send responses within Twitch's 500-character limit.

Explicitly NOT responsible for:
- Any LLM logic, prompt building, or routing.
- Cone state (Twitch users cannot be coned — cone system is Discord-only).
"""

from __future__ import annotations

import logging
import traceback
from typing import Optional

from twitchio.ext import commands

from ..utils.config import get_config
from ..utils.models import Platform
from ..memory.state import StateManager
from ..cone.manager import ConeManager
from ..pipeline.context import ContextBuilder
from ..pipeline.handler import process_message

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
        import os
        cfg = get_config()
        super().__init__(
            token=os.environ["TWITCH_TOKEN"],
            client_id=os.environ.get("TWITCH_CLIENT_ID", ""),
            client_secret=os.environ.get("TWITCH_CLIENT_SECRET", ""),
            bot_id=os.environ.get("TWITCH_CLIENT_ID", ""),
            nick=os.environ.get("TWITCH_BOT_NAME", "ghost_bot"),
            prefix="!",
            initial_channels=[os.environ.get("TWITCH_CHANNEL_NAME", "")],
        )
        self._cfg = cfg
        self._state = state_manager
        self._cone = cone_manager
        self._ctx_builder = context_builder

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def event_ready(self) -> None:
        logger.info("Twitch bot ready: %s", self.nick)
        try:
            channel_name = self._cfg.bot.name_triggers[0] if self._cfg.bot.name_triggers else "ghost"
            import os
            channel = self.get_channel(os.environ.get("TWITCH_CHANNEL_NAME", ""))
            if channel:
                await channel.send("/me Make way lil humans, Gh0st is here!")
        except Exception as exc:
            logger.warning("Could not send startup message: %s", exc)

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def event_message(self, message) -> None:
        if message.echo:
            return

        try:
            await self._handle_message(message)
        except Exception:
            logger.error("Unhandled exception in event_message:\n%s", traceback.format_exc())

    async def _handle_message(self, message) -> None:
        cfg = self._cfg

        # ------------------------------------------------------------------
        # Commands
        # ------------------------------------------------------------------
        if message.content.startswith(("!", "/")):
            cmd = message.content[1:].strip().lower()
            cmd = "".join(ch for ch in cmd if ch.isprintable())
            if await self._handle_command(message, cmd):
                return

        # ------------------------------------------------------------------
        # Determine if Ghost should respond
        # ------------------------------------------------------------------
        message_lower = message.content.lower()
        import os
        bot_name = os.environ.get("TWITCH_BOT_NAME", "ghost").lower()
        should_respond = (
            any(trigger in message_lower for trigger in cfg.bot.name_triggers)
            or f"@{bot_name}" in message_lower
        )

        if not should_respond:
            return

        # ------------------------------------------------------------------
        # Get or create user state
        # ------------------------------------------------------------------
        platform_key = f"twitch_{message.author.id}"
        user_state, link_notification = await self._state.get_user_state(
            user_id=str(message.author.id),
            username=message.author.name,
            platform="twitch",
        )

        # ------------------------------------------------------------------
        # Get response from pipeline
        # ------------------------------------------------------------------
        response = await process_message(
            platform=Platform.TWITCH,
            user_state=user_state,
            message=message.content,
            state_manager=self._state,
            context_builder=self._ctx_builder,
        )

        # ------------------------------------------------------------------
        # Persist conversation
        # ------------------------------------------------------------------
        if response not in _NON_INTERACTION_RESPONSES:
            await self._state.add_message(platform_key, message.content, False, message.author.name)
            await self._state.add_message(platform_key, response, True, cfg.bot.name)

            if self._state.needs_summary_update(platform_key):
                success, msg = await self._state.update_summaries(platform_key)
                if not success:
                    logger.warning("Summary update failed for %s: %s", platform_key, msg)

        # ------------------------------------------------------------------
        # Send response
        # ------------------------------------------------------------------
        await message.channel.send(f"@{message.author.name} {response}")

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def _handle_command(self, message, cmd: str) -> bool:
        """Handle !commands. Returns True if the command was consumed."""
        platform_key = f"twitch_{message.author.id}"

        if cmd == "ping":
            await message.channel.send(f"@{message.author.name} pong!")
            return True

        if cmd == "update_summary":
            success, msg = await self._state.update_summaries(platform_key)
            await message.channel.send(f"@{message.author.name} {msg}")
            return True

        if cmd == "confirm_link":
            success, msg = await self._state.confirm_link_request(
                str(message.author.id), message.author.name
            )
            await message.channel.send(f"@{message.author.name} {msg}")
            return True

        return False
