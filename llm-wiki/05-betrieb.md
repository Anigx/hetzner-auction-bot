# 05 — Betrieb

## Das Compose-File

```yaml
services:
  bot:
    image: ghcr.io/anigx/hetzner-auction-bot:latest
    container_name: hetzner-auction-bot
    env_file: .env
    volumes:
      - bot-data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "healthcheck.py"]
      interval: 5m
      timeout: 10s
      retries: 2
      start_period: 2m

volumes:
  bot-data:
    name: hetzner-auction-bot-data
```

Es wird **nichts lokal gebaut**. Das Image kommt aus der GitHub Container
Registry; `latest` zeigt auf die letzte Release-Version. Für reproduzierbare
Deploys im File auf eine feste Version pinnen (Zeile ist auskommentiert
vorbereitet) und beim Update bewusst ändern.

## Volume statt Host-Bind

Die Datenbank und der Heartbeat liegen im benannten Volume
`hetzner-auction-bot-data`:

- Docker übernimmt beim ersten Start Besitzer und Rechte aus dem Image
  (`/app/data` gehört `uid 10001`) — kein `mkdir`/`chown` auf dem Host nötig.
- Ein Host-Bind wurde bewusst nicht verwendet: Bei einem fehlenden Verzeichnis
  legt Docker es als `root` an, und der non-root-Container kann die SQLite-Datei
  nicht öffnen.
- Preis: Die Datei ist nicht mehr direkt im Projektordner sichtbar. Dafür gibt es
  `docker compose down -v` zum Zurücksetzen und den Backup-Befehl unten.

## Start und Update

```bash
cp .env.example .env          # DISCORD_TOKEN
docker compose pull
docker compose up -d
docker compose logs -f bot

# Update auf eine neue Version
docker compose pull && docker compose up -d
```

## Umgebungsvariablen

| Variable | Default | Zweck |
|---|---|---|
| `DISCORD_TOKEN` | — | Pflicht, sonst Abbruch mit klarer Meldung |
| `DATABASE_PATH` | `data/bot.sqlite3` | Pfad in der DB (im Volume) |
| `POLL_MINUTES` | `10` | Prüfintervall |
| `MAX_POSTS_PER_RUN` | `15` | Obergrenze pro Lauf |
| `MAX_FILTERS_PER_USER` | `5` | Filter pro Person und Server |
| `LOG_LEVEL` | `INFO` | Log-Schwelle |
| `AUCTION_URL` | Hetzner-URL | andere Datenquelle (Tests, Umzug) |
| `LAST_POLL_FILE` | `data/last_poll` | Heartbeat für den Healthcheck |
| `MAX_POLL_AGE_MINUTES` | `30` | ab wann der Healthcheck rot wird |

## Healthcheck

`healthcheck.py` liest `data/last_poll`, das der Poller nach jedem erfolgreichen
Lauf schreibt (atomar über `.tmp` + `os.replace`). Fehlt die Datei oder ist sie
älter als 30 Minuten, endet der Check mit Exit-Code 1.

Der Healthcheck ist nur ein Signal. Die Meldung an Menschen macht der Bot selbst:
nach drei Fehlläufen in Folge schreibt er einmal pro Guild „Ich komme seit N
Minuten nicht an die Daten" und beim nächsten Erfolg eine Entwarnung.

## Wenn etwas klemmt

| Symptom | Ursache | Prüfen |
|---|---|---|
| Container startet im Loop | Token fehlt/ungültig | `docker compose logs bot` |
| „unable to open database file" | Volume-Rechte | `docker volume inspect hetzner-auction-bot-data` |
| Keine Posts | kein `/setup`, Filter pausiert, keine Treffer | `/status` im Discord |
| Posts fehlen seit Stunden | Datenquelle oder Kanalrechte | `/status`, Logs, Healthcheck |
| „Treffer verworfen" | 3 Fehlversuche | Kanalrechte, dann `/status` |

Der Bot zählt Fehlversuche pro Treffer. Nach drei Versuchen wird der Treffer
verworfen und als gesehen markiert, damit ein kaputter Kanal nicht in jeder Runde
dieselben Server erneut versucht.

## Backup und Reset

```bash
# Sicherung
docker run --rm -v hetzner-auction-bot-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/bot-data.tgz -C /data .

# Alles zurücksetzen (Filter, Verlauf, Baseline)
docker compose down -v
```

## Logs

Eine JSON-Zeile pro Ereignis mit `time` (UTC), `level`, `logger`, `msg` und bei
Fehlern `exception`. Gebaut mit `json.dumps`, deshalb brechen auch
Anführungszeichen oder Zeilenumbrüche im Text die Zeile nicht.

---

Zurück: [04 — Filter](04-filter.md) · Weiter: [06 — Entwicklung](06-entwicklung.md)
