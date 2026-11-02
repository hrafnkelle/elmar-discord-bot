import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from elmar.bot import Elmar
from elmar.kindex import Progress, Reading
from elmar.kindex_discord import KIndexCommands
from elmar.kindex_service import KIndexConfig
from elmar.registry import Registry


def registry():
    return Registry.load(Path(__file__).resolve().parents[1] / "data/callsigns.json")


def test_kindex_command_private_cached_bilingual_and_no_mentions():
    async def run():
        monitor = SimpleNamespace(progress=Progress(Reading(datetime(2026, 11, 1, 21, tzinfo=UTC), 6)),
                                  checked_at=None, source_error=False)
        group = KIndexCommands(monitor)
        interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))
        for language, expected in [("íslenska", "K-stuðull"), ("English", "Local K")]:
            await group.current.callback(group, interaction, language)
            args = interaction.response.send_message.call_args
            assert expected in args.args[0]
            assert "k_lrv1a.gif" in args.args[0]
            assert args.kwargs["ephemeral"] is True
            assert args.kwargs["allowed_mentions"].to_dict() == {"parse": []}
            assert "HF" not in args.args[0]
            await group.current.callback(group, interaction, language, itarlegt=True)
            detailed = interaction.response.send_message.call_args
            assert "HF" in detailed.args[0] and "k_lrv1a.txt" in detailed.args[0]
            assert detailed.kwargs["ephemeral"] is True
    asyncio.run(run())


def test_all_command_groups_register_and_pollers_close(tmp_path):
    async def run():
        async with Elmar(registry(), 123, KIndexConfig(str(tmp_path / "state.sqlite3"))) as client:
            commands = client.tree.get_commands(guild=client.guild)
            assert {c.name for c in commands} == {"kallmerki", "kindex", "fof2", "skipanir", "qrz"}
            payload = next(c for c in commands if c.name == "kindex").to_dict(client.tree)
            assert payload["options"][0]["name"] == "nuna"
            fof2_payload = next(c for c in commands if c.name == "fof2").to_dict(client.tree)
            assert fof2_payload["options"][0]["name"] == "nuna"
            assert client.intents.value == 0
            client.tree.sync = AsyncMock(return_value=commands)
            client.kindex.run = AsyncMock()
            await client.setup_hook()
            assert client.kindex_task is not None
            assert client.fof2_task is not None
            # Cancel the task waiting for Discord readiness on context exit.
        assert client.kindex_task.cancelled()
        assert client.fof2_task.cancelled()
    asyncio.run(run())


def test_channel_alert_and_wrong_server_rejection(tmp_path):
    async def run():
        config = KIndexConfig(str(tmp_path / "state.sqlite3"), 456)
        async with Elmar(registry(), 123, config) as client:
            channel = Mock(spec=discord.TextChannel)
            channel.guild = SimpleNamespace(id=123)
            channel.send = AsyncMock()
            client.fetch_channel = AsyncMock(return_value=channel)
            reading = Reading(datetime(2026, 11, 1, 21, tzinfo=UTC), 6)
            await client.send_kindex_alert(reading)
            assert "hækkar í 6" in channel.send.call_args.args[0]
            assert channel.send.call_args.kwargs["allowed_mentions"].to_dict() == {"parse": []}
            channel.guild.id = 999
            with pytest.raises(ValueError, match="configured server"):
                await client.send_kindex_alert(reading)
            assert channel.send.await_count == 1
    asyncio.run(run())
