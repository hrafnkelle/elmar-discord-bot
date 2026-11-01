"""KC2G model estimates at a fixed Icelandic reference location."""

import asyncio
import io
import logging
import math
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

import aiohttp
import h5py
import hdf5plugin  # Registers the SZ filter used by the provider's grids.
import numpy as np

SOURCE_URL = "https://prop.kc2g.com/api/assimilated.h5"
MAP_URL = "https://prop.kc2g.com/fof2/"
ABOUT_URL = "https://prop.kc2g.com/about/"
LATITUDE = 64.15
LONGITUDE = -21.94
POLL_SECONDS = 900
MAX_AGE = timedelta(minutes=45)
FUTURE_TOLERANCE = timedelta(minutes=15)
MAX_BYTES = 2 * 1024 * 1024
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FoF2Estimate:
    mhz: float
    valid_at: datetime
    etag: str | None = None
    last_modified: str | None = None

    def is_fresh(self, now: datetime) -> bool:
        return -FUTURE_TOLERANCE <= now - self.valid_at <= MAX_AGE


def decode_grid(body: bytes, now: datetime) -> FoF2Estimate:
    """Read the nowcast time and bilinearly interpolate foF2 near Reykjavík.

    Provider axes: latitudes -90..90, longitudes -180..180, one-degree steps.
    The grid is a model surface, not a local ionosonde measurement.
    """
    try:
        with h5py.File(io.BytesIO(body), "r") as grid:
            for path in ("ts", "maps", "maps/fof2"):
                if not isinstance(grid.get(path, getlink=True), h5py.HardLink):
                    raise ValueError("KC2G grid contains a missing or external data link")
            timestamp = grid["ts"]
            values = grid["maps/fof2"]
            if not isinstance(timestamp, h5py.Dataset) or not isinstance(values, h5py.Dataset):
                raise ValueError("Unexpected KC2G datasets")
            if timestamp.is_virtual or values.is_virtual or timestamp.external or values.external:
                raise ValueError("KC2G grid must contain its own data")
            if timestamp.shape != () or values.shape != (181, 361):
                raise ValueError("Unexpected KC2G grid dimensions")
            if timestamp.dtype.kind not in "iuf" or values.dtype.kind not in "iuf":
                raise ValueError("Unexpected KC2G grid types")
            ts = float(timestamp[()])
            if not math.isfinite(ts) or ts <= 0:
                raise ValueError("Invalid KC2G model timestamp")
            valid_at = datetime.fromtimestamp(ts, UTC)
            if valid_at > now + FUTURE_TOLERANCE:
                raise ValueError("KC2G grid is a future forecast, not a current estimate")
            y, x = LATITUDE + 90, LONGITUDE + 180
            i, j = math.floor(y), math.floor(x)
            corners = values[i:i + 2, j:j + 2]
            if not np.all(np.isfinite(corners) & (corners > 0) & (corners <= 50)):
                raise ValueError("KC2G foF2 is unavailable or invalid at the Iceland reference location")
            a, b = y - i, x - j
            mhz = float((1-a)*(1-b)*corners[0, 0] + (1-a)*b*corners[0, 1]
                        + a*(1-b)*corners[1, 0] + a*b*corners[1, 1])
    except (OSError, KeyError, TypeError, OverflowError) as error:
        raise ValueError("Cannot decode KC2G foF2 grid") from error
    return FoF2Estimate(mhz, valid_at)


class KC2GSource:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def fetch(self, previous: FoF2Estimate | None, now: datetime | None = None) -> FoF2Estimate:
        headers = {"User-Agent": "ElmarDiscordBot (+https://github.com/hrafnkelle/elmar-discord-bot)"}
        if previous:
            if previous.etag:
                headers["If-None-Match"] = previous.etag
            if previous.last_modified:
                headers["If-Modified-Since"] = previous.last_modified
        async with self.session.get(SOURCE_URL, headers=headers, allow_redirects=False) as response:
            if response.status == 304 and previous:
                return previous
            if response.status != 200:
                raise ValueError(f"KC2G source returned HTTP {response.status}")
            body = bytearray()
            async for chunk in response.content.iter_chunked(16384):
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ValueError("KC2G model grid exceeds expected size")
            # HDF5 decompression must not hold up the Discord event loop.
            estimate = await asyncio.to_thread(decode_grid, bytes(body), now or datetime.now(UTC))
            return replace(estimate, etag=response.headers.get("ETag"),
                           last_modified=response.headers.get("Last-Modified"))


class FoF2Monitor:
    """One shared in-memory cache for queries; no alerts or subscription state."""

    def __init__(self):
        self.latest: FoF2Estimate | None = None
        self.checked_at: datetime | None = None
        self.source_error = False

    async def poll_once(self, source: KC2GSource, now: datetime | None = None):
        estimate = await source.fetch(self.latest, now)
        if self.latest and estimate.valid_at < self.latest.valid_at:
            raise ValueError("KC2G model valid time moved backwards")
        self.latest = estimate
        self.checked_at = now or datetime.now(UTC)
        self.source_error = False

    async def run(self):
        delay = POLL_SECONDS
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30), trust_env=True) as session:
            source = KC2GSource(session)
            while True:
                try:
                    await self.poll_once(source)
                except (aiohttp.ClientError, TimeoutError, ValueError, OSError):
                    self.source_error = True
                    log.exception("Cannot refresh KC2G foF2; retaining last known estimate")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 3600)
                else:
                    delay = POLL_SECONDS
                    await asyncio.sleep(POLL_SECONDS)
