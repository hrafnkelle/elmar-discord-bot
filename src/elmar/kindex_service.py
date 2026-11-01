"""Numerical source access, durable cache/progress, and shared polling."""

import asyncio
import json
import logging
import os
import sqlite3
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiohttp

from elmar.kindex import Progress, Reading, SOURCE_URL, advance, parse_feed

log = logging.getLogger(__name__)
POLL_SECONDS = 600


@dataclass(frozen=True)
class KIndexConfig:
    state_path: str = "state/kindex.sqlite3"
    channel_id: int | None = None
    threshold: int = 5

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "KIndexConfig":
        env = os.environ if env is None else env
        threshold = env.get("ELMAR_K_THRESHOLD", "5").strip()
        if not threshold.isascii() or not threshold.isdecimal() or not 0 <= int(threshold) <= 9:
            raise ValueError("ELMAR_K_THRESHOLD must be an integer from 0 to 9")
        channel = env.get("ELMAR_K_CHANNEL_ID", "").strip()
        if channel and (not channel.isascii() or not channel.isdecimal() or int(channel) <= 0):
            raise ValueError("ELMAR_K_CHANNEL_ID must be empty or a positive channel ID")
        path = env.get("ELMAR_K_STATE_PATH", "state/kindex.sqlite3").strip()
        if not path:
            raise ValueError("ELMAR_K_STATE_PATH must not be empty")
        return cls(path, int(channel) if channel else None, int(threshold))


@dataclass(frozen=True)
class CachedFeed:
    text: str
    etag: str | None = None
    last_modified: str | None = None


class StateStore:
    """A single small SQLite record; cache and notification cursor commit together."""

    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS kindex_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)")
        self.connection.commit()

    def load(self) -> tuple[Progress, CachedFeed | None, datetime | None]:
        row = self.connection.execute("SELECT payload FROM kindex_state WHERE id=1").fetchone()
        if row is None:
            return Progress(), None, None
        data = json.loads(row[0])
        if data.get("version") != 1:
            raise ValueError("Unsupported K-index state version")

        def reading(value):
            if value is None:
                return None
            end = datetime.fromisoformat(value["end"])
            k = value["value"]
            if end.tzinfo is None or (k is not None and (type(k) is not int or not 0 <= k <= 9)):
                raise ValueError("Invalid saved K-index reading")
            return Reading(end, k)

        progress = Progress(reading(data["latest"]), reading(data["processed"]))
        cache = CachedFeed(**data["cache"]) if data["cache"] else None
        if cache:
            parse_feed(cache.text)
        checked = datetime.fromisoformat(data["checked_at"]) if data["checked_at"] else None
        if checked and checked.tzinfo is None:
            raise ValueError("Invalid saved K-index check time")
        return progress, cache, checked

    def save(self, progress: Progress, cache: CachedFeed, checked_at: datetime):
        def reading(value):
            return {"end": value.end.isoformat(), "value": value.value} if value else None

        data = {"version": 1, "latest": reading(progress.latest), "processed": reading(progress.processed),
                "cache": {"text": cache.text, "etag": cache.etag, "last_modified": cache.last_modified},
                "checked_at": checked_at.isoformat()}
        with self.connection:
            self.connection.execute("INSERT OR REPLACE INTO kindex_state VALUES (1, ?)", (json.dumps(data),))

    def close(self):
        self.connection.close()


class TgoSource:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def fetch(self, cached: CachedFeed | None) -> CachedFeed:
        headers = {"User-Agent": "ElmarDiscordBot/0.2 (+https://github.com/hrafnkelle/elmar-discord-bot)"}
        if cached:
            if cached.etag:
                headers["If-None-Match"] = cached.etag
            if cached.last_modified:
                headers["If-Modified-Since"] = cached.last_modified
        async with self.session.get(SOURCE_URL, headers=headers, allow_redirects=False) as response:
            if response.status == 304 and cached:
                return cached
            if response.status != 200:
                raise ValueError(f"Leirvogur source returned HTTP {response.status}")
            body = bytearray()
            async for chunk in response.content.iter_chunked(4096):
                body.extend(chunk)
                if len(body) > 65536:
                    raise ValueError("Leirvogur feed exceeds expected size")
            return CachedFeed(body.decode("utf-8"), response.headers.get("ETag"),
                              response.headers.get("Last-Modified"))


class KIndexMonitor:
    def __init__(self, config: KIndexConfig):
        self.config = config
        self.store = StateStore(config.state_path)
        try:
            self.progress, self.cached, self.checked_at = self.store.load()
        except Exception:
            self.store.close()
            raise
        self.source_error = self.cached is not None  # Verify restored cache on the first poll.

    async def poll_once(self, source: TgoSource, notify: Callable[[Reading], Awaitable[None]],
                        now: datetime | None = None):
        cached = await source.fetch(self.cached)
        now = datetime.now(UTC) if now is None else now
        progress, alert = advance(self.progress, parse_feed(cached.text), now, self.config.threshold)
        # Consume an interval durably before sending. This favors no duplicate pings
        # across restarts over retrying an ambiguously delivered Discord request.
        self.store.save(progress, cached, now)
        self.progress, self.cached, self.checked_at = progress, cached, now
        self.source_error = False
        if alert and self.config.channel_id:
            try:
                await notify(alert)
            except Exception:
                log.exception("K-index alert delivery failed; interval will not be replayed")

    async def run(self, notify: Callable[[Reading], Awaitable[None]]):
        delay = POLL_SECONDS
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20), trust_env=True) as session:
            source = TgoSource(session)
            while True:
                try:
                    await self.poll_once(source, notify)
                except (aiohttp.ClientError, TimeoutError, ValueError, OSError, sqlite3.Error):
                    self.source_error = True
                    log.exception("Cannot refresh Leirvogur K-index; retaining last known data")
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 3600)
                else:
                    delay = POLL_SECONDS
                    await asyncio.sleep(POLL_SECONDS)

    def close(self):
        self.store.close()
