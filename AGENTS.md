# AGENTS.md — Projekt-Wiki

Einstiegspunkt für Menschen und LLM-Agenten, die an diesem Projekt arbeiten.
Kurz, aktuell, ohne Ballast. Details stehen in den verlinkten Dateien.

## Was das ist

Ein Discord-Bot, der die Hetzner-Serverbörse beobachtet und neue passende
Server in einen gemeinsamen Discord-Kanal postet. Jede Person legt per
Slash-Command eigene Filter an und entscheidet, ob sie bei Treffern getaggt
werden will.

## Stand

Umgesetzt und getestet (74 Tests). Läuft lokal, Deployment auf einem VPS per
Docker Compose steht noch aus.
Siehe [Design](docs/superpowers/specs/2026-10-29-hetzner-auktion-discord-bot-design.md),
[Plan](docs/superpowers/plans/2026-10-29-hetzner-auktion-discord-bot.md)
und [TASKS.md](TASKS.md).

## Wiki

| Datei | Inhalt |
|---|---|
| [AGENTS.md](AGENTS.md) | Einstieg, Konventionen, Regeln für Agenten |
| [TASKS.md](TASKS.md) | Arbeitsliste, Phasen, offene Punkte |
| [CHANGELOG.md](CHANGELOG.md) | Was sich wann geändert hat |
| [docs/superpowers/specs/](docs/superpowers/specs/) | Design-Dokumente |
| [docs/superpowers/plans/](docs/superpowers/plans/) | Umsetzungspläne |

## Technik

- Python 3.12, `discord.py` 2.x, `httpx`, SQLite
- Betrieb: Docker Compose auf einem VPS
- Datenquelle: `https://www.hetzner.com/_resources/app/data/app/live_data_sb.json`
  (öffentlich, kein Key, ein GET alle 10 Minuten)
- Bot-Sprache: Deutsch

## Geplante Struktur

```
bot.py              Start, Intents, Command-Registrierung
hetzner/client.py   Fetch + Parsing in Dataclasses
filters.py          Kriterien, Matching, Validierung
store.py            SQLite-Zugriff
notify.py           Embed-Bau, Pings, Posten
config.py           Token, Intervall, Pfade aus Env
tests/              Unit-Tests, Fixture der echten JSON-Antwort
data/               SQLite-Volume (nicht im Repo)
```

## Konventionen

- Deutsch in UI, Commits und Doku. Code-Bezeichner englisch.
- Keine Secrets im Repo. `DISCORD_TOKEN` nur über `.env`, `.env` in
  `.gitignore`, `.env.example` mit Platzhaltern.
- Zeitangaben in UTC speichern, in Europe/Berlin anzeigen.
- Preise in EUR als `Decimal`, nicht `float` — Cent-Differenzen entscheiden.
- Jede Regel in `filters.py` bekommt einen Test. Fixture ist ein echter
  JSON-Snapshot der Auktionsdatei.
- Keine stillen Fehler: entweder Log mit Kontext oder eine Meldung im Discord.

## Regeln für Agenten

- Erst Design, dann Plan, dann Code. Änderungen am Verhalten zuerst im
  Design-Dokument nachziehen.
- `TASKS.md` ist die Wahrheit über den Fortschritt: Aufgabe abhaken, neue
  Erkenntnisse als offenen Punkt eintragen.
- Jede abgeschlossene Änderung mit Datum in `CHANGELOG.md`.
- Vor „fertig" die Tests laufen lassen und die Ausgabe zeigen.
- Hetzner nicht häufiger als nötig abfragen. Im Betrieb 10 Minuten, beim
  Entwickeln maximal ein Request pro Minute und nur gegen einen
  Fixture-Snapshot, nicht live im Test.

## Befehle (nach dem Gerüst)

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python bot.py
pytest
docker compose pull && docker compose up -d
docker compose logs -f bot
```

## Offene Entscheidungen

Siehe „Offen / beim Bauen zu klären" im Design-Dokument.
