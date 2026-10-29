import json
from pathlib import Path

from hetzner.client import parse_servers
from hetzner.cpus import cores_for


def test_known_cpus():
    assert cores_for("AMD Ryzen 9 5950X") == 16
    assert cores_for("Intel Xeon Gold 5412U") == 24
    assert cores_for("Intel Core i7-6700") == 4


def test_unknown_cpu_returns_none():
    assert cores_for("AMD Threadripper 9999X") is None


def test_every_cpu_in_fixture_is_known():
    payload = json.loads(Path("tests/fixtures/auction_snapshot.json").read_text("utf-8"))
    unknown = {s.cpu_name for s in parse_servers(payload) if cores_for(s.cpu_name) is None}
    assert unknown == set(), f"CPU-Tabelle ergaenzen: {sorted(unknown)}"
