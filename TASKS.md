# TASKS

Arbeitsliste. Oben steht, was als Nächstes dran ist. Abgehakte Aufgaben bleiben
stehen, bis die Phase abgeschlossen ist.

Status: **Planung abgeschlossen, Freigabe des Designs offen.**

## Blockiert durch

- [x] Freigabe des Design-Dokuments durch den Projektinhaber (2026-10-29)

## Phase 0 — Gerüst

- [ ] Git-Repository initialisieren, `.gitignore` (`.env`, `data/`, `.venv`, `__pycache__`)
- [ ] `requirements.txt` mit festen Versionen (`discord.py`, `httpx`, `pytest`, `python-dotenv`)
- [ ] `config.py`: Env laden, fehlenden Token klar melden
- [ ] Projektstruktur anlegen (`hetzner/`, `tests/`)

## Phase 1 — Datenquelle

- [ ] Fixture-Snapshot der echten `live_data_sb.json` in `tests/fixtures/` ablegen
- [ ] `hetzner/models.py`: Dataclasses für Server, Hardware, Preise
- [ ] `hetzner/client.py`: Fetch mit Timeout, 3 Versuche, Backoff
- [ ] Parser-Tests gegen Fixture, inkl. fehlender Felder
- [ ] Prüfen: filtert `?freetext=<ID>` die Auktionsseite vor?

## Phase 2 — Filter und Matching

- [ ] Kriterien-Dataclass mit Validierung (mindestens ein Kriterium, Preis > 0, `mention` zählt nicht)
- [ ] `matches()` pro Kriterium und in Kombination, mit Unit-Tests
- [ ] CPU-Tabelle (24 Auktionsmodelle → Kerne) inkl. Wächter-Test auf unbekannte CPUs
- [ ] Platten-Typ-Logik (nvme/sata/hdd aus `Details.Storage.Details`, Semantik siehe Design)
- [ ] Standort-Mapping (FSN/NBG/HEL aus `Datacenter.Name`)

## Phase 3 — Speicher

- [ ] `store.py`: SQLite-Schema `guilds`, `filters`, `seen`, `posts`, `queue` anlegen
- [ ] CRUD für Filter (anlegen, überschreiben, löschen, pausieren)
- [ ] Dedupe-Abfragen pro Guild: unbekannt / Preis gefallen / unverändert
- [ ] Baseline beim Filter-Anlegen in `seen` schreiben, ohne `posts` anzufassen
- [ ] Warteschlange für Treffer über der 15er-Grenze und für Fehlversuche
- [ ] Tests gegen temporäre DB

## Phase 4 — Discord

- [ ] Bot-Grundgerüst, Intents (nur `guilds`), Command-Sync
- [ ] `/setup` mit Rechteprüfung
- [ ] `/watch` mit allen Filteroptionen, ephemeres Feedback
- [ ] Erstlauf-Verhalten: bestehende Treffer als gesehen markieren, nicht posten
- [ ] `/filters`, `/unwatch`, `/pause`, `/resume`, `/status`
- [ ] Poll-Loop alle 10 Minuten, max. 15 Posts pro Lauf
- [ ] Ausfall-Meldung im Kanal nach 3 fehlgeschlagenen Polls, Entwarnung danach
- [ ] Embed-Bau inkl. Preisfall-Darstellung
- [ ] Ping-Logik: Vereinigung aller passenden Filter mit `mention`

## Phase 5 — Betrieb

- [ ] `Dockerfile` (non-root, python:3.12-slim)
- [ ] `docker-compose.yml` mit Volume, `restart: unless-stopped`, `.env`
- [ ] Healthcheck-Signal (letzter erfolgreicher Poll)
- [ ] Logging als JSON-Zeilen nach stdout
- [ ] `README.md` mit Setup-Anleitung für den VPS
- [ ] Trockenlauf auf einem Testserver mit echtem Token

## Offene Punkte

- [ ] Entscheiden, ob `Timer.ReduceNextTimestamp` im Embed erscheint
- [ ] Grenze für Filter pro Person festlegen (Vorschlag: 5)
- [ ] Verhalten bei gelöschtem Kanal festlegen (Vorschlag: WARN + `/setup` verlangen)

## Ideen für später

- `/preise` — Preishistorie eines Servers als Sparkline
- Sammel-Nachricht statt Einzelposts, wenn ein Filter sehr breit ist
- Zweiter Kanal nur für Preisrückgänge
