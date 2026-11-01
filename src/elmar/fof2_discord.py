"""Private foF2 query and Icelandic/English presentation."""

from datetime import UTC, datetime
from typing import Literal

import discord
from discord import app_commands

from elmar.fof2 import ABOUT_URL, LATITUDE, LONGITUDE, MAP_URL, FoF2Estimate, FoF2Monitor


def estimate_text(estimate: FoF2Estimate | None, *, language: str = "is", now: datetime | None = None,
                  source_error: bool = False, checked_at: datetime | None = None) -> str:
    english = language == "en"
    now = now or datetime.now(UTC)
    links = (f"[{'foF2 map' if english else 'foF2-kort'}](<{MAP_URL}>) · "
             f"[{'About the model' if english else 'Um líkanið'}](<{ABOUT_URL}>)")
    if estimate is None:
        text = ("No KC2G foF2 estimate is available yet. Please try again later." if english else
                "Ekkert foF2-mat frá KC2G er tiltækt enn. Reyndu aftur síðar.")
        return f"{text}\n{links}"
    mhz = f"{estimate.mhz:.1f}" if english else f"{estimate.mhz:.1f}".replace(".", ",")
    title = (f"**Estimated foF2 near Reykjavík: {mhz} MHz**" if english else
             f"**Áætluð foF2 við Reykjavík: {mhz} MHz**")
    location = (f"Reference location: Reykjavík ({LATITUDE}° N, {abs(LONGITUDE)}° W)." if english else
                f"Viðmiðunarstaður: Reykjavík ({LATITUDE}° N, {abs(LONGITUDE)}° V).")
    valid = ("Model valid time: " if english else "Gildistími líkans: ") + estimate.valid_at.strftime("%Y-%m-%d %H:%M UTC")
    minutes = int((now - estimate.valid_at).total_seconds() / 60)
    if minutes < 0:
        age = (f"Valid in {abs(minutes)} min (model nowcast)." if english else
               f"Gildir eftir {abs(minutes)} mín. (númat líkans).")
    else:
        age = f"Model age: {minutes} min." if english else f"Aldur líkansgildis: {minutes} mín."
    explanation = ("An estimate for the ionosphere near this Icelandic reference point, not a direct measurement in Iceland or a value for the whole island. foF2 is the F2-layer vertical critical frequency; it alone does not establish whether an HF band or path is usable." if english else
                   "Þetta er líkanmat við þennan íslenska viðmiðunarstað, ekki bein mæling á Íslandi eða gildi fyrir allt landið. foF2 er marktíðni F2-lagsins fyrir lóðrétta útbreiðslu; gildið eitt og sér segir ekki til um hvort HF-band eða sambandsleið sé nothæf.")
    warnings = []
    if not estimate.is_fresh(now):
        warnings.append("⚠️ Model data is stale; showing the last available estimate." if english else
                        "⚠️ Líkanagögn eru orðin gömul; sýni síðasta tiltæka mat.")
    if source_error:
        warnings.append("⚠️ Source refresh failed; showing the cached estimate." if english else
                        "⚠️ Ekki tókst að uppfæra gögn frá gagnaveitu; sýni vistað mat.")
    checked = (("Last checked: " if english else "Síðast kannað: ") + checked_at.strftime("%Y-%m-%d %H:%M UTC")) if checked_at else ""
    return "\n\n".join(part for part in (title, location, f"{valid}\n{age}", "\n".join(warnings),
                                         explanation, links, checked, "KC2G · GIRO / IRI") if part)


class FoF2Commands(app_commands.Group):
    def __init__(self, monitor: FoF2Monitor):
        super().__init__(name="fof2", description="Áætluð marktíðni jónahvolfs við Ísland")
        self.monitor = monitor

    @app_commands.command(name="nuna", description="Sýna nýjasta foF2-mat við Reykjavík")
    @app_commands.describe(tungumal="Tungumál svars")
    async def current(self, interaction: discord.Interaction,
                      tungumal: Literal["íslenska", "English"] = "íslenska"):
        await interaction.response.send_message(
            estimate_text(self.monitor.latest, language="en" if tungumal == "English" else "is",
                          source_error=self.monitor.source_error, checked_at=self.monitor.checked_at),
            ephemeral=True, allowed_mentions=discord.AllowedMentions.none(), suppress_embeds=True)
