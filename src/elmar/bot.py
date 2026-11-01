"""Discord transport. Add future feature groups alongside Callsigns."""

import logging
import os
from typing import Literal

import discord
from discord import app_commands

from elmar.messages import result_text
from elmar.registry import Registry

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
    def __init__(self, registry: Registry, guild_id: int):
        super().__init__(intents=discord.Intents.none(), allowed_mentions=discord.AllowedMentions.none())
        self.tree = app_commands.CommandTree(self)
        self.guild = discord.Object(id=guild_id)
        self.tree.add_command(Callsigns(registry), guild=self.guild)
        self.tree.on_error = self.command_error

    async def setup_hook(self):
        commands = await self.tree.sync(guild=self.guild)
        log.info("Registered %d command group(s)", len(commands))

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
    except (OSError, ValueError, TypeError) as error:
        raise SystemExit(f"Cannot load callsign register: {error}") from error
    Elmar(registry, int(guild)).run(token, log_handler=None)


if __name__ == "__main__":
    main()
