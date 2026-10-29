# Hetzner-Auktions-Bot für Discord — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein Discord-Bot, der die Hetzner-Serverbörse alle 10 Minuten liest, pro Person gespeicherte Filter prüft und nur passende Server in einen festgelegten Kanal postet — mit optionalem Ping und erneuter Meldung bei Preisrückgang.

**Architecture:** Python-Prozess mit `discord.py`, der einen `tasks.loop` alle 10 Minuten laufen lässt. Ein reiner Parser macht aus der Auktions-JSON `Server`-Dataclasses, eine reine Matching-Funktion vergleicht sie mit den Filtern aus SQLite, und eine dünne Discord-Schicht baut Embeds und postet. Die Kernlogik (Parsen, Filtern, Dedupe, Preisverfall) ist ohne Discord und ohne Netzwerk testbar.

**Tech Stack:** Python 3.12, `discord.py` 2.4+, `httpx`, `python-dotenv`, SQLite (`sqlite3`), `pytest`, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-29-hetzner-auktion-discord-bot-design.md`

## Global Constraints

- Python 3.12, keine weiteren Laufzeit-Abhängigkeiten außer `discord.py`, `httpx`, `python-dotenv`.
- Bot-Sprache Deutsch, Code-Bezeichner englisch.
- Preise als `Decimal`, immer aus `str(wert)` gebaut, nie `Decimal(float)`.
- Zeiten in UTC speichern, in Europe/Berlin anzeigen (`zoneinfo`).
- `DISCORD_TOKEN` nur aus `.env`; `.env` und `data/` sind in `.gitignore`.
- Poll-Intervall 10 Minuten, maximal 15 Posts pro Lauf.
- Datenquelle: `https://www.hetzner.com/_resources/app/data/app/live_data_sb.json`, ein GET pro Lauf, Timeout 10 s, 3 Versuche.
- Bots können nicht in Gruppen-DMs arbeiten; der Bot rechnet mit Guild + Kanal.
- Tests sprechen nie mit dem Netz: Fixture oder `httpx.MockTransport`.

## Review Focus

- **Server verschwindet zwischen zwei Läufen:** Ein Server aus der Warteschlange, der nicht mehr im Snapshot steht, darf keinen Fehler auslösen, sondern fällt still aus der Warteschlange.
- **Fehlende Felder in der JSON:** Ein Server ohne `Hardware.Storage.Details` oder ohne `Timer` darf den ganzen Lauf nicht abbrechen — Defaults, kein `KeyError`.
- **Preisgleichstand und Cent-Differenzen:** `73.7` aus JSON muss als `Decimal("73.7")` ankommen; ein um 1 Cent gesunkener Preis muss als Rückgang erkannt werden, ein gleicher Preis nicht.
- **Kanal fehlt oder keine Rechte:** Ein kaputter Kanal darf den Loop nicht töten und nicht 15-mal pro Lauf retryen — Zähler, nach 3 Versuchen verwerfen.
- **Zwei Filter derselben Person treffen denselben Server:** genau ein Post, genau ein Ping.

---

### Task 1: Projektgerüst und Konfiguration

**Files:**
- Create: `.gitignore`, `requirements.txt`, `.env.example`, `config.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: nichts
- Produces: `Config` (frozen dataclass: `discord_token: str`, `database_path: Path`, `auction_url: str`, `poll_minutes: int`, `max_posts_per_run: int`, `log_level: str`), `ConfigError(RuntimeError)`, `load_config(env: Mapping[str, str] | None = None) -> Config`

- [ ] **Step 1: Repository und Abhängigkeiten anlegen**

```bash
git init
mkdir tests
```

`.gitignore`:

```
.env
data/
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

`requirements.txt`:

```
discord.py>=2.4,<3
httpx>=0.27,<1
python-dotenv>=1.0,<2
pytest>=8.0,<9
```

`.env.example`:

```
DISCORD_TOKEN=dein-bot-token
DATABASE_PATH=data/bot.sqlite3
POLL_MINUTES=10
MAX_POSTS_PER_RUN=15
LOG_LEVEL=INFO
```

- [ ] **Step 2: Failing test schreiben**

`tests/test_config.py`:

```python
from pathlib import Path
import pytest
from config import ConfigError, load_config

def test_load_config_uses_defaults():
    cfg = load_config({"DISCORD_TOKEN": "abc"})
    assert cfg.poll_minutes == 10
    assert cfg.max_posts_per_run == 15
    assert cfg.database_path == Path("data/bot.sqlite3")
    assert cfg.auction_url.endswith("live_data_sb.json")

def test_load_config_requires_token():
    with pytest.raises(ConfigError):
        load_config({})

def test_load_config_rejects_non_positive_interval():
    with pytest.raises(ConfigError):
        load_config({"DISCORD_TOKEN": "abc", "POLL_MINUTES": "0"})
```

- [ ] **Step 3: Test laufen lassen und Fehlschlag bestätigen**

Run: `pytest tests/test_config.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 4: `config.py` implementieren**

`load_config` liest aus `os.environ`, wenn `env=None`. Fehlender oder leerer Token → `ConfigError("DISCORD_TOKEN fehlt")`. `POLL_MINUTES` und `MAX_POSTS_PER_RUN` müssen ganze Zahlen > 0 sein, sonst `ConfigError`. `AUCTION_URL` ist überschreibbar, Default ist die Hetzner-URL aus den Global Constraints.

- [ ] **Step 5: Tests laufen lassen**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt .env.example config.py tests/test_config.py
git commit -m "chore: Projektgerüst und Konfiguration"
```

---

### Task 2: Fixture und Parser

**Files:**
- Create: `tests/fixtures/auction_snapshot.json`, `hetzner/__init__.py`, `hetzner/models.py`, `hetzner/client.py`, `tests/test_parse.py`

**Interfaces:**
- Consumes: nichts
- Produces: `Server` (frozen dataclass: `id: int`, `cpu_name: str`, `sockets: int`, `ram_gb: int`, `ecc: bool`, `storage_total_gb: int`, `nvme_gb: int`, `sata_gb: int`, `hdd_gb: int`, `location: str`, `datacenter: str`, `bandwidth_mbit: int`, `traffic: str`, `price_month_eur: Decimal`, `price_hour_eur: Decimal`, `setup_eur: Decimal`, `extra_ips: int`, `reduce_next_at: datetime | None`), `parse_servers(payload: dict) -> list[Server]`

- [ ] **Step 1: Echten Snapshot einmalig ziehen**

```bash
mkdir -p tests/fixtures
curl.exe -s -o tests/fixtures/auction_snapshot.json "https://www.hetzner.com/_resources/app/data/app/live_data_sb.json"
```

Nur einmal. Danach nie wieder live im Test. Datei committen — sie ist die Grundlage aller Parser- und Matching-Tests.

- [ ] **Step 2: Failing tests schreiben**

`tests/test_parse.py`:

```python
import json
from decimal import Decimal
from pathlib import Path
from hetzner.client import parse_servers

FIXTURE = json.loads(Path("tests/fixtures/auction_snapshot.json").read_text("utf-8"))

def test_parse_returns_all_servers():
    servers = parse_servers(FIXTURE)
    assert len(servers) == len(FIXTURE["server"])
    assert len(servers) > 0

def test_parse_prices_are_exact_decimals():
    servers = {s.id: s for s in parse_servers(FIXTURE)}
    server = next(s for s in servers.values() if s.price_month_eur == Decimal("72"))
    assert str(server.price_month_eur) == "72"
    assert isinstance(server.price_hour_eur, Decimal)

def test_parse_extracts_storage_and_location():
    server = parse_servers(FIXTURE)[0]
    assert server.storage_total_gb > 0
    assert server.datacenter.startswith(("FSN", "NBG", "HEL"))

def test_parse_survives_missing_fields():
    payload = {"server": [{"Id": 1, "Hardware": {}, "Prices": {}, "Details": {}, "Timer": {}}]}
    servers = parse_servers(payload)
    assert servers[0].id == 1
    assert servers[0].price_month_eur == Decimal("0")
    assert servers[0].reduce_next_at is None
```

- [ ] **Step 3: Test laufen lassen**

Run: `pytest tests/test_parse.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'hetzner'`

- [ ] **Step 4: `hetzner/models.py` und `hetzner/client.py` implementieren**

`Server` als frozen dataclass ohne Logik. `parse_servers` liest mit `.get()`-Ketten und Defaults:

- `price_month_eur = Decimal(str(Prices.monthly.EUR))`, Default `Decimal("0")`
- `storage_total_gb = Hardware.Storage.Size`, Default 0
- `nvme_gb/sata_gb/hdd_gb` = `sum(Details.Storage.Details.<typ>)`, Default 0
- `location` = Präfix des Datacenter-Namens vor dem ersten `-` (`FSN1-DC14` → `"FSN1"`), und daraus `FSN`/`NBG`/`HEL` ableiten; unbekannt → `""`
- `reduce_next_at` = `datetime.fromtimestamp(Timer.ReduceNextTimestamp, tz=UTC)`, bei 0/fehlend `None`
- `sockets = Hardware.CPU.CoreCount`, `ram_gb = Hardware.RAM.Size`, `ecc = Hardware.RAM.ecc is True`, `bandwidth_mbit = Details.Bandwidth`, `traffic = Details.Traffic or ""`, `extra_ips = IPPrices.Amount or 0`

Kein Feld darf eine Exception werfen.

- [ ] **Step 5: Tests laufen lassen**

Run: `pytest tests/test_parse.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add hetzner tests/fixtures tests/test_parse.py
git commit -m "feat: Parser fuer die Hetzner-Auktionsdaten"
```

---

### Task 3: HTTP-Abruf mit Retry

**Files:**
- Create: `tests/test_fetch.py`
- Modify: `hetzner/client.py`

**Interfaces:**
- Consumes: `parse_servers`
- Produces: `async def fetch_servers(client: httpx.AsyncClient, url: str = AUCTION_URL) -> list[Server]`, `class FetchError(RuntimeError)`

- [ ] **Step 1: Failing test schreiben**

`tests/test_fetch.py`:

```python
import httpx
import pytest
from hetzner.client import FetchError, fetch_servers

PAYLOAD = {"server": [{"Id": 7, "Hardware": {}, "Prices": {}, "Details": {}, "Timer": {}}]}

@pytest.mark.asyncio
async def test_fetch_parses_response():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=PAYLOAD))
    async with httpx.AsyncClient(transport=transport) as client:
        servers = await fetch_servers(client, "https://example.invalid/sb.json")
    assert servers[0].id == 7

@pytest.mark.asyncio
async def test_fetch_retries_then_raises():
    calls = {"n": 0}
    def handler(request):
        calls["n"] += 1
        return httpx.Response(500)
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(FetchError):
            await fetch_servers(client, "https://example.invalid/sb.json", retries=3, backoff=0)
    assert calls["n"] == 3
```

`pytest-asyncio` in `requirements.txt` ergänzen und `asyncio_mode = auto` in `pyproject.toml` (`[tool.pytest.ini_options]`) setzen.

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_fetch.py -v`
Expected: FAIL, `ImportError: cannot import name 'fetch_servers'`

- [ ] **Step 3: `fetch_servers` implementieren**

Signatur mit Defaults `retries: int = 3`, `backoff: float = 1.0`. Bei Status != 200 oder `httpx.HTTPError` erneut versuchen, Wartezeit `backoff * 2**versuch`. Nach dem letzten Fehlversuch `FetchError` mit letztem Fehlertext. Erfolg → `response.json()` an `parse_servers`.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_fetch.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add hetzner/client.py tests/test_fetch.py requirements.txt pyproject.toml
git commit -m "feat: HTTP-Abruf mit Retry"
```

---

### Task 4: CPU-Tabelle

**Files:**
- Create: `hetzner/cpus.py`, `tests/test_cpus.py`

**Interfaces:**
- Consumes: `Server.cpu_name`
- Produces: `CORES_BY_CPU: dict[str, int]`, `cores_for(cpu_name: str) -> int | None`

- [ ] **Step 1: Failing tests schreiben**

`tests/test_cpus.py`:

```python
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
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_cpus.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'hetzner.cpus'`

- [ ] **Step 3: `hetzner/cpus.py` anlegen**

Exakte Zuordnung (physische Kerne):

```
AMD EPYC 7502P 32
AMD Ryzen 5 3600 6
AMD Ryzen 7 1700X 8
AMD Ryzen 7 3700X 8
AMD Ryzen 7 7700 8
AMD Ryzen 7 PRO 1700X 8
AMD Ryzen 9 3900 12
AMD Ryzen 9 5950X 16
Intel Core i5-12500 6
Intel Core i5-13500 14
Intel Core i7-6700 4
Intel Core i7-7700 4
Intel Core i7-8700 6
Intel Core i9-12900K 16
Intel Core i9-13900 24
Intel Core i9-9900K 8
Intel Xeon E3-1270V3 4
Intel Xeon E3-1271V3 4
Intel Xeon E3-1275v5 4
Intel Xeon E3-1275V6 4
Intel Xeon E5-1650V3 6
Intel Xeon Gold 5412U 24
Intel Xeon W-2145 8
Intel Xeon W-2295 18
```

`cores_for` normalisiert mit `.strip().lower()` gegen eine daraus gebaute Lookup-Map, damit Groß-/Kleinschreibung nicht beißt.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_cpus.py -v`
Expected: 3 passed. Der Fixture-Test ist der Wächter: sobald Hetzner eine neue CPU in die Auktion legt, schlägt er fehl.

- [ ] **Step 5: Commit**

```bash
git add hetzner/cpus.py tests/test_cpus.py
git commit -m "feat: CPU-Tabelle fuer Kernzahlen"
```

---

### Task 5: Filterkriterien und Validierung

**Files:**
- Create: `filters.py`, `tests/test_criteria.py`

**Interfaces:**
- Consumes: nichts
- Produces: `CriteriaError(ValueError)`, `Criteria` (frozen dataclass: `max_price: Decimal | None`, `min_ram: int | None`, `min_cores: int | None`, `cpu_contains: str | None`, `min_disk: Decimal | None`, `disk_type: str`, `location: str`, `ecc: str`, `no_setup: bool`, `min_bandwidth: int | None`), `Criteria.has_criterion() -> bool`, `Criteria.validate() -> None`, `Criteria.to_json() -> dict`, `Criteria.from_json(dict) -> Criteria`, `FilterRecord` (frozen dataclass: `id: int`, `guild_id: int`, `user_id: int`, `name: str`, `criteria: Criteria`, `mention: bool`, `active: bool`)

- [ ] **Step 1: Failing tests schreiben**

`tests/test_criteria.py`:

```python
from decimal import Decimal
import pytest
from filters import Criteria, CriteriaError

def test_empty_criteria_is_rejected():
    with pytest.raises(CriteriaError):
        Criteria().validate()

def test_mention_alone_is_not_a_criterion():
    assert Criteria().has_criterion() is False
    assert Criteria(max_price=Decimal("50")).has_criterion() is True

def test_price_must_be_positive():
    with pytest.raises(CriteriaError):
        Criteria(max_price=Decimal("0")).validate()

def test_unknown_location_is_rejected():
    with pytest.raises(CriteriaError):
        Criteria(location="XYZ").validate()

def test_json_roundtrip():
    original = Criteria(max_price=Decimal("45.5"), min_ram=64, disk_type="nvme", ecc="ja")
    assert Criteria.from_json(original.to_json()) == original

def test_from_json_tolerates_unknown_keys():
    assert Criteria.from_json({"max_price": 50, "gibt_es_nicht": 1}) == Criteria(max_price=Decimal("50"))
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_criteria.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'filters'`

- [ ] **Step 3: `filters.py` implementieren**

Erlaubte Werte: `disk_type ∈ {egal, nvme, sata, hdd}`, `location ∈ {egal, FSN, NBG, HEL}`, `ecc ∈ {egal, ja}`. Alle Zahlen > 0. `cpu_contains` wird getrimmt, leer → `None`. `from_json` baut `Decimal(str(wert))` und ignoriert unbekannte Schlüssel. `has_criterion` prüft nur echte Kriterien — `mention` ist nicht Teil von `Criteria`.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_criteria.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add filters.py tests/test_criteria.py
git commit -m "feat: Filterkriterien mit Validierung"
```

---

### Task 6: Matching

**Files:**
- Create: `tests/test_matching.py`
- Modify: `filters.py`

**Interfaces:**
- Consumes: `Criteria`, `Server`, `cores_for`
- Produces: `matches(criteria: Criteria, server: Server) -> bool`

- [ ] **Step 1: Failing tests schreiben**

`tests/test_matching.py` (Builder-Funktion für Testserver am Dateikopf):

```python
from decimal import Decimal
from filters import Criteria, matches
from hetzner.models import Server

def make_server(**over):
    base = dict(id=1, cpu_name="AMD Ryzen 9 5950X", sockets=1, ram_gb=64, ecc=True,
                storage_total_gb=4096, nvme_gb=0, sata_gb=0, hdd_gb=8000,
                location="FSN", datacenter="FSN1-DC14", bandwidth_mbit=1000,
                traffic="unlimited", price_month_eur=Decimal("45"),
                price_hour_eur=Decimal("0.05"), setup_eur=Decimal("0"),
                extra_ips=1, reduce_next_at=None)
    base.update(over)
    return Server(**base)

def test_price_boundary_is_inclusive():
    assert matches(Criteria(max_price=Decimal("45")), make_server()) is True
    assert matches(Criteria(max_price=Decimal("44.99")), make_server()) is False

def test_min_cores_uses_table_and_skips_unknown():
    assert matches(Criteria(min_cores=16), make_server()) is True
    assert matches(Criteria(min_cores=17), make_server()) is False
    assert matches(Criteria(min_cores=4), make_server(cpu_name="Unbekannt")) is False

def test_cpu_contains_is_case_insensitive():
    assert matches(Criteria(cpu_contains="ryzen 9"), make_server()) is True

def test_disk_type_requires_type_and_sums_that_type_only():
    assert matches(Criteria(disk_type="hdd", min_disk=Decimal("8")), make_server()) is True
    assert matches(Criteria(disk_type="nvme", min_disk=Decimal("1")), make_server()) is False
    assert matches(Criteria(disk_type="nvme"), make_server(nvme_gb=1000)) is True

def test_min_disk_without_type_uses_usable_total():
    assert matches(Criteria(min_disk=Decimal("4")), make_server(storage_total_gb=4096)) is True
    assert matches(Criteria(min_disk=Decimal("2")), make_server(storage_total_gb=1966)) is False

def test_no_setup_and_location_and_bandwidth():
    assert matches(Criteria(no_setup=True), make_server(setup_eur=Decimal("0"))) is True
    assert matches(Criteria(no_setup=True), make_server(setup_eur=Decimal("49"))) is False
    assert matches(Criteria(location="FSN"), make_server(location="FSN")) is True
    assert matches(Criteria(location="NBG"), make_server(location="FSN")) is False
    assert matches(Criteria(min_bandwidth=1000), make_server(bandwidth_mbit=1000)) is True
    assert matches(Criteria(min_bandwidth=1000), make_server(bandwidth_mbit=100)) is False

def test_ecc_and_all_criteria_together():
    assert matches(Criteria(ecc="ja"), make_server(ecc=False)) is False
    both = Criteria(max_price=Decimal("50"), min_ram=64, min_cores=16, ecc="ja")
    assert matches(both, make_server()) is True
    assert matches(both, make_server(ram_gb=32)) is False
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_matching.py -v`
Expected: FAIL, `ImportError: cannot import name 'matches'`

- [ ] **Step 3: `matches` implementieren**

Jedes gesetzte Kriterium ist ein UND. Vergleiche:

- `max_price`: `server.price_month_eur <= criteria.max_price`
- `min_ram`: `server.ram_gb >= min_ram`
- `min_cores`: `cores_for(server.cpu_name)` ist nicht `None` und `>= min_cores`
- `cpu_contains`: `cpu_contains.lower() in server.cpu_name.lower()`
- `min_disk` bei `disk_type == "egal"`: `server.storage_total_gb >= min_disk * 1000`
- `min_disk` mit Typ: `pool = {"nvme": nvme_gb, "sata": sata_gb, "hdd": hdd_gb}[disk_type]` und `pool > 0` und `pool >= min_disk * 1000`
- `disk_type` ohne `min_disk`: `pool > 0`
- `location`: Gleichheit, bei `egal` ignorieren
- `ecc`: `ja` → `server.ecc is True`
- `no_setup`: `server.setup_eur == 0`
- `min_bandwidth`: `server.bandwidth_mbit >= min_bandwidth`

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_matching.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add filters.py tests/test_matching.py
git commit -m "feat: Filter-Matching"
```

---

### Task 7: SQLite-Speicher

**Files:**
- Create: `store.py`, `tests/test_store.py`

**Interfaces:**
- Consumes: `Criteria`, `FilterRecord`
- Produces: `class Store`, `QueuedItem` (frozen dataclass: `guild_id: int`, `server_id: int`, `filter_ids: tuple[int, ...]`, `attempts: int`). Methoden: `__init__(path)`, `init_schema()`, `close()`, `set_channel(guild_id, channel_id)`, `get_channel(guild_id) -> int | None`, `save_filter(guild_id, user_id, name, criteria, mention) -> FilterRecord`, `get_filter(guild_id, user_id, name) -> FilterRecord | None`, `list_filters(guild_id=None, user_id=None, active_only=False) -> list[FilterRecord]`, `delete_filter(guild_id, user_id, name) -> bool`, `set_active(guild_id, user_id, name, active) -> bool`, `mark_seen(filter_id, server_ids)`, `is_seen(filter_id, server_id) -> bool`, `last_price(guild_id, server_id) -> Decimal | None`, `record_post(guild_id, server_id, price)`, `enqueue(guild_id, server_id, filter_ids)`, `queued() -> list[QueuedItem]`, `dequeue(guild_id, server_id)`, `bump_attempts(guild_id, server_id) -> int`

- [ ] **Step 1: Failing tests schreiben**

`tests/test_store.py`:

```python
from decimal import Decimal
import pytest
from filters import Criteria
from store import Store

@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.sqlite3")
    s.init_schema()
    yield s
    s.close()

def test_channel_roundtrip(store):
    assert store.get_channel(1) is None
    store.set_channel(1, 99)
    assert store.get_channel(1) == 99

def test_save_filter_replaces_by_name(store):
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    record = store.save_filter(1, 2, "standard", Criteria(min_ram=128), mention=True)
    assert record.criteria.min_ram == 128
    assert record.mention is True
    assert len(store.list_filters(1, 2)) == 1

def test_delete_and_pause(store):
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    assert store.set_active(1, 2, "standard", False) is True
    assert store.list_filters(1, 2, active_only=True) == []
    assert store.delete_filter(1, 2, "standard") is True
    assert store.get_filter(1, 2, "standard") is None

def test_seen_is_per_filter(store):
    a = store.save_filter(1, 2, "a", Criteria(min_ram=64), mention=False)
    b = store.save_filter(1, 3, "b", Criteria(min_ram=64), mention=False)
    store.mark_seen(a.id, [10, 11])
    assert store.is_seen(a.id, 10) is True
    assert store.is_seen(b.id, 10) is False

def test_posts_are_per_guild(store):
    store.record_post(1, 10, Decimal("45"))
    assert store.last_price(1, 10) == Decimal("45")
    assert store.last_price(2, 10) is None

def test_queue_roundtrip_and_attempts(store):
    store.enqueue(1, 10, (5, 6))
    item = store.queued()[0]
    assert item.filter_ids == (5, 6)
    assert store.bump_attempts(1, 10) == 1
    store.dequeue(1, 10)
    assert store.queued() == []
```

`list_filters` bekommt einen Parameter `active_only: bool = False`.

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_store.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'store'`

- [ ] **Step 3: `store.py` implementieren**

Schema exakt wie im Design: `guilds`, `filters`, `seen`, `posts`, `queue`. `PRAGMA journal_mode=WAL`, `PRAGMA foreign_keys=ON`. `save_filter` ist `INSERT ... ON CONFLICT(guild_id, user_id, name) DO UPDATE`, gibt danach den gespeicherten `FilterRecord` zurück (ID bleibt stabil). `record_post` überschreibt `last_price_eur` (als `TEXT` gespeichert, mit `Decimal(...)` zurückgelesen). `bump_attempts` erhöht und gibt den neuen Stand zurück.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_store.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add store.py tests/test_store.py
git commit -m "feat: SQLite-Speicher fuer Filter, Posts und Warteschlange"
```

---

### Task 8: Dedupe- und Preisverfall-Logik

**Files:**
- Create: `poller.py`, `tests/test_candidates.py`

**Interfaces:**
- Consumes: `Server`, `FilterRecord`, `matches`
- Produces: `Candidate` (frozen dataclass: `guild_id: int`, `server: Server`, `filter_ids: tuple[int, ...]`, `user_ids: tuple[int, ...]`, `previous_price: Decimal | None`), `find_candidates(servers, filters, is_seen: Callable[[int, int], bool], last_price: Callable[[int, int], Decimal | None]) -> list[Candidate]`

- [ ] **Step 1: Failing tests schreiben**

`tests/test_candidates.py`:

```python
from decimal import Decimal
from filters import Criteria, FilterRecord
from hetzner.models import Server
from poller import find_candidates

def server(id=10, price="45", **over):
    data = dict(id=id, cpu_name="AMD Ryzen 9 5950X", sockets=1, ram_gb=64, ecc=True,
                storage_total_gb=4096, nvme_gb=0, sata_gb=0, hdd_gb=8000,
                location="FSN", datacenter="FSN1-DC14", bandwidth_mbit=1000,
                traffic="unlimited", price_month_eur=Decimal(price),
                price_hour_eur=Decimal("0.05"), setup_eur=Decimal("0"),
                extra_ips=1, reduce_next_at=None)
    data.update(over)
    return data

def flt(id=1, guild=1, user=2, mention=True, active=True, **crit):
    return FilterRecord(id=id, guild_id=guild, user_id=user, name=f"f{id}",
                        criteria=Criteria(**crit), mention=mention, active=active)

def test_new_server_is_candidate():
    out = find_candidates([server()], [flt(min_ram=64)], lambda f, s: False, lambda g, s: None)
    assert len(out) == 1
    assert out[0].user_ids == (2,)
    assert out[0].previous_price is None

def test_baselined_server_is_not_posted():
    out = find_candidates([server()], [flt(min_ram=64)], lambda f, s: True, lambda g, s: None)
    assert out == []

def test_price_drop_is_posted_even_if_seen():
    out = find_candidates([server(price="39")], [flt(min_ram=64)],
                          lambda f, s: True, lambda g, s: Decimal("45"))
    assert len(out) == 1
    assert out[0].previous_price == Decimal("45")

def test_same_price_is_not_posted():
    out = find_candidates([server(price="45")], [flt(min_ram=64)],
                          lambda f, s: True, lambda g, s: Decimal("45"))
    assert out == []

def test_one_post_per_server_and_guild_with_two_filters():
    out = find_candidates([server()], [flt(id=1, user=2), flt(id=2, user=3)],
                          lambda f, s: False, lambda g, s: None)
    assert len(out) == 1
    assert out[0].filter_ids == (1, 2)
    assert out[0].user_ids == (2, 3)

def test_same_user_two_filters_pings_once():
    out = find_candidates([server()], [flt(id=1, user=2), flt(id=2, user=2)],
                          lambda f, s: False, lambda g, s: None)
    assert out[0].user_ids == (2,)

def test_inactive_filters_and_non_matches_are_ignored():
    out = find_candidates([server()], [flt(active=False), flt(id=9, min_ram=512)],
                          lambda f, s: False, lambda g, s: None)
    assert out == []

def test_guilds_are_independent():
    out = find_candidates([server()], [flt(id=1, guild=1), flt(id=2, guild=2)],
                          lambda f, s: False, lambda g, s: None)
    assert {c.guild_id for c in out} == {1, 2}
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_candidates.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'poller'`

- [ ] **Step 3: `find_candidates` implementieren**

Pro Guild gruppieren, pro Server:

1. `eligible = [f for f in filters_of_guild if f.active and matches(f.criteria, server)]`
2. leer → weiter
3. `prev = last_price(guild_id, server.id)`
4. `prev is None`: nur posten, wenn **mindestens ein** `eligible`-Filter `is_seen` verneint. Sonst weiter.
5. `prev is not None`: nur posten, wenn `server.price_month_eur < prev`.
6. `filter_ids` = sortierte IDs aller eligible, `user_ids` = sortierte, eindeutige User-IDs der eligible mit `mention=True`.
7. Sortierung der Ausgabe: `(guild_id, server.price_month_eur, server.id)` aufsteigend, damit günstige Deals zuerst kommen.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_candidates.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add poller.py tests/test_candidates.py
git commit -m "feat: Dedupe und Preisverfall-Logik"
```

---

### Task 9: Embed-Bau

**Files:**
- Create: `notify.py`, `tests/test_notify.py`

**Interfaces:**
- Consumes: `Server`
- Produces: `build_embed(server: Server, previous_price: Decimal | None) -> discord.Embed`, `mention_prefix(user_ids: Sequence[int]) -> str`

- [ ] **Step 1: Failing tests schreiben**

`tests/test_notify.py`:

```python
from decimal import Decimal
from notify import build_embed, mention_prefix
from hetzner.models import Server

SERVER = Server(id=3101875, cpu_name="AMD Ryzen 9 5950X", sockets=1, ram_gb=64, ecc=True,
                storage_total_gb=4096, nvme_gb=2000, sata_gb=0, hdd_gb=8000,
                location="FSN", datacenter="FSN1-DC14", bandwidth_mbit=1000,
                traffic="unlimited", price_month_eur=Decimal("39"),
                price_hour_eur=Decimal("0.05"), setup_eur=Decimal("0"),
                extra_ips=1, reduce_next_at=None)

def field_text(embed, name):
    return next(f.value for f in embed.fields if f.name == name)

def test_embed_shows_key_specs():
    embed = build_embed(SERVER, None)
    assert "Ryzen 9 5950X" in embed.title
    assert "64 GB" in field_text(embed, "RAM")
    assert "FSN1-DC14" in field_text(embed, "Standort")
    assert "39" in field_text(embed, "Preis")

def test_embed_marks_price_drop():
    embed = build_embed(SERVER, Decimal("45"))
    assert "45" in field_text(embed, "Preis")
    assert "39" in field_text(embed, "Preis")
    assert "3101875" in embed.footer.text

def test_embed_without_drop_has_no_old_price():
    embed = build_embed(SERVER, None)
    assert "45" not in field_text(embed, "Preis")

def test_mention_prefix_deduplicates():
    assert mention_prefix([3, 1, 3]) == "<@1> <@3>"
    assert mention_prefix([]) == ""
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_notify.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'notify'`

- [ ] **Step 3: `notify.py` implementieren**

Titel: `f"{server.cpu_name} · {server.storage_total_gb // 1000} TB"`. Farbton `0x00A88F` (Hetzner-Grün). Felder: `Kerne` (aus `cores_for`, sonst `unbekannt`), `RAM` (`f"{ram_gb} GB" + " ECC"`), `Platten` (`2× HDD 4000 GB, 1× NVMe 2000 GB` aus den GB-Summen, 0-Werte weglassen, leer → `–`), `Standort` (`datacenter`), `Anbindung` (`f"{bandwidth_mbit} Mbit/s"`), `Preis` (`f"{price_month_eur} €/Monat · {price_hour_eur} €/Std · Setup {setup_eur} €"`; bei Preisfall zusätzlich `"vorher ~~45 €~~"`), `Server-ID` (inline). Footer: `"Hetzner Serverbörse · ID {id}"`. `url` = `https://www.hetzner.com/sb/`.

Kein `discord.py`-Client nötig — `discord.Embed` funktioniert allein.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_notify.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add notify.py tests/test_notify.py
git commit -m "feat: Embed-Bau fuer Treffer"
```

---

### Task 10: Bot-Gerüst und `/setup`

**Files:**
- Create: `bot.py`, `cogs/__init__.py`, `cogs/commands.py`, `tests/test_setup_command.py`

**Interfaces:**
- Consumes: `Config`, `Store`
- Produces: `class HetznerBot(commands.Bot)` mit Attributen `store: Store`, `config: Config`, `http: httpx.AsyncClient`, `tree: app_commands.CommandTree`; `HetznerBot.setup_hook()`, `on_ready()`; Cog `Commands` mit `/setup channel:<discord.TextChannel>` (Berechtigung `manage_guild`)

- [ ] **Step 1: Failing test schreiben**

`tests/test_setup_command.py` — testet die reine Logik, nicht Discord:

```python
import pytest
from cogs.commands import resolve_guild_id

class FakeGuild:
    id = 42

class FakeInteraction:
    def __init__(self, guild, user_permissions):
        self.guild = guild
        self.user = type("U", (), {"guild_permissions": user_permissions})()

def test_missing_guild_is_rejected():
    with pytest.raises(ValueError):
        resolve_guild_id(FakeInteraction(None, None))

def test_guild_without_permission_is_rejected():
    perms = type("P", (), {"manage_guild": False})()
    with pytest.raises(PermissionError):
        resolve_guild_id(FakeInteraction(FakeGuild(), perms))

def test_guild_with_permission_is_accepted():
    perms = type("P", (), {"manage_guild": True})()
    assert resolve_guild_id(FakeInteraction(FakeGuild(), perms)) == 42
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_setup_command.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'cogs'`

- [ ] **Step 3: Bot-Gerüst und Command implementieren**

`bot.py`: liest Config, baut `commands.Bot(command_prefix="!", intents=discord.Intents.default())` (Präfix wird nicht genutzt, Slash-Commands laufen über `self.tree`), registriert `cogs.Commands`, startet mit `bot.run(config.discord_token)`. In `setup_hook` wird `self.store.init_schema()` aufgerufen und `self.http = httpx.AsyncClient(timeout=10.0)` erzeugt; im `close()` wird beides geschlossen.

`cogs/commands.py`: `resolve_guild_id(interaction)` wirft `ValueError` ohne Guild und `PermissionError` ohne `manage_guild`. `/setup` ruft sie auf, speichert `store.set_channel(guild_id, channel.id)` und antwortet ephemer: `"Treffer landen ab jetzt in #kanal."`.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_setup_command.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add bot.py cogs tests/test_setup_command.py
git commit -m "feat: Bot-Geruest und /setup"
```

---

### Task 11: `/watch` mit Baseline

**Files:**
- Modify: `cogs/commands.py`, `tests/test_watch_command.py`

**Interfaces:**
- Consumes: `Criteria`, `Store`, `matches`, `fetch_servers`
- Produces: `build_criteria(**kwargs) -> Criteria`, `async def snap_to_current(store, filter_record, servers) -> int` (Anzahl markierter Server)

- [ ] **Step 1: Failing tests schreiben**

`tests/test_watch_command.py`:

```python
from decimal import Decimal
from filters import Criteria, CriteriaError
from hetzner.models import Server
from store import Store
import pytest
from cogs.commands import build_criteria, snap_to_current

def test_build_criteria_maps_options():
    crit = build_criteria(max_price=45, min_ram=64, disk_type=None, location=None,
                          cpu=None, min_disk=None, ecc=None, no_setup=None,
                          min_bandwidth=None, min_cores=None)
    assert crit.max_price == Decimal("45")
    assert crit.min_ram == 64
    assert crit.disk_type == "egal"

def test_build_criteria_without_any_criterion_raises():
    with pytest.raises(CriteriaError):
        build_criteria(max_price=None, min_ram=None, disk_type=None, location=None,
                       cpu=None, min_disk=None, ecc=None, no_setup=None,
                       min_bandwidth=None, min_cores=None)

def test_snap_marks_all_current_matches(tmp_path):
    store = Store(tmp_path / "t.sqlite3")
    store.init_schema()
    rec = store.save_filter(1, 2, "standard", Criteria(min_ram=1), mention=False)
    servers = [Server(id=10, cpu_name="X", sockets=1, ram_gb=64, ecc=True,
                      storage_total_gb=1000, nvme_gb=0, sata_gb=0, hdd_gb=0,
                      location="FSN", datacenter="FSN1-DC1", bandwidth_mbit=1000,
                      traffic="unlimited", price_month_eur=Decimal("45"),
                      price_hour_eur=Decimal("0.05"), setup_eur=Decimal("0"),
                      extra_ips=0, reduce_next_at=None)]
    assert snap_to_current(store, rec, servers) == 1
    assert store.is_seen(rec.id, 10) is True
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_watch_command.py -v`
Expected: FAIL, `ImportError: cannot import name 'build_criteria'`

- [ ] **Step 3: Implementieren**

`build_criteria` übersetzt die Command-Optionen (`None` → Default), baut `Criteria`, ruft `validate()` und gibt sie zurück.

`snap_to_current` lädt den aktuellen Snapshot (übergeben, damit testbar), filtert mit `matches`, ruft `store.mark_seen(rec.id, ids)` und gibt die Anzahl zurück.

`/watch`-Command: Optionen `name` (Default `standard`), `max_price`, `min_ram`, `min_cores`, `cpu`, `min_disk`, `disk_type` (Choices), `location` (Choices), `ecc` (Choices), `no_setup`, `min_bandwidth`, `mention`. Ablauf: `build_criteria` → `store.save_filter` → `snap_to_current` → epistemische Antwort: `"Filter 'standard' gespeichert. Aktuell passen 3 Server — ab jetzt melde ich neue."` Bei `CriteriaError` ephemer mit der Fehlermeldung.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_watch_command.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add cogs/commands.py tests/test_watch_command.py
git commit -m "feat: /watch mit Baseline"
```

---

### Task 12: `/filters`, `/unwatch`, `/pause`, `/resume`, `/status`

**Files:**
- Modify: `cogs/commands.py`, `tests/test_manage_commands.py`

**Interfaces:**
- Consumes: `Store`, `Criteria`
- Produces: `describe_filter(record: FilterRecord, match_count: int) -> str`, Command-Gruppe `Commands`

- [ ] **Step 1: Failing test schreiben**

`tests/test_manage_commands.py`:

```python
from decimal import Decimal
from filters import Criteria, FilterRecord
from cogs.commands import describe_filter

def test_describe_filter_lists_criteria():
    rec = FilterRecord(id=1, guild_id=1, user_id=2, name="standard",
                       criteria=Criteria(max_price=Decimal("45"), min_ram=64),
                       mention=True, active=True)
    text = describe_filter(rec, 3)
    assert "standard" in text
    assert "45" in text
    assert "64 GB" in text
    assert "3 passende Server" in text
    assert "Ping an" in text

def test_describe_filter_marks_paused():
    rec = FilterRecord(id=1, guild_id=1, user_id=2, name="x",
                       criteria=Criteria(min_ram=64), mention=False, active=False)
    assert "pausiert" in describe_filter(rec, 0)
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_manage_commands.py -v`
Expected: FAIL, `ImportError: cannot import name 'describe_filter'`

- [ ] **Step 3: Implementieren**

`describe_filter` baut eine Zeile: Name fett, Kriterien in Klartext (`"≤ 45 €/Monat"`, `"≥ 64 GB RAM"`, `"≥ 16 Kerne"`, `"CPU enthält 'ryzen'"`, `"≥ 4 TB (NVMe)"`, `"FSN"`, `"ECC"`, `"ohne Setup"`, `"≥ 1 Gbit/s"`), dann `"· N passende Server"` und `"· Ping an"`/`"· pausiert"`.

`/filters` zeigt alle eigenen Filter als ephemeren Text, Trefferzahl aus dem letzten Snapshot (im Bot zwischengespeichert, sonst 0).
`/unwatch name` löscht, bestätigt oder meldet „nicht gefunden".
`/pause`/`/resume` setzen `active`, bestätigen.
`/status` zeigt: letzter erfolgreicher Poll (Europe/Berlin), Anzahl Server im Snapshot, Anzahl aktiver Filter der Guild, nächster Preisfall (`min(reduce_next_at)`), letzter Fehler (falls vorhanden), Anzahl wartender Treffer.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_manage_commands.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add cogs/commands.py tests/test_manage_commands.py
git commit -m "feat: Verwaltungs- und Status-Commands"
```

---

### Task 13: Poll-Loop und Zustellung

**Files:**
- Modify: `bot.py`, `poller.py`, `tests/test_poller.py`

**Interfaces:**
- Consumes: `fetch_servers`, `find_candidates`, `build_embed`, `mention_prefix`, `Store`
- Produces: `class Poller` mit `__init__(bot, store, config)`, `async def run_once() -> PollReport`, `PollReport` (dataclass: `fetched: int`, `posted: int`, `queued: int`, `failed: bool`); `bot.poller`

- [ ] **Step 1: Failing tests schreiben**

`tests/test_poller.py` — ein Durchlauf mit Fakes, ohne Discord und ohne Netz:

```python
from decimal import Decimal
from unittest.mock import AsyncMock
import pytest
from filters import Criteria
from store import Store
from poller import Poller

class FakeChannel:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []
    async def send(self, content=None, embed=None):
        if self.fail:
            raise RuntimeError("keine Rechte")
        self.sent.append((content, embed))

class FakeBot:
    def __init__(self, channel):
        self.channel = channel
    def get_channel(self, cid):
        return self.channel

def make_server(id=10, price="45"):
    from hetzner.models import Server
    return Server(id=id, cpu_name="AMD Ryzen 9 5950X", sockets=1, ram_gb=64, ecc=True,
                  storage_total_gb=4096, nvme_gb=0, sata_gb=0, hdd_gb=8000,
                  location="FSN", datacenter="FSN1-DC14", bandwidth_mbit=1000,
                  traffic="unlimited", price_month_eur=Decimal(price),
                  price_hour_eur=Decimal("0.05"), setup_eur=Decimal("0"),
                  extra_ips=0, reduce_next_at=None)

@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "t.sqlite3")
    s.init_schema()
    yield s
    s.close()

@pytest.mark.asyncio
async def test_run_posts_and_marks_seen(store):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=True)
    channel = FakeChannel()
    poller = Poller(FakeBot(channel), store, fetch=lambda: [make_server()], max_posts=15)
    report = await poller.run_once()
    assert report.posted == 1
    assert channel.sent[0][0] == "<@2>"
    assert store.last_price(1, 10) == Decimal("45")

@pytest.mark.asyncio
async def test_second_run_posts_nothing(store):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    channel = FakeChannel()
    poller = Poller(FakeBot(channel), store, fetch=lambda: [make_server()], max_posts=15)
    await poller.run_once()
    report = await poller.run_once()
    assert report.posted == 0
    assert len(channel.sent) == 1

@pytest.mark.asyncio
async def test_failed_send_is_queued_not_recorded(store):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    poller = Poller(FakeBot(FakeChannel(fail=True)), store, fetch=lambda: [make_server()], max_posts=15)
    report = await poller.run_once()
    assert report.posted == 0
    assert report.queued == 1
    assert store.last_price(1, 10) is None
    assert len(store.queued()) == 1

@pytest.mark.asyncio
async def test_vanished_queued_server_is_dropped(store):
    store.set_channel(1, 99)
    store.save_filter(1, 2, "standard", Criteria(min_ram=64), mention=False)
    store.enqueue(1, 999, (1,))
    poller = Poller(FakeBot(FakeChannel()), store, fetch=lambda: [], max_posts=15)
    report = await poller.run_once()
    assert report.posted == 0
    assert store.queued() == []
```

- [ ] **Step 2: Test laufen lassen**

Run: `pytest tests/test_poller.py -v`
Expected: FAIL, `ImportError: cannot import name 'Poller'`

- [ ] **Step 3: `Poller` implementieren**

`Poller.__init__(bot, store, config=None, fetch=None, max_posts=None)`: `fetch` ist ein Callable ohne Argumente, das eine `list[Server]` liefert (Default: wrappt `fetch_servers` mit `bot.http`); `max_posts` Default `config.max_posts_per_run`.

`run_once`:

1. `servers = await self.fetch()`; bei `FetchError`: `PollReport(failed=True)` und Ausfallzähler erhöhen.
2. `by_id = {s.id: s for s in servers}`
3. Warteschlange: für jedes `QueuedItem` prüfen, ob `server_id` in `by_id`; wenn nicht → `dequeue` (still). Wenn ja und `last_price` existiert und `price >= last_price` → `dequeue`. Sonst Candidate bauen.
4. `find_candidates(servers, store.list_filters(), store.is_seen, store.last_price)`
5. Zusammenführen (Warteschlange zuerst), Duplikate pro `(guild_id, server_id)` entfernen.
6. Auf `max_posts` kürzen; Rest `enqueue`.
7. Pro Candidate: `channel = bot.get_channel(store.get_channel(guild_id))`. Fehlt Kanal oder `channel_id` → `bump_attempts`, bei `>= 3` `dequeue` + WARN, weiter.
8. `await channel.send(content=mention_prefix(user_ids) or None, embed=build_embed(...))`. Erfolg → `record_post`, für jede `filter_id` `mark_seen(filter_id, [server_id])`, `dequeue`. Fehler → `bump_attempts`, WARN, weiter.
9. Nach Erfolg: Ausfallzähler auf 0, ggf. Entwarnung posten. Nach 3 Fehlläufen in Folge einmalig `"Ich komme seit 30 Minuten nicht an die Daten."` posten (Flag gegen Wiederholung).

`bot.py`: `poller = Poller(self, self.store, self.config)` in `setup_hook`, `tasks.loop(minutes=config.poll_minutes)` startet `poller.run_once`.

- [ ] **Step 4: Tests laufen lassen**

Run: `pytest tests/test_poller.py -v`
Expected: 4 passed

- [ ] **Step 5: Alle Tests laufen lassen**

Run: `pytest -v`
Expected: alles grün

- [ ] **Step 6: Commit**

```bash
git add bot.py poller.py tests/test_poller.py
git commit -m "feat: Poll-Loop mit Warteschlange und Ausfallmeldung"
```

---

### Task 14: Docker, Healthcheck und README

**Files:**
- Create: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `healthcheck.py`, `README.md`
- Modify: `bot.py` (Erfolgszeitstempel schreiben)

**Interfaces:**
- Consumes: alles Vorherige
- Produces: lauffähiges Image, `python healthcheck.py` als Healthcheck

- [ ] **Step 1: Erfolgszeitstempel schreiben**

`bot.py` schreibt nach jedem erfolgreichen Poll `datetime.now(UTC).isoformat()` in `data/last_poll` (`config.database_path.parent / "last_poll"`), atomar über eine `.tmp`-Datei + `os.replace`.

- [ ] **Step 2: `healthcheck.py` schreiben**

Liest `LAST_POLL_FILE` (Env, Default `data/last_poll`). Fehlt die Datei oder ist der Inhalt älter als 30 Minuten → Exit-Code 1 mit Meldung auf stderr, sonst 0.

Prüfen: `python healthcheck.py; echo $LASTEXITCODE` gegen eine frische und eine alte Datei.

- [ ] **Step 3: `Dockerfile` und `.dockerignore` schreiben**

`FROM python:3.12-slim`, `WORKDIR /app`, `COPY requirements.txt`, `RUN pip install --no-cache-dir -r requirements.txt`, `COPY . .`, Non-root-User `bot` (uid 10001), `USER bot`, `CMD ["python", "bot.py"]`. `.dockerignore`: `.git`, `.venv`, `data`, `__pycache__`, `.env`, `tests`.

- [ ] **Step 4: `docker-compose.yml` schreiben**

```yaml
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "healthcheck.py"]
      interval: 5m
      timeout: 10s
      retries: 2
      start_period: 2m
```

- [ ] **Step 5: `README.md` schreiben**

Kurz und praktisch: was der Bot tut, Bot bei Discord anlegen (Message Content Intent nicht nötig, nur `applications.commands` + `bot`-Scope, Rechte: Nachrichten senden, Embeds einbetten, Erwähnungen), `.env` anlegen, `docker compose up -d --build`, `/setup` im Kanal, `/watch`-Beispiel, Logs ansehen, Daten zurücksetzen (`rm data/bot.sqlite3`).

- [ ] **Step 6: Build prüfen**

Run: `docker compose build`
Expected: Build erfolgreich. Ohne `DISCORD_TOKEN` startet der Container absichtlich mit `ConfigError` — das ist korrekt und wird im README erwähnt.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore healthcheck.py README.md bot.py
git commit -m "chore: Docker, Healthcheck und README"
```

---

## Self-Review

- **Spec-Abdeckung:** Datenquelle (Tasks 2, 3), Filter (5, 6), Kerne (4), Platten (6), Dedupe/Baseline (7, 8), Preisverfall (8, 9), Commands (10–12), 10-Minuten-Loop, 15er-Grenze, Warteschlange und Ausfallmeldung (13), Betrieb (14), Deutsch (durchgehend). Keine Lücke gefunden.
- **Typen konsistent:** `Criteria`-Felder, `FilterRecord`, `Store`-Methoden und `Candidate` werden in späteren Tasks mit denselben Namen benutzt.
- **Review Focus:** Server verschwindet → Task 13; fehlende Felder → Task 2; Preisgleichstand/Cent → Tasks 5, 6, 8; kaputter Kanal → Task 13; Doppel-Ping → Task 8.
