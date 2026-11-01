from datetime import UTC, datetime, timedelta

import pytest

from elmar.kindex import Progress, Reading, advance, is_fresh, parse_feed
from elmar.kindex_discord import reading_text
from elmar.kindex_service import KIndexConfig

START = datetime(2026, 11, 1, tzinfo=UTC)
HOURS = timedelta(hours=3)
FEED = "K-Indices for Leirvogur\n\n31 oct. 2026 5543 3476\n01 nov. 2026 7543 233x\n"


def series(values):
    return tuple(Reading(START + (i + 1) * HOURS, value) for i, value in enumerate(values))


def test_real_source_format_and_midnight():
    readings = parse_feed(FEED)
    assert len(readings) == 16
    assert readings[7] == Reading(START, 6)
    assert readings[-2] == Reading(START + timedelta(hours=21), 3)
    assert readings[-1] == Reading(START + timedelta(days=1), None)
    assert readings[8].start == START
    assert parse_feed(FEED.replace("x", "X")) == readings


@pytest.mark.parametrize("text", [
    "", FEED.replace("Leirvogur", "Tromsø"), FEED.replace("233x", "23?x"),
    FEED.replace("233x", "233"), FEED.replace("01 nov.", "31 nov."),
    FEED.replace("01 nov.", "01 xyz."), FEED + "unexpected text\n",
    "K-Indices for Leirvogur\n", FEED + "01 nov. 2026 1111 1111\n",
])
def test_reject_changed_or_ambiguous_format(text):
    with pytest.raises(ValueError):
        parse_feed(text)


def test_user_alert_sequence_and_configurable_threshold():
    readings = series([4, 5, 5, 6, 6, 5, 4])
    for threshold, expected in [(5, [5, 6]), (6, [6]), (7, [])]:
        progress = Progress()
        alerts = []
        for i, reading in enumerate(readings):
            progress, alert = advance(progress, readings[:i + 1], reading.end + timedelta(minutes=10), threshold)
            if alert:
                alerts.append(alert.value)
        assert alerts == expected


def test_initial_high_reading_is_quiet_and_repeated_poll_is_quiet():
    readings = series([4, 7])
    now = readings[-1].end + timedelta(minutes=10)
    progress, alert = advance(Progress(), readings, now, 5)
    assert alert is None
    assert progress.latest.value == 7
    assert advance(progress, readings, now, 5)[1] is None


def test_freshness_grace_and_midnight():
    reading = Reading(START, 4)
    assert is_fresh(reading, START + HOURS + timedelta(minutes=29, seconds=59))
    assert not is_fresh(reading, START + HOURS + timedelta(minutes=30))
    assert not is_fresh(Reading(START + HOURS, 5), START)
    assert is_fresh(Reading(START, 5), START + timedelta(minutes=10))
    assert not is_fresh(Reading(START, None), START)


def test_missing_interval_resets_increase_comparison():
    readings = series([4, None, 6, 7])
    progress, _ = advance(Progress(), readings[:1], readings[0].end, 5)
    progress, alert = advance(progress, readings[:3], readings[2].end, 5)
    assert alert is None  # 4 -> missing -> 6 is not a consecutive comparison.
    assert advance(progress, readings, readings[3].end, 5)[1].value == 7


def test_late_publication_is_not_consumed_as_missing():
    readings = series([4, None])
    progress, _ = advance(Progress(), readings[:1], readings[0].end, 5)
    progress, alert = advance(progress, readings, readings[1].end + timedelta(minutes=10), 5)
    assert alert is None
    published = series([4, 5])
    assert advance(progress, published, published[-1].end + timedelta(minutes=20), 5)[1].value == 5


def test_stale_or_historical_increases_do_not_alert():
    readings = series([4, 5])
    progress, _ = advance(Progress(), readings[:1], readings[0].end, 5)
    updated, alert = advance(progress, readings, readings[-1].end + HOURS + timedelta(minutes=31), 5)
    assert alert is None
    assert updated.latest == readings[-1]


def test_catch_up_only_notifies_for_latest_interval():
    readings = series([4, 5, 6, 7])
    progress, _ = advance(Progress(), readings[:1], readings[0].end, 5)
    progress, alert = advance(progress, readings, readings[-1].end, 5)
    assert alert == readings[-1]
    assert advance(progress, readings, readings[-1].end, 5)[1] is None


def test_same_interval_revision_updates_display_and_next_comparison():
    initial = series([4, 5])
    progress, _ = advance(Progress(), initial, initial[-1].end, 5)
    corrected = series([4, 6])
    progress, alert = advance(progress, corrected, corrected[-1].end, 5)
    assert alert is None
    assert progress.latest.value == 6
    next_readings = series([4, 6, 6])
    assert advance(progress, next_readings, next_readings[-1].end, 5)[1] is None


def test_future_slots_are_not_used():
    readings = series([4, 9])
    progress, alert = advance(Progress(), readings, readings[0].end, 5)
    assert progress.latest.value == 4
    assert alert is None


def test_all_unavailable_is_not_zero():
    assert advance(Progress(), series([None, None]), START + 2 * HOURS, 5) == (Progress(), None)


def test_source_regression_fails_closed():
    readings = series([4, 5])
    progress, _ = advance(Progress(), readings, readings[-1].end, 5)
    with pytest.raises(ValueError, match="moved backwards"):
        advance(progress, readings[:1], readings[-1].end, 5)


@pytest.mark.parametrize("threshold", ["-1", "10", "5.0", "abc", "", "５"])
def test_invalid_threshold_fails_configuration(threshold):
    with pytest.raises(ValueError, match="ELMAR_K_THRESHOLD"):
        KIndexConfig.from_env({"ELMAR_K_THRESHOLD": threshold})


@pytest.mark.parametrize("threshold", ["0", "5", "9"])
def test_valid_threshold(threshold):
    assert KIndexConfig.from_env({"ELMAR_K_THRESHOLD": threshold}).threshold == int(threshold)


def test_optional_channel_configuration():
    assert KIndexConfig.from_env({}).channel_id is None
    assert KIndexConfig.from_env({"ELMAR_K_CHANNEL_ID": "123"}).channel_id == 123
    for channel in ("0", "-1", "not-an-id"):
        with pytest.raises(ValueError, match="ELMAR_K_CHANNEL_ID"):
            KIndexConfig.from_env({"ELMAR_K_CHANNEL_ID": channel})


def test_public_message_languages_staleness_and_graph():
    reading = Reading(START + timedelta(hours=21), 6)
    for language in ("is", "en"):
        text = reading_text(reading, language=language, now=reading.end)
        assert "6" in text and "UTC" in text and "k_lrv1a.gif" in text
        assert "k_lrv1a.txt" in text and "HF" in text
        assert "⚠️" not in text
        old = reading_text(reading, language=language, now=reading.end + timedelta(hours=4), source_error=True)
        assert old.count("⚠️") == 2
    assert "hækkar í 6" in reading_text(reading, alert=True, now=reading.end)
    assert "k_lrv1a.gif" in reading_text(None)
    assert "aukinnar" not in reading_text(Reading(reading.end, 1), now=reading.end)
