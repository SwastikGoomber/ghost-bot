"""
Discord bot — thin platform adapter.

Responsibilities:
- Receive Discord events (messages, slash commands).
- Parse platform-specific data into domain types.
- Call process_message() for LLM responses.
- Call ConeManager for cone operations.
- Handle webhook replacement for coned users.
- Format and send responses.

Explicitly NOT responsible for:
- Any LLM logic, prompt building, or routing.
- Understanding what a cone effect does.
- Cross-platform state management.
"""

from __future__ import annotations

import logging
import traceback
from collections import deque
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands, tasks

from ..utils.config import get_config
from ..utils.models import Platform
from ..memory.state import StateManager
from ..cone.manager import ConeManager
from ..pipeline.context import ContextBuilder
from ..pipeline.handler import process_message, _ERROR_RESPONSES, _RATE_LIMIT_RESPONSES

logger = logging.getLogger(__name__)

# Responses that must NOT be saved to conversation history.
# Built from handler's error/rate-limit pools so adding variants there auto-propagates here.
_NON_INTERACTION_RESPONSES: set[str] = set(_ERROR_RESPONSES) | set(_RATE_LIMIT_RESPONSES)


class GhostDiscordBot(commands.Bot):
    def __init__(
        self,
        state_manager: StateManager,
        cone_manager: ConeManager,
        context_builder: ContextBuilder,
    ) -> None:
        cfg = get_config()
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

        self._cfg = cfg
        self._state = state_manager
        self._cone = cone_manager
        self._ctx_builder = context_builder

        # Rate-limiting state
        self._daily_requests: int = 0
        self._minute_requests: deque[datetime] = deque(maxlen=cfg.bot.minute_request_limit)
        self._nap_until: Optional[datetime] = None

        # Optional RAG scheduler — set by main.py after construction
        # Kept as Any to avoid importing jobs package from platforms package
        self._rag_scheduler: Optional[object] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def setup_hook(self) -> None:
        """Called once after login, before the bot goes online."""
        await self._register_slash_commands()
        logger.info("Discord slash commands registered.")

    async def on_ready(self) -> None:
        logger.info("Discord bot ready: %s (ID: %s)", self.user, self.user.id)
        if self._rag_scheduler is not None:
            self._rag_scheduler.start()

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        try:
            await self._handle_message(message)
        except Exception:
            logger.error("Unhandled exception in on_message:\n%s", traceback.format_exc())

    async def _handle_message(self, message: discord.Message) -> None:
        cfg = self._cfg
        platform_key = f"discord_{message.author.id}"
        user_discord_id = str(message.author.id)

        # ------------------------------------------------------------------
        # Prefix commands (!update_summary etc.) — handled before anything else
        # ------------------------------------------------------------------
        if message.content.startswith("!"):
            await self._handle_prefix_command(message, platform_key)
            return

        # ------------------------------------------------------------------
        # Cone check — applies to ALL messages, not just bot-addressed ones
        # ------------------------------------------------------------------
        is_coned, effect = await self._cone.is_coned(user_discord_id)

        message_was_deleted = False
        if is_coned:
            # Check if the cone release condition is met first
            condition_met = await self._cone.check_and_release_condition(
                user_discord_id, message.content
            )
            if condition_met:
                await message.channel.send(
                    f"🎉 {message.author.mention} has met their cone condition and is now free!"
                )
                is_coned = False

            if is_coned:
                # Delete original and send transformed version via webhook
                try:
                    await message.delete()
                    message_was_deleted = True
                except (discord.NotFound, discord.Forbidden):
                    pass

                from ..cone.effects import apply_effect
                transformed = apply_effect(message.content, effect)

                webhook = await self._get_or_create_webhook(message.channel)
                if webhook:
                    try:
                        await webhook.send(
                            content=transformed,
                            username=message.author.display_name,
                            avatar_url=str(message.author.avatar.url) if message.author.avatar else None,
                        )
                    except Exception as exc:
                        logger.error("Webhook send failed: %s", exc)

        # ------------------------------------------------------------------
        # Determine if Ghost should respond
        # ------------------------------------------------------------------
        name_triggers = cfg.bot.name_triggers
        message_lower = message.content.lower()
        should_respond = (
            isinstance(message.channel, discord.DMChannel)
            or self.user in message.mentions
            or any(trigger in message_lower for trigger in name_triggers)
        )

        if not should_respond:
            return

        # ------------------------------------------------------------------
        # Rate-limiting / nap check
        # ------------------------------------------------------------------
        if self._is_rate_limited():
            if message_was_deleted:
                await message.channel.send(f"{message.author.mention} can't be bothered right now.")
            return

        # ------------------------------------------------------------------
        # Get or create user state
        # ------------------------------------------------------------------
        user_state, link_notification = await self._state.get_user_state(
            user_id=user_discord_id,
            username=message.author.name,
            platform="discord",
            nickname=message.author.nick,
        )

        # ------------------------------------------------------------------
        # Extract image attachments
        # ------------------------------------------------------------------
        image_urls = [
            att.url
            for att in message.attachments
            if att.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"))
        ]

        # ------------------------------------------------------------------
        # Get response from pipeline
        # ------------------------------------------------------------------
        response = await process_message(
            platform=Platform.DISCORD,
            user_state=user_state,
            message=message.content,
            state_manager=self._state,
            context_builder=self._ctx_builder,
            cone_manager=self._cone,
            image_urls=image_urls or None,
        )

        # ------------------------------------------------------------------
        # Persist conversation (only for genuine interactions)
        # ------------------------------------------------------------------
        if response not in _NON_INTERACTION_RESPONSES:
            await self._state.add_message(platform_key, message.content, False, message.author.name)
            await self._state.add_message(platform_key, response, True, cfg.bot.name)

            if self._state.needs_summary_update(platform_key):
                success, msg = await self._state.update_summaries(platform_key)
                if not success:
                    logger.warning("Summary update failed for %s: %s", platform_key, msg)
        else:
            await self._state.save_states()

        # ------------------------------------------------------------------
        # Send response
        # ------------------------------------------------------------------
        if message_was_deleted:
            await message.channel.send(f"{message.author.mention} {response}")
        else:
            await message.reply(response)

        self._record_request()

    # ------------------------------------------------------------------
    # Prefix commands
    # ------------------------------------------------------------------

    async def _handle_prefix_command(self, message: discord.Message, platform_key: str) -> None:
        cmd = message.content[1:].strip().lower()

        if cmd == "update_summary":
            success, msg = await self._state.update_summaries(platform_key)
            await message.reply(msg)

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------

    async def _register_slash_commands(self) -> None:
        cfg = self._cfg

        @self.tree.command(name="limits", description="Check remaining API limits and bot state")
        async def limits(interaction: discord.Interaction) -> None:
            daily_remaining = max(0, cfg.bot.daily_request_limit - self._daily_requests)
            now = datetime.now()
            self._clean_minute_requests(now)
            minute_remaining = max(0, cfg.bot.minute_request_limit - len(self._minute_requests))

            if self._daily_requests >= cfg.bot.daily_request_limit:
                status = "Sleeping until tomorrow!"
            elif self._nap_until and now < self._nap_until:
                mins_left = max(0, (self._nap_until - now).seconds // 60)
                status = f"Taking a {mins_left} minute nap!"
            else:
                status = "Awake and ready!"

            await interaction.response.send_message(
                f"Status: {status}\n"
                f"Daily requests remaining: {daily_remaining}/{cfg.bot.daily_request_limit}\n"
                f"Requests available this minute: {minute_remaining}/{cfg.bot.minute_request_limit}"
            )

        @self.tree.command(name="cone_status", description="Check cone status for a user")
        async def cone_status(
            interaction: discord.Interaction,
            username: Optional[str] = None,
        ) -> None:
            target = username or interaction.user.name
            discord_id = str(interaction.user.id) if not username else \
                self._cone.find_discord_id_by_username(target)

            if not discord_id:
                await interaction.response.send_message(f"{target} has never been coned.")
                return

            result = self._cone.get_status(discord_id)
            await interaction.response.send_message(f"**Cone Status for {target}:**\n{result.message}")

        @self.tree.command(name="cone", description="Apply a cone effect to a user")
        async def cone_cmd(
            interaction: discord.Interaction,
            user: discord.Member,
            effect: str = "shakespeare",
            duration: Optional[str] = None,
            condition: Optional[str] = None,
        ) -> None:
            if interaction.user.id not in cfg.discord.authorized_slash_user_ids:
                await interaction.response.send_message(
                    "❌ You don't have permission to use cone commands.", ephemeral=True
                )
                return

            result = await self._cone.apply(
                discord_id=str(user.id),
                effect=effect.lower(),
                applied_by=interaction.user.name,
                duration=duration,
                condition=condition,
            )
            await interaction.response.send_message(result.message)

        @self.tree.command(name="uncone", description="Remove cone effect from a user")
        async def uncone_cmd(
            interaction: discord.Interaction,
            user: discord.Member,
        ) -> None:
            if interaction.user.id not in cfg.discord.authorized_slash_user_ids:
                await interaction.response.send_message(
                    "❌ You don't have permission to use cone commands.", ephemeral=True
                )
                return

            result = await self._cone.remove(
                discord_id=str(user.id),
                removed_by=interaction.user.name,
            )
            await interaction.response.send_message(result.message)

        @self.tree.command(name="link_twitch", description="Link your Discord account with a Twitch account")
        async def link_twitch(interaction: discord.Interaction, twitch_username: str) -> None:
            success = await self._state.create_link_request(
                str(interaction.user.id), twitch_username
            )
            if success:
                await interaction.response.send_message(
                    f"Link request created! Type `!confirm_link` in the Twitch chat to complete."
                )
            else:
                await interaction.response.send_message("Failed to create link request.")

        @self.tree.command(name="unlink_accounts", description="Unlink your Discord and Twitch accounts")
        async def unlink_accounts(interaction: discord.Interaction) -> None:
            success = await self._state.unlink_accounts(f"discord_{interaction.user.id}")
            if success:
                await interaction.response.send_message("Accounts unlinked successfully.")
            else:
                await interaction.response.send_message("No linked accounts found.")

        @self.tree.command(name="update_summary", description="Force-update your relationship summary")
        async def update_summary(
            interaction: discord.Interaction,
            username: Optional[str] = None,
        ) -> None:
            await interaction.response.defer(ephemeral=True)
            platform_key = f"discord_{interaction.user.id}"

            if username:
                discord_id = self._state.find_discord_id_by_username(username)
                if not discord_id:
                    await interaction.followup.send(f"Could not find user '{username}'.")
                    return
                platform_key = f"discord_{discord_id}"

            success, msg = await self._state.update_summaries(platform_key)
            target = username or interaction.user.name
            prefix = "✓" if success else "✗"
            await interaction.followup.send(f"{prefix} {msg} ({target})")

        # ------------------------------------------------------------------
        # /ghost set — user profile commands
        # ------------------------------------------------------------------

        ghost_group = discord.app_commands.Group(
            name="ghost",
            description="Ghost Bot profile commands",
        )
        set_group = discord.app_commands.Group(
            name="set",
            description="Update your Ghost Bot profile",
            parent=ghost_group,
        )

        @set_group.command(name="alias", description="Set your aliases (comma-separated nicknames Ghost will recognise)")
        @discord.app_commands.describe(aliases="Comma-separated list, e.g. 'goomber, swas, swastik'")
        async def set_alias(
            interaction: discord.Interaction,
            aliases: str,
        ) -> None:
            state, _ = await self._state.get_user_state(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                platform="discord",
                nickname=interaction.user.display_name,
            )
            parsed = [a.strip() for a in aliases.split(",") if a.strip()]
            state.aliases = parsed
            # Merge aliases into name_variants so resolution works immediately
            existing = set(state.name_variants)
            for alias in parsed:
                existing.add(alias.lower())
            state.name_variants = list(existing)
            await self._state.save_states()
            logger.info("[/ghost set alias] %s set aliases: %s", interaction.user.name, parsed)
            await interaction.response.send_message(
                f"✓ Aliases updated: {', '.join(parsed)}", ephemeral=True
            )

        @set_group.command(name="pronouns", description="Set your pronouns (comma-separated)")
        @discord.app_commands.describe(pronouns="Comma-separated list, e.g. 'she/her, they/them'")
        async def set_pronouns(
            interaction: discord.Interaction,
            pronouns: str,
        ) -> None:
            state, _ = await self._state.get_user_state(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                platform="discord",
                nickname=interaction.user.display_name,
            )
            parsed = [p.strip() for p in pronouns.split(",") if p.strip()]
            state.pronouns = parsed
            await self._state.save_states()
            logger.info("[/ghost set pronouns] %s set pronouns: %s", interaction.user.name, parsed)
            await interaction.response.send_message(
                f"✓ Pronouns updated: {', '.join(parsed)}", ephemeral=True
            )

        @set_group.command(name="bio", description="Set a short bio that Ghost will know about you")
        @discord.app_commands.describe(bio="A short paragraph about yourself")
        async def set_bio(
            interaction: discord.Interaction,
            bio: str,
        ) -> None:
            if len(bio) > 500:
                await interaction.response.send_message(
                    "Bio must be 500 characters or fewer.", ephemeral=True
                )
                return
            state, _ = await self._state.get_user_state(
                user_id=str(interaction.user.id),
                username=interaction.user.name,
                platform="discord",
                nickname=interaction.user.display_name,
            )
            state.bio = bio.strip()
            await self._state.save_states()
            logger.info("[/ghost set bio] %s updated bio.", interaction.user.name)
            await interaction.response.send_message("✓ Bio updated.", ephemeral=True)

        self.tree.add_command(ghost_group)

        # Sync commands globally
        try:
            synced = await self.tree.sync()
            logger.info("Synced %d global slash commands.", len(synced))
        except Exception as exc:
            logger.error("Failed to sync slash commands: %s", exc)

    # ------------------------------------------------------------------
    # Webhook helpers
    # ------------------------------------------------------------------

    async def _get_or_create_webhook(self, channel: discord.TextChannel) -> Optional[discord.Webhook]:
        try:
            webhooks = await channel.webhooks()
            for wh in webhooks:
                if wh.name == "Ghost-Cone-System":
                    return wh
            return await channel.create_webhook(name="Ghost-Cone-System")
        except discord.Forbidden:
            logger.warning("No permission to manage webhooks in #%s", channel.name)
            return None
        except Exception as exc:
            logger.error("Webhook management error in #%s: %s", channel.name, exc)
            return None

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _is_rate_limited(self) -> bool:
        cfg = self._cfg
        now = datetime.now()
        self._clean_minute_requests(now)

        if self._daily_requests >= cfg.bot.daily_request_limit:
            return True
        if len(self._minute_requests) >= cfg.bot.minute_request_limit:
            return True
        if self._nap_until and now < self._nap_until:
            return True

        return False

    def _record_request(self) -> None:
        self._daily_requests += 1
        self._minute_requests.append(datetime.now())

        # Check nap thresholds
        for threshold, nap_minutes in sorted(self._cfg.bot.nap_durations.items()):
            if self._daily_requests == threshold:
                from datetime import timedelta
                self._nap_until = datetime.now() + timedelta(minutes=nap_minutes)
                logger.info("Bot entering %d-minute nap at %d requests.", nap_minutes, threshold)
                break

    def _clean_minute_requests(self, now: datetime) -> None:
        from datetime import timedelta
        cutoff = now - timedelta(seconds=60)
        while self._minute_requests and self._minute_requests[0] < cutoff:
            self._minute_requests.popleft()
