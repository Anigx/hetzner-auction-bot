# AGENTS.md

Kurzer Vertrag für Agenten. Das **Wissen** steht im Wiki: [`llm-wiki/`](llm-wiki/README.md).

## Was das ist

Ein Discord-Bot, der die Hetzner-Serverbörse beobachtet und passende Server in
einen Kanal postet. Python 3.12, `discord.py`, SQLite, Docker.
Details: [01 — Überblick](llm-wiki/01-ueberblick.md).

## Wo was steht

| Frage | Datei |
|---|---|
| Wie funktioniert es, welche Datei macht was? | [llm-wiki/02-architektur.md](llm-wiki/02-architektur.md) |
| Woher kommen die Server, welche Fallstricke? | [llm-wiki/03-datenquelle.md](llm-wiki/03-datenquelle.md) |
| Was bedeutet ein Filter genau? | [llm-wiki/04-filter.md](llm-wiki/04-filter.md) |
| Container, Volume, Healthcheck, Updates | [llm-wiki/05-betrieb.md](llm-wiki/05-betrieb.md) |
| Tests, Fixture, Release | [llm-wiki/06-entwicklung.md](llm-wiki/06-entwicklung.md) |
| Was ist offen? | [TASKS.md](TASKS.md) |
| Was ist passiert? | [CHANGELOG.md](CHANGELOG.md) |
| Warum ist es so gebaut? | [Design](docs/superpowers/specs/2026-10-29-hetzner-auktion-discord-bot-design.md) |

## Regeln

- Erst Design, dann Plan, dann Code. Verhalten ändern heißt: Design und Wiki
  nachziehen, nicht nur den Code.
- `TASKS.md` ist die Wahrheit über den Fortschritt, `CHANGELOG.md` über die
  Historie. Beides bei jeder Änderung pflegen.
- Vor „fertig" die Tests laufen lassen und die Ausgabe zeigen.
- Preise als `Decimal(str(...))`, Zeiten in UTC speichern und nur zur Anzeige
  nach `Europe/Berlin`.
- Keine Secrets im Repo. `DISCORD_TOKEN` nur in `.env`; `.env.example` pflegen.
- Keine stillen Fehler: Log mit Kontext oder Meldung im Discord.
- Hetzner nicht häufiger als nötig abfragen: im Betrieb 10 Minuten, beim
  Entwickeln gegen die Fixture, nicht live.

## Befehle

```bash
uv venv --python 3.12 .venv
uv pip install -r requirements.txt --python .venv/Scripts/python.exe
.venv/Scripts/python.exe -m pytest -q
docker compose pull && docker compose up -d
docker compose logs -f bot
```
