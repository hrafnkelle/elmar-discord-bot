import json
from pathlib import Path
from itertools import product
import string

import pytest

from elmar.messages import result_text
from elmar.registry import Registry, parse_suffix

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def registry():
    return Registry.load(ROOT / "data/callsigns.json")


@pytest.mark.parametrize("value", ["IRA", "ira", "TF1IRA", " tf9ira ", "TF3 IRA"])
def test_suffix_is_occupied_across_digits(registry, value):
    assert registry.status(value) == ("IRA", "occupied")


@pytest.mark.parametrize("suffix", ["FOX", "GU", "JAM", "SS", "WA", "DX", "HZ", "LX", "PZ"])
def test_unusual_and_page_boundary_entries_are_occupied(registry, suffix):
    assert registry.status(suffix)[1] == "occupied"


@pytest.mark.parametrize("suffix", [
    "ASH", "CU", "EE", "HKB", "HV", "IR", "KEX", "KFP", "MJP", "OSO",
    "PAS", "PQ", "RT", "SH", "SP", "TF", "UT", "WLF", "WPR", "YA",
])
def test_november_2026_additions_are_occupied(registry, suffix):
    # Includes WLF, printed under V, and TF, which is itself a valid suffix.
    assert registry.status(suffix) == (suffix, "occupied")


@pytest.mark.parametrize("value", ["TF0ABC", "A", "WARD", "YOTA", "ABCD"])
def test_restricted_inputs_are_never_available(registry, value):
    assert registry.status(value)[1] != "unlisted"


@pytest.mark.parametrize("value", ["", "TF12ABC", "TF3", "ABC/P", "ÞÓR", "TFnFOX", "<@123>", "AB C", "ABCDE"])
def test_invalid_inputs(value):
    with pytest.raises(ValueError):
        parse_suffix(value)


def test_complete_candidate_pools(registry, monkeypatch):
    for length in (2, 3):
        pool = registry.candidates(length)
        excluded = {s for s in registry.occupied | registry.excluded if len(s) == length}
        assert len(pool) == 26 ** length - len(excluded)
        assert len(pool) == len(set(pool))
        assert all(registry.status(s) == (s, "unlisted") for s in pool)
        def choose(population):
            assert population == pool
            return population[-1]
        monkeypatch.setattr("elmar.registry.random.choice", choose)
        assert registry.suggest(length) == pool[-1]


def test_exhausted_pool():
    all_pairs = frozenset("".join(chars) for chars in product(string.ascii_uppercase, repeat=2))
    registry = Registry("2025-11-02", "https://www.ira.is/", all_pairs, frozenset())
    with pytest.raises(ValueError, match="No available"):
        registry.suggest(2)


@pytest.mark.parametrize("change", [
    {"schema_version": 2}, {"occupied_suffixes": []}, {"occupied_suffixes": ["IRA", "IRA"]},
    {"occupied_suffixes": ["ira"]}, {"occupied_suffixes": [None]},
    {"register_date": "yesterday"}, {"source_url": "https://example.com/"},
    {"excluded_suffixes": None},
])
def test_bad_register_fails_closed(tmp_path, change):
    data = json.loads((ROOT / "data/callsigns.json").read_text())
    data.update(change)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        Registry.load(path)


def test_missing_or_broken_json_fails_closed(tmp_path):
    with pytest.raises(OSError):
        Registry.load(tmp_path / "missing.json")
    path = tmp_path / "broken.json"
    path.write_text("{")
    with pytest.raises(ValueError):
        Registry.load(path)


def test_both_languages_and_source_date(registry):
    assert "Ekki laust" in result_text(registry, "IRA")
    assert "Not available" in result_text(registry, "IRA", "en")
    for language in ("is", "en"):
        text = result_text(registry, "ABC", language)
        assert registry.register_date in text
        assert registry.source_url in text
        assert "Fjarskiptastofa" in text
    assert "Virðist laust" in result_text(registry, "ABC")
    assert "Appears available" in result_text(registry, "ABC", "en")
