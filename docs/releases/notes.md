![Hetzner Auction Bot](https://raw.githubusercontent.com/Anigx/hetzner-auction-bot/main/docs/assets/banner.png)

# Hetzner Auction Bot __TAG__

Beobachtet die [Hetzner-Serverbörse](https://www.hetzner.com/sb/) und postet neue
passende Server in einen Discord-Kanal. Jede Person legt per Slash-Command eigene
Filter an und entscheidet, ob sie bei Treffern getaggt werden will.

## Container-Image

```bash
docker pull __IMAGE__:__VERSION__
```

Verfügbare Tags: `__VERSION__`, `latest`. Gebaut für `linux/amd64`, läuft als
non-root (uid 10001) und bringt einen Healthcheck mit.

```yaml
services:
  bot:
    image: __IMAGE__:__VERSION__
    env_file: .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

## Was drin ist

- Prüft alle 10 Minuten, ein HTTP-Request pro Lauf gegen die Auktionsdaten
- Filter pro Person: Preis, RAM, Kerne, CPU-Name, Platten (Größe und Typ),
  Standort, ECC, ohne Setup, Anbindung, optionaler Ping
- Jeder Server erscheint einmal; fällt er im Preis, kommt eine zweite Meldung mit
  altem und neuem Preis — auch für Server, die beim Anlegen des Filters schon da
  waren
- Baseline beim Filter-Anlegen: der Kanal wird nicht mit Altbestand geflutet
- Warteschlange für Nachzügler, Ausfallmeldung im Kanal nach drei Fehlläufen
- Zustand in SQLite, Neustart verliert nichts

## Schnellstart

```bash
cp .env.example .env            # DISCORD_TOKEN eintragen
mkdir -p data && sudo chown 10001:10001 data
docker compose up -d
```

Im Discord dann `/setup channel:#server-deals` und
`/watch max_price:50 min_ram:64 min_cores:16 mention:true`.

## Qualität

74 Tests grün in CI, keine Netzwerkzugriffe in den Tests (Fixture-Snapshot plus
`httpx.MockTransport`).

**Changelog:** [CHANGELOG.md](https://github.com/Anigx/hetzner-auction-bot/blob/main/CHANGELOG.md) ·
**Lizenz:** MIT
