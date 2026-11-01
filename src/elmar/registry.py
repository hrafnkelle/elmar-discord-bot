"""Validated local register and suffix selection, independent of Discord."""

import json
import random
import re
import string
from dataclasses import dataclass
from datetime import date
from itertools import product
from pathlib import Path
from urllib.parse import urlparse


def parse_suffix(value: str) -> tuple[str, bool]:
    """Return suffix and whether a complete callsign uses TF0."""
    value = value.strip().upper()
    match = re.fullmatch(r"TF([0-9])\s*([A-Z]{1,4})", value)
    if match:
        return match[2], match[1] == "0"
    if re.fullmatch(r"[A-Z]{1,4}", value):
        return value, False
    raise ValueError("Expected an A–Z suffix or a TF callsign with one digit")


@dataclass(frozen=True)
class Registry:
    register_date: str
    source_url: str
    occupied: frozenset[str]
    excluded: frozenset[str]

    @classmethod
    def load(cls, path: str | Path) -> "Registry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("Unsupported register schema")
        register_date = data.get("register_date")
        if not isinstance(register_date, str):
            raise ValueError("Missing register date")
        date.fromisoformat(register_date)
        source_url = data.get("source_url")
        if not isinstance(source_url, str):
            raise ValueError("Missing source URL")
        url = urlparse(source_url)
        if url.scheme != "https" or url.hostname not in {"ira.is", "www.ira.is"}:
            raise ValueError("Expected an HTTPS ÍRA source URL")

        def suffixes(key: str, *, nonempty: bool) -> frozenset[str]:
            values = data.get(key)
            if not isinstance(values, list) or (nonempty and not values):
                raise ValueError(f"Invalid {key}")
            if any(not isinstance(s, str) or not re.fullmatch(r"[A-Z]{1,4}", s) for s in values):
                raise ValueError(f"Invalid suffix in {key}")
            if len(values) != len(set(values)):
                raise ValueError(f"Duplicate suffix in {key}")
            return frozenset(values)

        return cls(register_date, source_url, suffixes("occupied_suffixes", nonempty=True),
                   suffixes("excluded_suffixes", nonempty=False))

    def status(self, value: str) -> tuple[str, str]:
        suffix, zero = parse_suffix(value)
        if suffix in self.occupied:
            return suffix, "occupied"
        if suffix in self.excluded or len(suffix) not in (2, 3) or zero:
            return suffix, "restricted"
        return suffix, "unlisted"

    def candidates(self, length: int) -> tuple[str, ...]:
        if length not in (2, 3):
            raise ValueError("Suggestion length must be 2 or 3")
        return tuple(s for chars in product(string.ascii_uppercase, repeat=length)
                     if (s := "".join(chars)) not in self.occupied | self.excluded)

    def suggest(self, length: int = 3) -> str:
        candidates = self.candidates(length)
        if not candidates:
            raise ValueError("No available suffixes")
        return random.choice(candidates)
