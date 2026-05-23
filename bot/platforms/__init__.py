"""Platform adapters. Public surface: GhostDiscordBot, GhostTwitchBot."""

from .discord_bot import GhostDiscordBot
from .twitch_bot import GhostTwitchBot

__all__ = ["GhostDiscordBot", "GhostTwitchBot"]
