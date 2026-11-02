import asyncio
from unittest.mock import patch
from xml.sax.saxutils import escape

import pytest

from elmar.qrz import QRZClient, QRZEntry, QRZError


def xml(*, key="session", error="", entry="", namespace=True):
    xmlns = ' xmlns="http://xmldata.qrz.com"' if namespace else ""
    key_node = f"<Key>{key}</Key>" if key else ""
    return (f"<QRZDatabase{xmlns}><Session>{key_node}<Error>{escape(error)}</Error>"
            f"</Session>{entry}</QRZDatabase>").encode()


ENTRY = "<Callsign><call>TF3IRA</call><fname>Jón &amp; María</fname><name>Prófun</name><addr2>Reykjavík</addr2><country>Iceland</country><unknown>ignored</unknown></Callsign>"


class Response:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status
        self.content = self

    async def iter_chunked(self, size):
        # Several chunks exercise incremental XML download handling.
        for offset in range(0, len(self.body), 17):
            yield self.body[offset:offset + 17]

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class Session:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []

    def post(self, url, *, data, allow_redirects):
        assert url == "https://xmldata.qrz.com/xml/current/"
        assert allow_redirects is False
        self.requests.append(data)
        return next(self.responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def test_login_lookup_cache_and_rotated_keys():
    async def run():
        session = Session(Response(xml()), Response(xml(key="rotated", entry=ENTRY)),
                          Response(xml(entry=ENTRY, namespace=False)))
        client = QRZClient("username", "p&ss;word")
        with patch("elmar.qrz.aiohttp.ClientSession", return_value=session):
            assert await client.lookup(" tf3ira ") == QRZEntry("TF3IRA", "Jón & María", "Prófun", "Reykjavík", "Iceland")
            await client.lookup("TF3IRA")
        assert session.requests == [
            {"username": "username", "password": "p&ss;word", "agent": "Elmar/0.3"},
            {"s": "session", "callsign": "TF3IRA"},
            {"s": "rotated", "callsign": "TF3IRA"},
        ]
    asyncio.run(run())


@pytest.mark.parametrize("error", ["Not found: TF3HX", "Callsign not found"])
def test_missing_callsign(error):
    async def run():
        session = Session(Response(xml()), Response(xml(error=error)))
        with patch("elmar.qrz.aiohttp.ClientSession", return_value=session):
            assert await QRZClient("user", "pass").lookup("TF3HX") is None
    asyncio.run(run())


def test_session_expiry_reauthenticates_once():
    async def run():
        session = Session(Response(xml()), Response(xml(key="", error="Session Timeout")),
                          Response(xml(key="new")), Response(xml(entry=ENTRY)))
        with patch("elmar.qrz.aiohttp.ClientSession", return_value=session):
            assert (await QRZClient("user", "pass").lookup("TF3IRA")).callsign == "TF3IRA"
        assert session.requests[-1] == {"s": "new", "callsign": "TF3IRA"}
    asyncio.run(run())


def test_user_example_non_subscriber_response():
    async def run():
        body = b'''<?xml version="1.0" encoding="utf-8" ?>
<QRZDatabase version="1.36" xmlns="http://xmldata.qrz.com">
<Callsign>
<call>TF3HR</call><fname>Hrafnkell</fname><name>Eiriksson</name>
<addr2>Kopavogur</addr2><country>Iceland</country>
</Callsign>
<Session>
<Key>example-session</Key><Count>148</Count><SubExp>non-subscriber</SubExp>
<Message>A subscription is required to access the complete record.</Message>
<GMTime>Mon Nov  2 21:29:53 2026</GMTime><Remark>cpu: 0.018s</Remark>
</Session>
</QRZDatabase>'''
        session = Session(Response(xml()), Response(body))
        with patch("elmar.qrz.aiohttp.ClientSession", return_value=session):
            entry = await QRZClient("user", "pass").lookup("tf3hr")
        from elmar.qrz_discord import entry_text
        assert entry_text(entry) == (
            "[TF3HR](<https://www.qrz.com/db/TF3HR>) - Hrafnkell Eiriksson - Kopavogur Iceland")
    asyncio.run(run())


@pytest.mark.parametrize("response", [
    Response(xml(key="", error="Invalid password")),
    Response(b"not XML"),
    Response(b"<html/>"),
    Response(b"", status=503),
])
def test_login_failures_raise_service_error(response):
    async def run():
        session = Session(response)
        with patch("elmar.qrz.aiohttp.ClientSession", return_value=session):
            with pytest.raises(QRZError):
                await QRZClient("user", "pass").lookup("TF3IRA")
    asyncio.run(run())


@pytest.mark.parametrize("result", [
    xml(error="Subscription required"),
    xml(),
    xml(key="", error="Invalid session key"),
])
def test_lookup_errors_are_not_reported_as_missing(result):
    async def run():
        session = Session(Response(xml()), Response(result), Response(xml()), Response(result))
        with patch("elmar.qrz.aiohttp.ClientSession", return_value=session):
            with pytest.raises(QRZError):
                await QRZClient("user", "pass").lookup("TF3IRA")
        assert len(session.requests) <= 4
    asyncio.run(run())


def test_credentials_optional_until_lookup():
    with pytest.raises(QRZError, match="not configured"):
        asyncio.run(QRZClient().lookup("TF3IRA"))
