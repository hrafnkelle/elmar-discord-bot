"""Leirvogur observations and notification policy, independent of Discord and HTTP."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

SOURCE_URL = "https://flux.phys.uit.no/Kindice/k_lrv1a.txt"
GRAPH_URL = "https://flux.phys.uit.no/Kindice/k_lrv1a.gif"
INTERVAL = timedelta(hours=3)
PUBLICATION_GRACE = timedelta(minutes=30)
MONTHS = {name: i for i, name in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}


@dataclass(frozen=True)
class Reading:
    end: datetime
    value: int | None

    @property
    def start(self) -> datetime:
        return self.end - INTERVAL


def parse_feed(text: str) -> tuple[Reading, ...]:
    """Parse all eight UT slots per day; x/X means unavailable, including future slots."""
    lines = text.strip().splitlines()
    if not lines or lines[0].strip() != "K-Indices for Leirvogur":
        raise ValueError("Unexpected Leirvogur feed header")
    readings = []
    previous_day = None
    for line in lines[1:]:
        if not line.strip():
            continue
        match = re.fullmatch(r"\s*(\d{1,2})\s+([A-Za-z]{3})\.?\s+(\d{4})\s+([0-9xX]{4})\s+([0-9xX]{4})\s*", line)
        if not match or match[2].lower() not in MONTHS:
            raise ValueError("Unexpected Leirvogur daily row")
        day = datetime(int(match[3]), MONTHS[match[2].lower()], int(match[1]), tzinfo=UTC)
        if previous_day is not None and day <= previous_day:
            raise ValueError("Duplicate or unordered Leirvogur dates")
        previous_day = day
        for slot, character in enumerate(match[4] + match[5], 1):
            readings.append(Reading(day + slot * INTERVAL,
                                    None if character.lower() == "x" else int(character)))
    if not readings:
        raise ValueError("Empty Leirvogur feed")
    return tuple(readings)


def is_fresh(reading: Reading, now: datetime) -> bool:
    """After the grace period, require the most recently completed UT interval."""
    boundary = now.replace(hour=now.hour // 3 * 3, minute=0, second=0, microsecond=0)
    expected = boundary if now >= boundary + PUBLICATION_GRACE else boundary - INTERVAL
    return reading.value is not None and expected <= reading.end <= now


@dataclass(frozen=True)
class Progress:
    latest: Reading | None = None
    processed: Reading | None = None


def advance(progress: Progress, readings: tuple[Reading, ...], now: datetime,
            threshold: int) -> tuple[Progress, Reading | None]:
    """Advance through completed observations; only the latest interval can alert.

    First use seeds a baseline. Missing slots break comparisons. Corrections update
    the baseline without alerting. Catch-up observations may restore a consecutive
    baseline, but never generate a queue of historical notifications.
    """
    completed = [reading for reading in readings if reading.end <= now]
    valid = [reading for reading in completed if reading.value is not None]
    if not valid:
        return progress, None
    latest = valid[-1]
    if progress.latest is not None and latest.end < progress.latest.end:
        raise ValueError("Leirvogur feed moved backwards")
    if progress.processed is None:
        return Progress(latest, latest), None

    previous = progress.processed
    alert = None
    for reading in completed:
        if reading.end == previous.end:
            # A revision can change the next interval's comparison, but never alert.
            previous = reading
        elif reading.end > previous.end:
            if reading.value is None:
                # A still-unpublished tail slot can arrive during the grace period.
                # Retain the cursor so its eventual numeric value is processed.
                continue
            consecutive = reading.end - previous.end == INTERVAL
            increasing = previous.value is not None and reading.value > previous.value
            if (consecutive and increasing and reading.value >= threshold
                    and reading.end == latest.end and is_fresh(reading, now)):
                alert = reading
            previous = reading
    return Progress(latest, previous), alert
