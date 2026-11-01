"""Icelandic and English response text."""

from elmar.registry import Registry


def result_text(registry: Registry, value: str, language: str = "is", *, suggestion: bool = False) -> str:
    english = language == "en"
    try:
        suffix, status = registry.status(value)
    except ValueError:
        return ("Enter an A–Z suffix (e.g. ABC) or an Icelandic callsign (e.g. TF3ABC)."
                if english else "Sláðu inn viðskeyti með A–Z (t.d. ABC) eða íslenskt kallmerki (t.d. TF3ABC).")
    if status == "occupied":
        text = f"**{suffix}: Not available.** This suffix is listed, regardless of digit." if english else (
            f"**{suffix}: Ekki laust.** Viðskeytið er skráð, óháð tölustaf.")
    elif status == "restricted":
        text = f"**{suffix}: Outside ordinary allocation.** Single-letter suffixes, special allocations and TF0 are excluded." if english else (
            f"**{suffix}: Utan almennrar úthlutunar.** Eins stafs viðskeyti, sérúthlutanir og TF0 eru undanskilin.")
    else:
        text = f"**{suffix}: Appears available according to ÍRA’s callsign register.**" if english else (
            f"**{suffix}: Virðist laust samkvæmt kallmerkjaskrá ÍRA.**")
        text += (" Allocation must be confirmed by Fjarskiptastofa." if english else
                 " Fjarskiptastofa þarf að staðfesta úthlutun.")
    if suggestion:
        text = ("Suggested suffix: " if english else "Tillaga að viðskeyti: ") + text
    label = "Register dated" if english else "Kallmerkjaskrá dags."
    return f"{text}\n{label} {registry.register_date} · [ÍRA](<{registry.source_url}>)"
