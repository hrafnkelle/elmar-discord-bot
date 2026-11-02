import asyncio
import io
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer
import h5py
import hdf5plugin
import numpy as np
import pytest

from elmar.fof2 import FoF2Estimate, FoF2Monitor, KC2GSource, decode_grid
from elmar.fof2_discord import FoF2Commands, estimate_text

NOW = datetime(2026, 11, 1, 22, 35, tzinfo=UTC)
VALID = NOW - timedelta(minutes=5)


def make_grid(*, values=None, timestamp=None, compressed=False):
    output = io.BytesIO()
    if values is None:
        values = np.full((181, 361), 3.7)
    with h5py.File(output, "w") as f:
        f["ts"] = VALID.timestamp() if timestamp is None else timestamp
        options = hdf5plugin.SZ(absolute=0.001) if compressed else {}
        f.create_dataset("maps/fof2", data=values, **options)
    return output.getvalue()


def test_bilinear_interpolation_and_latitude_longitude_order():
    # A linear surface has an exact analytical interpolation at the reference point.
    lat, lon = np.meshgrid(np.arange(-90, 91), np.arange(-180, 181), indexing="ij")
    values = 5 + lat * .01 + lon * .001
    estimate = decode_grid(make_grid(values=values), NOW)
    assert estimate.mhz == pytest.approx(5 + 64.15 * .01 - 21.94 * .001)
    assert estimate.valid_at == VALID


def test_provider_sz_compression_can_be_read():
    estimate = decode_grid(make_grid(compressed=True), NOW)
    assert estimate.mhz == pytest.approx(3.7, abs=.002)


@pytest.mark.parametrize("timestamp", [float("nan"), float("inf"), -1,
                                      (NOW + timedelta(hours=1)).timestamp(), [VALID.timestamp()]])
def test_invalid_or_forecast_timestamp_rejected(timestamp):
    with pytest.raises(ValueError):
        decode_grid(make_grid(timestamp=timestamp), NOW)


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), 100])
def test_invalid_reference_cell_is_not_reported_as_a_frequency(value):
    values = np.full((181, 361), 3.7)
    values[154, 158] = value
    with pytest.raises(ValueError, match="unavailable or invalid"):
        decode_grid(make_grid(values=values), NOW)


def test_invalid_cells_elsewhere_do_not_hide_valid_reference_location():
    values = np.full((181, 361), 3.7)
    values[0, 0] = np.nan
    assert decode_grid(make_grid(values=values), NOW).mhz == pytest.approx(3.7)


@pytest.mark.parametrize("values", [np.ones((361, 181)), np.ones((2, 2)),
                                   np.full((181, 361), b"x", dtype="S1")])
def test_grid_shape_and_type_changes_fail_closed(values):
    with pytest.raises(ValueError):
        decode_grid(make_grid(values=values), NOW)


def test_unreadable_missing_and_external_datasets_rejected():
    with pytest.raises(ValueError):
        decode_grid(b"<html>upstream unavailable</html>", NOW)
    for mode in ("missing", "group", "external", "soft"):
        output = io.BytesIO()
        with h5py.File(output, "w") as f:
            f["ts"] = VALID.timestamp()
            if mode == "group":
                f.create_group("maps/fof2")
            elif mode == "external":
                f["maps"] = h5py.ExternalLink("/not-a-local-input.h5", "/maps")
            elif mode == "soft":
                f["maps"] = h5py.SoftLink("/other")
        with pytest.raises(ValueError):
            decode_grid(output.getvalue(), NOW)


def test_freshness_including_short_nowcast_horizon():
    assert FoF2Estimate(3.7, NOW - timedelta(minutes=45)).is_fresh(NOW)
    assert not FoF2Estimate(3.7, NOW - timedelta(minutes=46)).is_fresh(NOW)
    assert FoF2Estimate(3.7, NOW + timedelta(minutes=5)).is_fresh(NOW)
    assert not FoF2Estimate(3.7, NOW + timedelta(hours=1)).is_fresh(NOW)


def test_bilingual_estimate_label_links_age_and_stale_warning():
    estimate = FoF2Estimate(3.7, VALID)
    for language, title in [("is", "Áætluð foF2"), ("en", "Estimated foF2")]:
        text = estimate_text(estimate, language=language, now=NOW, checked_at=NOW, detailed=True)
        assert title in text and "Reykjavík" in text
        assert "MHz" in text and "2026-11-01 22:30 UTC" in text
        assert "64.15" in text and "21.94" in text
        assert "prop.kc2g.com/fof2/" in text and "prop.kc2g.com/about/" in text
        assert "⚠️" not in text
        stale = estimate_text(estimate, language=language, now=NOW + timedelta(hours=1), source_error=True)
        assert stale.count("⚠️") == 2
        assert "prop.kc2g.com/fof2/" in estimate_text(None, language=language)


def test_query_is_private_bilingual_and_does_not_fetch():
    async def run():
        monitor = SimpleNamespace(latest=FoF2Estimate(3.7, VALID), source_error=False, checked_at=NOW)
        group = FoF2Commands(monitor)
        interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))
        for language, expected in [("íslenska", "Áætluð"), ("English", "Estimated")]:
            await group.current.callback(group, interaction, language)
            args = interaction.response.send_message.call_args
            assert expected in args.args[0]
            assert args.kwargs["ephemeral"] is True
            assert args.kwargs["allowed_mentions"].to_dict() == {"parse": []}
            assert "HF" not in args.args[0]
            await group.current.callback(group, interaction, language, itarlegt=True)
            detailed = interaction.response.send_message.call_args
            assert "HF" in detailed.args[0] and "GIRO" in detailed.args[0]
            assert detailed.kwargs["ephemeral"] is True
        monitor.latest = None
        await group.current.callback(group, interaction)
        assert interaction.response.send_message.call_args.kwargs["ephemeral"] is True
    asyncio.run(run())


def test_compact_estimate_keeps_estimate_label_time_map_and_warnings():
    estimate = FoF2Estimate(3.7, VALID)
    for language in ("is", "en"):
        text = estimate_text(estimate, language=language, now=NOW, checked_at=NOW)
        assert "MHz" in text and "Reykjavík" in text and "22:30 UTC" in text
        assert "prop.kc2g.com/fof2/" in text
        assert "HF" not in text and "GIRO" not in text and "about/" not in text
        assert "64.15" not in text
        assert len(text) < 220
        warned = estimate_text(estimate, language=language, now=NOW + timedelta(hours=1), source_error=True)
        assert warned.count("⚠️") == 2


def test_monitor_updates_corrections_but_rejects_regression():
    async def run():
        monitor = FoF2Monitor()
        source = AsyncMock()
        source.fetch.return_value = FoF2Estimate(3.7, VALID)
        await monitor.poll_once(source, NOW)
        source.fetch.return_value = FoF2Estimate(3.8, VALID)
        await monitor.poll_once(source, NOW)
        assert monitor.latest.mhz == 3.8
        source.fetch.return_value = FoF2Estimate(4, VALID - timedelta(minutes=15))
        with pytest.raises(ValueError, match="moved backwards"):
            await monitor.poll_once(source, NOW)
        assert monitor.latest.mhz == 3.8
    asyncio.run(run())


def test_http_data_conditional_requests_and_provider_failures(monkeypatch):
    async def run():
        mode = ["normal"]
        requests = []
        body = make_grid()
        async def handle(request):
            requests.append(dict(request.headers))
            if mode[0] == "failure":
                return web.Response(status=503)
            if mode[0] == "oversize":
                return web.Response(body=b"x" * 2049)
            if mode[0] == "bad":
                return web.Response(text="not an HDF5 grid")
            if request.headers.get("If-None-Match") == '"model"':
                return web.Response(status=304)
            return web.Response(body=body, headers={"ETag": '"model"', "Last-Modified": "Sun, 01 Nov 2026 22:30:00 GMT"})
        app = web.Application()
        app.router.add_get("/model", handle)
        async with TestServer(app) as server, aiohttp.ClientSession() as session:
            monkeypatch.setattr("elmar.fof2.SOURCE_URL", str(server.make_url("/model")))
            source = KC2GSource(session)
            estimate = await source.fetch(None, NOW)
            assert estimate.mhz == pytest.approx(3.7)
            assert await source.fetch(estimate, NOW) == estimate
            assert requests[-1]["If-Modified-Since"] == estimate.last_modified
            mode[0] = "failure"
            with pytest.raises(ValueError, match="HTTP 503"):
                await source.fetch(estimate, NOW)
            mode[0] = "bad"
            with pytest.raises(ValueError, match="Cannot decode"):
                await source.fetch(None, NOW)
            mode[0] = "oversize"
            monkeypatch.setattr("elmar.fof2.MAX_BYTES", 2048)
            with pytest.raises(ValueError, match="expected size"):
                await source.fetch(None, NOW)
    asyncio.run(run())


def test_background_failures_retain_estimate_and_back_off(monkeypatch):
    class StopPolling(BaseException):
        pass

    async def run():
        monitor = FoF2Monitor()
        estimate = FoF2Estimate(3.7, VALID)
        monitor.latest = estimate
        source = AsyncMock()
        source.fetch.side_effect = [TimeoutError(), ValueError("changed format"), estimate]
        session = AsyncMock()
        monkeypatch.setattr("elmar.fof2.aiohttp.ClientSession", lambda **kwargs: session)
        monkeypatch.setattr("elmar.fof2.KC2GSource", lambda session: source)
        delays = []
        async def sleep(delay):
            delays.append(delay)
            assert monitor.latest == estimate
            if len(delays) < 3:
                assert monitor.source_error
            else:
                assert not monitor.source_error
                raise StopPolling()
        monkeypatch.setattr("elmar.fof2.asyncio.sleep", sleep)
        with pytest.raises(StopPolling):
            await monitor.run()
        assert delays == [900, 1800, 900]
    asyncio.run(run())
