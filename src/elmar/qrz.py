"""QRZ XML lookups with a cached session and bounded reauthentication."""

import asyncio
from dataclasses import dataclass
from xml.etree import ElementTree

import aiohttp

API_URL = "https://xmldata.qrz.com/xml/current/"


class QRZError(Exception):
    """QRZ is unavailable or the account cannot perform a lookup."""


@dataclass(frozen=True)
class QRZEntry:
    callsign: str
    firstname: str
    lastname: str
    addr2: str
    country: str


class QRZClient:
    def __init__(self, username: str = "", password: str = ""):
        self.username = username
        self.password = password
        self._key = ""
        self._lock = asyncio.Lock()

    async def _request(self, session: aiohttp.ClientSession, data: dict[str, str]) -> ElementTree.Element:
        # POST keeps credentials and session keys out of request URLs and error logs.
        async with session.post(API_URL, data=data, allow_redirects=False) as response:
            if response.status != 200:
                raise QRZError("QRZ request failed")
            body = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                body.extend(chunk)
                if len(body) > 1024 * 1024:
                    raise QRZError("QRZ response too large")
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError:
            raise QRZError("Invalid QRZ XML response") from None
        if root.tag.split("}")[-1] != "QRZDatabase" or root.find("{*}Session") is None:
            raise QRZError("Invalid QRZ response")
        return root

    async def _login(self, session: aiohttp.ClientSession):
        root = await self._request(session, {
            "username": self.username, "password": self.password, "agent": "Elmar/0.3",
        })
        self._key = root.findtext("{*}Session/{*}Key", "").strip()
        if not self._key or root.findtext("{*}Session/{*}Error"):
            self._key = ""
            raise QRZError("QRZ login failed")

    async def lookup(self, callsign: str) -> QRZEntry | None:
        if not self.username or not self.password:
            raise QRZError("QRZ credentials are not configured")
        # Serialize session renewal so concurrent slash commands share the current key.
        async with self._lock:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                for attempt in range(2):
                    if not self._key:
                        await self._login(session)
                    root = await self._request(session, {"s": self._key, "callsign": callsign.strip().upper()})
                    self._key = root.findtext("{*}Session/{*}Key", "").strip()
                    error = root.findtext("{*}Session/{*}Error", "").strip()
                    if error.lower().startswith("not found") or error.lower().startswith("callsign not found"):
                        return None
                    if not self._key and attempt == 0:
                        continue
                    if error or not self._key:
                        raise QRZError("QRZ lookup failed")
                    entry = root.find("{*}Callsign")
                    if entry is None or not entry.findtext("{*}call", "").strip():
                        raise QRZError("QRZ response is missing callsign data")
                    return QRZEntry(*(entry.findtext(f"{{*}}{field}", "").strip()
                                      for field in ("call", "fname", "name", "addr2", "country")))
        raise QRZError("QRZ session renewal failed")
