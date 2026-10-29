# TASKS

Arbeitsliste. Oben steht, was als Nächstes dran ist.

Status: **Code fertig, 74 Tests grün. Deployment auf dem VPS offen.**

## Als Nächstes

- [ ] `docker compose up -d --build` auf dem VPS, `data/` vorher anlegen und chownen
- [ ] Bot einladen, `/setup` und `/watch` im echten Kanal testen
- [ ] Nach 24 Stunden prüfen: Healthcheck, Logs, keine Doppel-Posts

## Phase 0 — Gerüst

- [x] Git-Repository initialisieren, `.gitignore`
- [x] `requirements.txt` mit festen Versionen
- [x] `config.py`: Env laden, fehlenden Token klar melden
- [x] Projektstruktur anlegen (`hetzner/`, `tests/`)

## Phase 1 — Datenquelle

- [x] Fixture-Snapshot der echten `live_data_sb.json` in `tests/fixtures/`
- [x] `hetzner/models.py`: Dataclasses für Server, Hardware, Preise
- [x] `hetzner/client.py`: Fetch mit Timeout, 3 Versuche, Backoff
- [x] Parser-Tests gegen Fixture, inkl. fehlender Felder
- [x] `?freetext=<ID>` geprüft: filtert nicht vor, Embed nutzt den generischen Link

## Phase 2 — Filter und Matching

- [x] Kriterien-Dataclass mit Validierung
- [x] `matches()` pro Kriterium und in Kombination, mit Unit-Tests
- [x] CPU-Tabelle (24 Auktionsmodelle → Kerne) inkl. Wächter-Test
- [x] Platten-Typ-Logik nach der Semantik aus dem Design
- [x] Standort-Mapping (FSN/NBG/HEL aus `Datacenter.Name`)

## Phase 3 — Speicher

- [x] SQLite-Schema `guilds`, `filters`, `seen`, `posts`, `baselines`, `queue`
- [x] CRUD für Filter (anlegen, überschreiben, löschen, pausieren)
- [x] Dedupe-Abfragen pro Guild
- [x] Baseline beim Filter-Anlegen in `seen` + `baselines`, ohne `posts` anzufassen
- [x] Warteschlange für Treffer über der 15er-Grenze und für Fehlversuche
- [x] Tests gegen temporäre DB

## Phase 4 — Discord

- [x] Bot-Grundgerüst, Command-Sync
- [x] `/setup` mit Rechteprüfung
- [x] `/watch` mit allen Filteroptionen, ephemeres Feedback
- [x] Erstlauf-Verhalten: bestehende Treffer als gesehen markieren, nicht posten
- [x] `/filters`, `/unwatch`, `/pause`, `/resume`, `/status`
- [x] Poll-Loop alle 10 Minuten, max. 15 Posts pro Lauf
- [x] Ausfall-Meldung im Kanal nach 3 fehlgeschlagenen Polls, Entwarnung danach
- [x] Embed-Bau inkl. Preisfall-Darstellung
- [x] Ping-Logik: Vereinigung aller passenden Filter mit `mention`

## Phase 5 — Betrieb

- [x] `Dockerfile` (non-root, python:3.12-slim)
- [x] `docker-compose.yml` mit Volume, `restart: unless-stopped`, `.env`
- [x] Healthcheck über `data/last_poll`
- [x] Logging nach stdout
- [x] `README.md` mit Setup-Anleitung
- [ ] Trockenlauf auf einem Testserver mit echtem Token
- [ ] `docker compose build` auf dem VPS verifizieren (lokal kein Docker)

## Offene Punkte

- [ ] Grenze für Filter pro Person festlegen (Vorschlag: 5) — aktuell unbegrenzt
- [ ] Entscheiden, ob `Timer.ReduceNextTimestamp` zusätzlich im Embed erscheint
- [ ] Log-Ausgabe als echtes JSON (aktuell handgebaut, bricht bei Anführungszeichen)
- [ ] `seen`/`posts` irgendwann aufräumen (bei ~100 Servern jahrelang unkritisch)

## Ideen für später

- `/preise` — Preishistorie eines Servers als Sparkline
- Sammel-Nachricht statt Einzelposts, wenn ein Filter sehr breit ist
- Zweiter Kanal nur für Preisrückgänge
