"""Private K-index command and Icelandic/English presentation."""

from datetime import UTC, datetime
from typing import Literal

import discord
from discord import app_commands

from elmar.kindex import GRAPH_URL, SOURCE_URL, Reading, is_fresh
from elmar.kindex_service import KIndexMonitor


def reading_text(reading: Reading | None, *, language: str = "is", now: datetime | None = None,
                 source_error: bool = False, checked_at: datetime | None = None, alert: bool = False,
                 detailed: bool = False) -> str:
    english = language == "en"
    now = datetime.now(UTC) if now is None else now
    graph_link = f"[{'Graph' if english else 'Línurit'}](<{GRAPH_URL}>)"
    links = f"{graph_link} · [{'Data: UiT/TGO' if english else 'Gögn: UiT/TGO'}](<{SOURCE_URL}>)"
    if reading is None:
        text = ("No Leirvogur K-index data is available yet. Please try again later." if english else
                "Engin K-stuðulsgögn frá Leirvogi eru tiltæk enn. Reyndu aftur síðar.")
        return f"{text}\n{links if detailed else graph_link}"
    if alert:
        title = f"**K-stuðull í Leirvogi hækkar í {reading.value} af 9**"
    else:
        title = (f"**Local K at Leirvogur: {reading.value} of 9**" if english else
                 f"**K-stuðull í Leirvogi: {reading.value} af 9**")
    start = reading.start.strftime("%Y-%m-%d %H:%M")
    end = reading.end.strftime("%Y-%m-%d %H:%M")
    interval = (f"Interval: {start}–{end} UTC. Provisional; latest available published value." if english else
                f"Tímabil: {start}–{end} UTC. Bráðabirgðagildi; það nýjasta sem hefur verið birt.")
    warnings = []
    if not is_fresh(reading, now):
        warnings.append("⚠️ Data is stale; a newer interval is overdue." if english else
                        "⚠️ Gögn eru orðin gömul; nýrra tímabil vantar.")
    if source_error:
        warnings.append("⚠️ Source is unavailable or has not been checked since restart; showing saved data." if english else
                        "⚠️ Ekki hefur tekist að staðfesta gögn frá gagnaveitu; sýni vistað gildi.")
    if not detailed and not alert:
        short_end = reading.end.strftime("%H:%M" if reading.start.date() == reading.end.date() else "%Y-%m-%d %H:%M")
        return "\n".join(part for part in (title, f"{start}–{short_end} UTC", *warnings,
                                          graph_link) if part)
    if reading.value is not None and reading.value >= 5:
        explanation = ("This value indicates elevated geomagnetic disturbance at Leirvogur. Such disturbances can affect HF propagation, but K alone does not determine conditions on a particular path or frequency." if english else
                       "Gildið bendir til aukinnar segultruflunar við Leirvog. Slíkar truflanir geta haft áhrif á útbreiðslu á HF-böndum, en K-stuðullinn einn segir ekki til um skilyrði á tiltekinni leið eða tíðni.")
    else:
        explanation = ("This local index describes geomagnetic disturbance at Leirvogur. K alone does not determine HF conditions on a particular path or frequency." if english else
                       "Þessi staðbundni stuðull lýsir segultruflun við Leirvog. K-stuðullinn einn segir ekki til um HF-skilyrði á tiltekinni leið eða tíðni.")
    checked = (("Last checked: " if english else "Síðast kannað: ") + checked_at.strftime("%Y-%m-%d %H:%M UTC")) if checked_at else ""
    attribution = "Leirvogur / Háskóli Íslands · UiT/TGO"
    return "\n\n".join(part for part in (title, interval, "\n".join(warnings), explanation,
                                         links, checked, attribution) if part)


class KIndexCommands(app_commands.Group):
    def __init__(self, monitor: KIndexMonitor):
        super().__init__(name="kindex", description="Segulvirkni í Leirvogi")
        self.monitor = monitor

    @app_commands.command(name="nuna", description="Sýna nýjasta K-stuðul frá Leirvogi")
    @app_commands.describe(tungumal="Tungumál svars", itarlegt="Sýna útskýringar og ítarlegar heimildir")
    async def current(self, interaction: discord.Interaction,
                      tungumal: Literal["íslenska", "English"] = "íslenska", itarlegt: bool = False):
        await interaction.response.send_message(
            reading_text(self.monitor.progress.latest, language="en" if tungumal == "English" else "is",
                         source_error=self.monitor.source_error, checked_at=self.monitor.checked_at, detailed=itarlegt),
            ephemeral=True, allowed_mentions=discord.AllowedMentions.none(), suppress_embeds=True)
