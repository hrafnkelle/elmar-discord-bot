"""Private QRZ command and result presentation."""

import asyncio
from urllib.parse import quote

import aiohttp
import discord
from discord import app_commands

from elmar.qrz import QRZClient, QRZEntry, QRZError


def entry_text(entry: QRZEntry | None) -> str:
    if entry is None:
        return "Fann ekki kallmerki á qrz.com"

    def escape(value: str) -> str:
        return discord.utils.escape_markdown(" ".join(value.split()))

    link = f"[{escape(entry.callsign)}](<https://www.qrz.com/db/{quote(entry.callsign, safe='')}>)"
    name = escape(" ".join(part for part in (entry.firstname, entry.lastname) if part))
    address = escape(" ".join(part for part in (entry.addr2, entry.country) if part))
    budget = 2000 - len(link) - len(" -  - ")
    if budget < 0:
        raise QRZError("QRZ callsign link exceeds Discord's message limit")
    name_budget = min(len(name), max(budget // 2, budget - len(address)))

    def shorten(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        if limit == 0:
            return ""
        # Avoid leaving an incomplete Markdown escape at the truncation point.
        return value[:limit - 1].rstrip("\\") + "…"

    return f"{link} - {shorten(name, name_budget)} - {shorten(address, budget - name_budget)}"


class QRZCommands:
    def __init__(self, client: QRZClient):
        self.client = client

    @app_commands.describe(callsign="Kallmerki, t.d. TF3IRA")
    async def lookup(self, interaction: discord.Interaction, callsign: str):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            text = entry_text(await self.client.lookup(callsign))
        except (QRZError, aiohttp.ClientError, asyncio.TimeoutError):
            text = "Ekki tókst að fletta upp á qrz.com. Reyndu aftur síðar."
        await interaction.followup.send(text, ephemeral=True,
                                        allowed_mentions=discord.AllowedMentions.none(), suppress_embeds=True)
