"""Discord transport. Add future feature groups alongside Callsigns."""

import asyncio
import logging
import os
from contextlib import suppress
from typing import Literal

import discord
from discord import app_commands

from elmar.messages import result_text
from elmar.registry import Registry
from elmar.kindex import Reading
from elmar.kindex_discord import KIndexCommands, reading_text
from elmar.kindex_service import KIndexConfig, KIndexMonitor

Language = Literal["íslenska", "English"]
log = logging.getLogger(__name__)


class Callsigns(app_commands.Group):
    def __init__(self, registry: Registry):
        super().__init__(name="kallmerki", description="Athugaðu kallmerki eða fáðu tillögu")
        self.registry = registry

    @app_commands.command(name="athuga", description="Athugaðu hvort viðskeyti sé laust")
    @app_commands.describe(vidskeyti="Viðskeyti eða kallmerki, t.d. ABC eða TF3ABC", tungumal="Tungumál svars")
    async def check(self, interaction: discord.Interaction, vidskeyti: str, tungumal: Language = "íslenska"):
        await interaction.response.send_message(
            result_text(self.registry, vidskeyti, "en" if tungumal == "English" else "is"), ephemeral=True)

    @app_commands.command(name="velja", description="Fáðu tillögu að lausu viðskeyti")
    @app_commands.describe(lengd="Fjöldi bókstafa (sjálfgefið 3)", tungumal="Tungumál svars")
    async def suggest(self, interaction: discord.Interaction, lengd: Literal[2, 3] = 3,
                      tungumal: Language = "íslenska"):
        language = "en" if tungumal == "English" else "is"
        try:
            suffix = self.registry.suggest(lengd)
        except ValueError:
            text = "No available suffixes of this length." if language == "en" else "Engin laus viðskeyti af þessari lengd."
        else:
            text = result_text(self.registry, suffix, language, suggestion=True)
        await interaction.response.send_message(text, ephemeral=True)


class Elmar(discord.Client):
    def __init__(self, registry: Registry, guild_id: int, kindex_config: KIndexConfig | None = None):
        super().__init__(intents=discord.Intents.none(), allowed_mentions=discord.AllowedMentions.none())
        self.tree = app_commands.CommandTree(self)
        self.guild = discord.Object(id=guild_id)
        self.tree.add_command(Callsigns(registry), guild=self.guild)
        self.tree.on_error = self.command_error
        self.kindex = KIndexMonitor(kindex_config) if kindex_config is not None else None
        self.kindex_task: asyncio.Task | None = None
        if self.kindex:
            self.tree.add_command(KIndexCommands(self.kindex), guild=self.guild)

    async def setup_hook(self):
        commands = await self.tree.sync(guild=self.guild)
        log.info("Registered %d command group(s)", len(commands))
        if self.kindex:
            self.kindex_task = asyncio.create_task(self.poll_kindex(), name="leirvogur-kindex")

    async def poll_kindex(self):
        await self.wait_until_ready()
        await self.kindex.run(self.send_kindex_alert)

    async def send_kindex_alert(self, reading: Reading):
        channel = await self.fetch_channel(self.kindex.config.channel_id)
        if not isinstance(channel, discord.TextChannel) or channel.guild.id != self.guild.id:
            raise ValueError("ELMAR_K_CHANNEL_ID must identify a text channel in the configured server")
        await channel.send(reading_text(reading, alert=True),
                           allowed_mentions=discord.AllowedMentions.none(), suppress_embeds=True)

    async def close(self):
        if self.kindex_task:
            self.kindex_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.kindex_task
        if self.kindex:
            self.kindex.close()
        await super().close()

    async def command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("Command failed", exc_info=(type(error), error, error.__traceback__))
        text = "Villa kom upp. Reyndu aftur síðar. / Something went wrong. Please try again later."
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)


def main():
    logging.basicConfig(level=logging.INFO)
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    guild = os.environ.get("DISCORD_GUILD_ID", "").strip()
    if not token or not guild.isascii() or not guild.isdecimal() or int(guild) <= 0:
        raise SystemExit("Set DISCORD_TOKEN and a positive DISCORD_GUILD_ID")
    try:
        registry = Registry.load(os.environ.get("ELMAR_REGISTER_PATH", "data/callsigns.json"))
        kindex_config = KIndexConfig.from_env()
    except (OSError, ValueError, TypeError) as error:
        raise SystemExit(f"Invalid bot configuration: {error}") from error
    Elmar(registry, int(guild), kindex_config).run(token, log_handler=None)


if __name__ == "__main__":
    main()
