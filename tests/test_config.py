from datetime import datetime, timezone

import pytest

from watcher.config import Config, parse_ref


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        ("@name", "@name"),
        ("name", "name"),
        ("https://t.me/name/123", "name"),
        ("t.me/name", "name"),
        ("-1001234567890", -1001234567890),
    ],
)
def test_parse_ref(ref, expected):
    assert parse_ref(ref) == expected


def test_from_env(monkeypatch):
    monkeypatch.setenv("API_ID", "1")
    monkeypatch.setenv("API_HASH", "hash")
    monkeypatch.setenv("SOURCE_CHANNELS", "@a, https://t.me/b ,")
    monkeypatch.setenv("TARGET_CHANNEL", "@me")
    monkeypatch.setenv("TZ_OFFSET", "5")

    config = Config.from_env()

    assert config.sources == ["@a", "b"]
    moment = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    assert config.format_time(moment) == "01.01.2026 05:00:00 UTC+5"
