import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer
import pytest

from elmar.kindex_service import CachedFeed, KIndexConfig, KIndexMonitor, TgoSource

NOW = datetime(2026, 11, 1, 3, 10, tzinfo=UTC)


def feed(slots):
    return CachedFeed("K-Indices for Leirvogur\n\n01 nov. 2026 " + slots[:4] + " " + slots[4:] + "\n")


def test_persisted_progress_cache_and_no_repeat_on_restart(tmp_path):
    async def run():
        config = KIndexConfig(str(tmp_path / "state.sqlite3"), 123)
        monitor = KIndexMonitor(config)
        source = AsyncMock()
        notify = AsyncMock()
        source.fetch.return_value = feed("4xxxxxxx")
        await monitor.poll_once(source, notify, NOW)
        source.fetch.return_value = feed("45xxxxxx")
        await monitor.poll_once(source, notify, NOW + timedelta(hours=3))
        assert notify.await_count == 1
        monitor.close()
        monitor = KIndexMonitor(config)
        assert monitor.progress.latest.value == 5
        assert monitor.checked_at == NOW + timedelta(hours=3)
        assert monitor.source_error  # Restored data is labelled until checked.
        await monitor.poll_once(source, notify, NOW + timedelta(hours=3, minutes=10))
        assert notify.await_count == 1
        assert not monitor.source_error
        monitor.close()
    asyncio.run(run())


def test_no_channel_and_threshold_changes_do_not_replay(tmp_path):
    async def run():
        config = KIndexConfig(str(tmp_path / "state.sqlite3"), threshold=6)
        monitor = KIndexMonitor(config)
        source, notify = AsyncMock(), AsyncMock()
        source.fetch.return_value = feed("4xxxxxxx")
        await monitor.poll_once(source, notify, NOW)
        source.fetch.return_value = feed("45xxxxxx")
        await monitor.poll_once(source, notify, NOW + timedelta(hours=3))
        assert notify.await_count == 0
        monitor.close()
        monitor = KIndexMonitor(KIndexConfig(config.state_path, 123, 5))
        await monitor.poll_once(source, notify, NOW + timedelta(hours=3, minutes=10))
        assert notify.await_count == 0
        source.fetch.return_value = feed("456xxxxx")
        await monitor.poll_once(source, notify, NOW + timedelta(hours=6))
        assert notify.await_count == 1
        monitor.close()
    asyncio.run(run())


def test_failed_fetch_or_parse_preserves_last_known_data(tmp_path):
    async def run():
        monitor = KIndexMonitor(KIndexConfig(str(tmp_path / "state.sqlite3")))
        source, notify = AsyncMock(), AsyncMock()
        source.fetch.return_value = feed("4xxxxxxx")
        await monitor.poll_once(source, notify, NOW)
        expected = monitor.progress
        source.fetch.side_effect = TimeoutError()
        with pytest.raises(TimeoutError):
            await monitor.poll_once(source, notify, NOW)
        assert monitor.progress == expected
        source.fetch.side_effect = None
        source.fetch.return_value = CachedFeed("invalid changed format")
        with pytest.raises(ValueError):
            await monitor.poll_once(source, notify, NOW)
        assert monitor.progress == expected
        assert monitor.store.load()[0] == expected
        monitor.close()
    asyncio.run(run())


def test_send_failure_is_consumed_durably_without_repeat(tmp_path, caplog):
    async def run():
        config = KIndexConfig(str(tmp_path / "state.sqlite3"), 123)
        monitor = KIndexMonitor(config)
        source, notify = AsyncMock(), AsyncMock(side_effect=RuntimeError("send failed"))
        source.fetch.return_value = feed("4xxxxxxx")
        await monitor.poll_once(source, notify, NOW)
        source.fetch.return_value = feed("45xxxxxx")
        await monitor.poll_once(source, notify, NOW + timedelta(hours=3))
        monitor.close()
        monitor = KIndexMonitor(config)
        await monitor.poll_once(source, notify, NOW + timedelta(hours=3, minutes=10))
        assert notify.await_count == 1
        assert "will not be replayed" in caplog.text
        monitor.close()
    asyncio.run(run())


def test_source_http_conditional_requests_and_errors(monkeypatch):
    async def run():
        seen = []
        mode = ["normal"]
        async def handle(request):
            seen.append(dict(request.headers))
            if mode[0] == "error":
                return web.Response(status=503)
            if mode[0] == "oversized":
                return web.Response(text="a" * 65537)
            if request.headers.get("If-None-Match") == '"test"':
                return web.Response(status=304)
            return web.Response(text=feed("4xxxxxxx").text,
                                headers={"ETag": '"test"', "Last-Modified": "Sun, 01 Nov 2026 03:01:00 GMT"})
        app = web.Application()
        app.router.add_get("/k", handle)
        async with TestServer(app) as server, aiohttp.ClientSession() as session:
            monkeypatch.setattr("elmar.kindex_service.SOURCE_URL", str(server.make_url("/k")))
            source = TgoSource(session)
            first = await source.fetch(None)
            assert first.etag == '"test"'
            assert await source.fetch(first) == first
            assert seen[-1]["If-Modified-Since"] == first.last_modified
            mode[0] = "error"
            with pytest.raises(ValueError, match="HTTP 503"):
                await source.fetch(first)
            mode[0] = "oversized"
            with pytest.raises(ValueError, match="expected size"):
                await source.fetch(None)
    asyncio.run(run())


def test_polling_backoff_preserves_command_cache_and_recovers(tmp_path, monkeypatch):
    class StopPolling(BaseException):
        pass

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    async def run():
        monitor = KIndexMonitor(KIndexConfig(str(tmp_path / "state.sqlite3")))
        source = AsyncMock()
        source.fetch.side_effect = [TimeoutError(), TimeoutError(), feed("4xxxxxxx")]
        session = AsyncMock()
        monkeypatch.setattr("elmar.kindex_service.aiohttp.ClientSession", lambda **kwargs: session)
        monkeypatch.setattr("elmar.kindex_service.TgoSource", lambda session: source)
        monkeypatch.setattr("elmar.kindex_service.datetime", FixedDateTime)
        delays = []
        async def sleep(delay):
            delays.append(delay)
            if len(delays) < 3:
                assert monitor.source_error
            else:
                assert not monitor.source_error
                assert monitor.progress.latest.value == 4
                raise StopPolling()
        monkeypatch.setattr("elmar.kindex_service.asyncio.sleep", sleep)
        with pytest.raises(StopPolling):
            await monitor.run(AsyncMock())
        assert delays == [600, 1200, 600]
        monitor.close()
    asyncio.run(run())
