from datetime import UTC, datetime, timedelta

from hetzner_bot import healthcheck


def test_fresh_heartbeat_is_healthy(tmp_path, monkeypatch):
    path = tmp_path / "last_poll"
    path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    monkeypatch.setenv("LAST_POLL_FILE", str(path))
    assert healthcheck.main() == 0


def test_missing_heartbeat_is_unhealthy(tmp_path, monkeypatch):
    monkeypatch.setenv("LAST_POLL_FILE", str(tmp_path / "fehlt"))
    assert healthcheck.main() == 1


def test_stale_heartbeat_is_unhealthy(tmp_path, monkeypatch):
    path = tmp_path / "last_poll"
    old = datetime.now(UTC) - timedelta(minutes=90)
    path.write_text(old.isoformat(), encoding="utf-8")
    monkeypatch.setenv("LAST_POLL_FILE", str(path))
    assert healthcheck.main() == 1
