![Hetzner Auction Bot](docs/assets/banner.png)

[![CI](https://github.com/Anigx/hetzner-auction-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Anigx/hetzner-auction-bot/actions/workflows/ci.yml)

# Hetzner-Auktions-Bot für Discord

Beobachtet die [Hetzner-Serverbörse](https://www.hetzner.com/sb/) und postet neue
passende Server in einen Discord-Kanal. Jede Person legt per Slash-Command eigene
Filter an und entscheidet, ob sie bei Treffern getaggt werden will.

- Prüft alle 10 Minuten mit einem einzigen HTTP-Request pro Lauf
- Postet nur Server, die zu mindestens einem Filter passen
- Jeder Server erscheint einmal; fällt er im Preis, kommt eine zweite Meldung mit
  altem und neuem Preis
- Läuft als Docker-Container, Zustand in SQLite

## Bot bei Discord anlegen

1. Im [Discord Developer Portal](https://discord.com/developers/applications) eine
   Application anlegen und darin einen Bot.
2. Token kopieren.
3. Unter *OAuth2 → URL Generator* die Scopes `bot` **und** `applications.commands`
   wählen, Berechtigungen: *Kanäle ansehen*, *Nachrichten senden*,
   *Links einbetten*, *Nachrichtenverlauf lesen*.
4. Bot über die erzeugte URL auf den Server einladen.

> **Der Scope `bot` ist Pflicht.** Mit nur `applications.commands` werden die
> Slash-Commands installiert, der Bot taucht aber unter *Integrationen* statt unter
> *Mitglieder* auf, ist kein Servermitglied und kann keinen Kanal sehen. `/status`
> und das Log weisen darauf hin.

> **Gruppen-DMs gehen nicht.** Bots lassen sich nur auf Discord-Servern
> hinzufügen. Der „Gruppenchat" muss ein (privater) Server sein.

## Start

```bash
cp .env.example .env
# DISCORD_TOKEN in .env eintragen
docker compose pull
docker compose up -d
docker compose logs -f bot
```

Das Compose-File zieht `ghcr.io/anigx/hetzner-auction-bot:latest` — es wird nichts
lokal gebaut. Für reproduzierbare Deploys im Compose-File auf eine feste Version
pinnen (Zeile ist dort auskommentiert vorbereitet).

Ohne `DISCORD_TOKEN` bricht der Start mit einer klaren Meldung ab.

Die Daten liegen im benannten Volume `hetzner-auction-bot-data`. Ein
`mkdir`/`chown` auf dem Host ist nicht nötig — Docker übernimmt beim ersten Start
Besitzer und Rechte aus dem Image.

## Benutzung

```
/setup channel:#server-deals     # einmalig, braucht "Server verwalten"
/help                            # Befehle, Filter und Zustellung erklaert
/watch max_price:100 min_ram:64 min_cores:8 mention:true
/watch name:ryzen cpu:"Ryzen 9" min_disk:2 disk_type:nvme mention:true
/watch name:privat max_price:120 delivery:dm
/matches                         # was gerade passt, mit Direktlink
/filters
/pause name:standard
/resume name:standard
/unwatch name:standard
/status
```

Jeder Treffer verlinkt direkt auf den Server
(`hetzner.com/sb/?freetext=<ID>`), der Titel des Embeds ist klickbar.

Mit `delivery:dm` kommen die Treffer nur dir als Direktnachricht, nichts geht in
den Kanal. `delivery:kanal` (Standard) postet öffentlich, `mention:true` taggt dich
dabei.

Beim Anlegen eines Filters werden die aktuell passenden Server nur gezählt, nicht
gepostet — sonst würde der Kanal mit Altbestand geflutet.

Alle Optionen von `/watch`: `max_price` (€/Monat), `min_ram` (GB), `min_cores`,
`cpu` (Text im CPU-Namen), `min_disk` (TB), `disk_type` (`egal`/`nvme`/`sata`/`hdd`),
`location` (`FSN`/`NBG`/`HEL`), `ecc`, `no_setup`, `min_bandwidth` (Mbit/s),
`mention`.

Mindestens ein Kriterium muss gesetzt sein. Pro Person sind maximal 5 Filter
gleichzeitig aktiv (`MAX_FILTERS_PER_USER`); ein vorhandener Name lässt sich
jederzeit überschreiben.

## Betrieb

```bash
docker compose ps               # Healthcheck-Status
docker compose logs -f bot      # JSON-Zeilen
docker compose restart bot
docker compose pull && docker compose up -d   # auf eine neue Version aktualisieren
docker compose down -v          # Container und Daten-Volume entfernen
```

Der Container heisst `hetzner-auction-bot`, die Daten liegen im Volume
`hetzner-auction-bot-data`, das Image kommt aus der GitHub Container Registry
(`ghcr.io/anigx/hetzner-auction-bot`). Lokal bauen nur, wenn du am Code arbeitest:
`docker compose build` funktioniert erst, wenn im Compose-File wieder ein
`build:`-Block steht.

Sicherung des Volumes:

```bash
docker run --rm -v hetzner-auction-bot-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/bot-data.tgz -C /data .
```

Der Healthcheck prüft `data/last_poll`: Ist der letzte erfolgreiche Abruf älter als
30 Minuten, gilt der Container als unhealthy. Zusätzlich meldet sich der Bot selbst
im Kanal, wenn er dreimal hintereinander keine Daten bekommt.

Optionale Umgebungsvariablen: `AUCTION_URL` (andere Datenquelle),
`LAST_POLL_FILE` und `MAX_POLL_AGE_MINUTES` (Healthcheck), `POLL_MINUTES`,
`MAX_POSTS_PER_RUN`, `MAX_FILTERS_PER_USER` (Default 5), `GUILD_ID` (Bot nur auf
einem Server), `VAT_PERCENT` (Bruttopreis-Anzeige, z. B. 19), `LOG_LEVEL`.
Die Logs sind JSON-Zeilen, eine pro Ereignis.

## Entwicklung

```bash
uv venv --python 3.12 .venv
uv pip install -e ".[dev]" --python .venv/Scripts/python.exe
.venv/Scripts/python.exe -m pytest -q
```

Tests sprechen nie mit dem Netz: Sie nutzen den Snapshot in
`tests/fixtures/auction_snapshot.json` und `httpx.MockTransport`.

Die Kernzahlen der CPUs stehen in `src/hetzner_bot/auction/cpus.py`. Kommt in der
Auktion ein neues
Modell dazu, schlägt `test_every_cpu_in_fixture_is_known` fehl — dann Tabelle
ergänzen und den Snapshot neu ziehen.

Das Banner entsteht aus `tools/make_banner.py` (Pillow steckt in den Dev-Extras):

```bash
.venv/Scripts/python.exe tools/make_banner.py
```

## Dokumentation

- Wiki: [`llm-wiki/`](llm-wiki/README.md) — Überblick, Architektur, Datenquelle,
  Filter, Betrieb, Entwicklung
- Design: `docs/superpowers/specs/2026-10-29-hetzner-auktion-discord-bot-design.md`
- Plan: `docs/superpowers/plans/2026-10-29-hetzner-auktion-discord-bot.md`
- Aufgaben: `TASKS.md` · Historie: `CHANGELOG.md`
