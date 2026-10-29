# Hetzner-Auktions-Bot für Discord — Design

Datum: 2026-10-29
Status: freigegeben am 2026-10-29

## Warum

Gute Server aus der Hetzner-Serverbörse sind schnell weg. Wer nicht dauernd die
Seite neu lädt, verpasst sie. Der Bot beobachtet die Auktion im Hintergrund und
postet nur die Server, die zu einem gespeicherten Filter passen, in den
gemeinsamen Discord-Kanal — auf Wunsch mit Ping.

## Ziele

- Ein Discord-Bot, der dauerhaft auf einem VPS im Docker-Container läuft.
- Jede Person im Kanal legt per Slash-Command eigene Filter an.
- Der Bot prüft alle 10 Minuten die Auktion und postet Treffer in **einen**
  festgelegten Kanal.
- Gepostet wird nur, was mindestens einen Filter erfüllt, und jeder Server nur
  einmal.
- Fällt ein bereits geposteter Server im Preis, wird er erneut gepostet, mit
  altem und neuem Preis.
- Wer den Ping aktiviert hat, wird bei passenden Treffern getaggt.
- Alles auf Deutsch.

## Nicht-Ziele

- Keine automatische Bestellung, kein Klick-Bot.
- Nur die Serverbörse (Auktion), keine Cloud-Server, keine Dedicated-Neubestellung.
- Keine DMs, keine Web-Oberfläche, keine Statistik-Dashboards.
- Keine Preisprognose, kein Machine Learning.

## Anti-Ziele (das wäre ein Fehlschlag, auch wenn es technisch läuft)

- Doppelte Posts oder Spam, der den Kanal unlesbar macht.
- Treffer, die den Filter nicht erfüllen (Fehlalarm) — Vertrauen ist weg.
- Bot stirbt still und niemand merkt es.
- Einrichten neuer Filter dauert länger als das manuelle Nachschauen.

## Randbedingungen

- **Plattform:** Discord erlaubt Bots nicht in echten Gruppen-DMs. Der
  „Gruppenchat" muss ein (privater) Discord-Server mit einem Kanal sein.
- **Datenquelle:** `https://www.hetzner.com/_resources/app/data/app/live_data_sb.json`
  — die Datei, die die Auktionsseite selbst lädt. Kein Login, kein API-Key,
  kein Scraping von HTML. Ein GET pro Intervall, das ist unauffällig.
- **Bestell-Link:** Es gibt keinen Deep-Link pro Server. Der Bestell-Button der
  Seite schickt ein POST-Formular an `robot.hetzner.com/order/marketConfirm`;
  ein GET darauf leitet nur auf die Auktionsseite um. Der Embed zeigt deshalb
  die Server-ID gut sichtbar plus Link auf die Auktionsseite.
- **Technik:** Python 3.12, `discord.py` 2.x, `httpx`, SQLite. Deployment per
  Docker Compose auf einem VPS.

## Datenquelle im Detail

Antwort ist ein JSON-Objekt mit `server` (Liste), `filter` (Filter-Metadaten der
Seite) und `serverCount`. Rund 100 Server, ~105 KB.

Relevante Felder pro Server:

| Pfad | Bedeutung |
|---|---|
| `Id` | Server-ID, stabil, Grundlage für Dedupe |
| `Hardware.CPU.Name` / `.CoreCount` | CPU-Name und Kerne |
| `Hardware.RAM.Size` (GB), `.ecc` | RAM und ECC |
| `Hardware.Storage.Size` (GB), `.Amount`, `.Details.nvme/sata/hdd` | Plattensumme und Typen |
| `Details.Datacenter.Name` | z. B. `FSN1-DC14`, Standortpräfix FSN/NBG/HEL |
| `Details.Bandwidth` | Anbindung in Mbit/s |
| `Details.Traffic` | z. B. `unlimited` |
| `Details.Specials` | z. B. `IPv4`, `iNIC` |
| `Prices.monthly.EUR`, `.hourly.EUR`, `.setup.EUR` | Preise |
| `IPPrices` | Zusatz-IPs |
| `Timer.ReduceNextTimestamp` | Zeitpunkt des nächsten Preisfalls |

## Filter

Ein Filter gehört immer einer Person in einem Server (Guild) und hat einen
Namen (Default: `standard`). Alle Kriterien sind optional, aber mindestens
eines muss gesetzt sein.

| Kriterium | Typ | Bedeutung |
|---|---|---|
| `max_price` | Zahl (EUR/Monat) | Preis monatlich ≤ X |
| `min_ram` | Zahl (GB) | RAM ≥ X |
| `min_cores` | Zahl | Kerne ≥ X, aus CPU-Tabelle (siehe unten) |
| `cpu_contains` | Text | CPU-Name enthält (z. B. „Ryzen") |
| `min_disk` | Zahl (TB) | Nutzbare Plattensumme ≥ X (siehe unten) |
| `disk_type` | Auswahl | `nvme`, `sata`, `hdd`, `egal` |
| `location` | Auswahl | `FSN`, `NBG`, `HEL`, `egal` |
| `ecc` | Auswahl | `ja`, `egal` |
| `no_setup` | Ja/Nein | nur ohne Setup-Gebühr |
| `min_bandwidth` | Zahl (Mbit/s) | Anbindung ≥ X |
| `mention` | Ja/Nein | bei Treffer taggen (nur Kanal-Zustellung) |
| `delivery` | `kanal` (Default) / `dm` | wohin der Treffer geht |

Filter werden als JSON in SQLite gespeichert; die Kriterien bleiben erweiterbar,
ohne Migration. `mention` ist **kein** Kriterium, sondern eine Einstellung am
Filter — ein Filter nur mit `mention: ja` wird abgelehnt.

**Kern-Semantik.** `Hardware.CPU.CoreCount` ist die Anzahl der Sockel (bei allen
Servern `1`), nicht die Kerne. Deshalb hält der Bot eine kleine Tabelle
CPU-Name → physische Kerne für die Auktions-CPUs (aktuell 24 Modelle, z. B.
`AMD Ryzen 9 5950X → 16`, `Intel Xeon Gold 5412U → 24`). Unbekannte CPUs werden
im Log gemeldet und in `/status` als Warnung angezeigt; ein `min_cores`-Filter
greift bei ihnen nicht. Die Tabelle ist eine Python-Datei mit Tests, kein
Netzwerkabruf.

**Platten-Semantik.** `Hardware.Storage.Size` ist die nutzbare Gesamtkapazität
(2×4 TB im RAID → 4096 GB), während `Details.Storage.Details.nvme/sata/hdd` die
Rohgrößen je Typ enthalten. Deshalb:

- `disk_type: egal` → `min_disk` prüft die nutzbare Summe (`Size`).
- `disk_type: nvme|sata|hdd` → mindestens eine Platte dieses Typs **und**
  `min_disk` prüft die Rohsumme dieses Typs.
- Gemischte Server (2×HDD + 2×NVMe) erfüllen `disk_type: hdd` und
  `disk_type: nvme` beide.
- TB-Grenzen werden nicht gerundet: 1966 GB sind 1,92 TB und fallen bei
  `min_disk: 2` raus. Kein Aufrunden, sonst entstehen Fehltreffer.

## Verhalten

### Polling

`discord.ext.tasks.loop(minutes=10)` holt die JSON-Datei, parst sie in
Dataclasses und rechnet einmal pro Lauf alle Filter gegen alle Server. HTTP
mit Timeout (10 s) und 3 Versuchen mit exponentiellem Backoff. Schlägt alles
fehl, wird nichts gepostet; der Fehler landet im Log und in `/status`.

### Matching und Posten

1. Für jeden Server die Menge der passenden Filter ermitteln.
2. Server mit leerer Menge überspringen.
3. Dedupe **pro Guild**: Wurde die Server-ID in diesem Server schon gepostet?
   - Nein → posten.
   - Ja, aber aktueller Monatspreis liegt unter dem zuletzt geposteten →
     erneut posten, mit altem Preis durchgestrichen.
   - Ja, gleicher oder höherer Preis → nichts.
4. Ein Server wird **einmal** gepostet, auch wenn fünf Filter passen. Getaggt
   werden alle Personen, deren Filter gepasst hat und die `mention` aktiv haben
   — auch die, deren Filter erst durch den Preisfall wieder greift.
5. Pro Lauf höchstens 15 Posts. Alles darüber wandert in eine Warteschlange in
   der DB und wird im nächsten Lauf nachgeholt.
6. Ein Server zählt erst als gepostet, wenn Discord den Post bestätigt hat. Ein
   fehlgeschlagener Post bleibt in der Warteschlange und wird beim nächsten Lauf
   erneut versucht; nach drei Fehlversuchen wird er mit WARN verworfen, damit
   ein kaputter Kanal nicht ewig blockiert.
7. Der Vergleichspreis ist immer der Preis, der zuletzt **erfolgreich im Kanal
   stand**. Ein Server, der beim ersten Mal an der 15er-Grenze scheiterte und
   inzwischen günstiger wurde, erscheint als normaler neuer Treffer ohne
   „vorher"-Zeile — es gab ja nie einen alten Preis zu sehen.

### Erster Lauf nach Filtererstellung

Beim Anlegen eines Filters werden die aktuell passenden Server **pro Filter** als
gesehen markiert (`seen`), aber **nicht** in den Kanal gepostet. Stattdessen
antwortet der Bot nur der Person (ephemer): „Aktuell passen 3 Server — ab jetzt
melde ich neue." Sonst würde jeder neue Filter den Kanal mit Altbestand fluten.

Diese Markierung liegt getrennt von `posts`, damit sie (a) keinen erfundenen
„vorher"-Preis erzeugt und (b) Treffer anderer Personen nicht unterdrückt. Fällt
ein so markierter Server später im Preis und passt weiterhin zum Filter, wird er
als normaler neuer Treffer gepostet.

### Filter ändern

`/watch` mit einem bereits vorhandenen Namen **ersetzt** den Filter komplett,
statt Felder zu mischen — sonst lässt sich ein Kriterium nie wieder entfernen.
Nach dem Ersetzen wird neu baselined (siehe oben), damit die geänderten Kriterien
keinen Schwung Altbestand in den Kanal spülen.

### Preisverfall

Jeder Preisrückgang zählt, auch ein Cent — Hetzner senkt die Auktion
schrittweise, und genau diese Schritte sind die Deals. Gespeichert wird der
zuletzt gepostete Preis pro Server-ID.

### Embed

- Titel: CPU-Name + Kurzspec (`2x 4 TB`, `32 GB`)
- Felder: Kerne, RAM (+ECC), Platten (Anzahl/Typ), Standort/Rechenzentrum,
  Anbindung, Traffic, Preis monatlich, Preis stündlich, Setup, Server-ID
- Bei Preisfall: „vorher 45 € → jetzt 39 €"
- Fußzeile: „Hetzner Serverbörse · ID 3101875"
- Link: `https://www.hetzner.com/sb/?freetext=<ID>` — die Auktionsseite filtert
  per URL-Parameter auf genau diesen Server (im Browser geprüft: „1 results").

## Slash-Commands

| Command | Wer | Zweck |
|---|---|---|
| `/setup channel:<#kanal>` | Manage Server | Kanal festlegen, in dem gepostet wird |
| `/help` | alle | Befehle, Filter und Zustellarten erklären |
| `/matches` | alle | was gerade zu den eigenen Filtern passt, mit Direktlink |
| `/watch ...` | alle | Filter anlegen/überschreiben (Optionen = Filterfelder + `name`) |
| `/filters` | alle | eigene Filter auflisten, mit Trefferzahl von jetzt |
| `/unwatch name:<name>` | alle | Filter löschen |
| `/pause name:<name>` | alle | Filter deaktivieren, ohne ihn zu löschen |
| `/resume name:<name>` | alle | wieder aktivieren |
| `/status` | alle | letzter Lauf, Anzahl Server, nächster Preisfall, letzter Fehler |

Ohne `/setup` postet der Bot nichts, sondern weist im Command darauf hin.
Fehlerhafte Eingaben (kein Kriterium, Preis 0, unbekannter Standort) werden mit
einer klaren Meldung abgelehnt, ephemer.

## Datenmodell (SQLite)

```
guilds(guild_id PK, channel_id, updated_at)
filters(id PK, guild_id, user_id, name, criteria_json, mention, active,
        created_at, UNIQUE(guild_id, user_id, name))
seen(filter_id, server_id, PRIMARY KEY(filter_id, server_id))
posts(guild_id, server_id, last_price_eur, posted_at, PRIMARY KEY(guild_id, server_id))
queue(guild_id, server_id, filter_ids_json, first_seen_at, attempts,
      PRIMARY KEY(guild_id, server_id))
```

- `posts` ist pro Guild und Server, nicht pro Filter — das verhindert
  Doppel-Posts und macht die Ping-Logik eindeutig. Ein zweiter Discord-Server
  bekommt seine eigenen Posts, ohne dass der erste ihn blockiert.
- `seen` ist pro Filter. Hier landet auch das Baseline-Markieren beim Anlegen
  eines Filters.
- `queue` hält Treffer, die wegen der 15er-Grenze oder eines Fehlschlags noch
  nicht im Kanal stehen.

Die DB liegt im Docker-Volume, ein Neustart verliert nichts.

## Aufbau

```
src/hetzner_bot/__main__.py      Einstieg (python -m hetzner_bot)
src/hetzner_bot/config.py        Token, Intervall, Pfade aus Env
src/hetzner_bot/domain/          Server, Criteria, FilterRecord, Candidate
src/hetzner_bot/auction/         HTTP + Parsing, CPU-Tabelle
src/hetzner_bot/engine/          Matching, Treffer-Auswahl, Poll-Lauf
src/hetzner_bot/storage/         SQLite + schema.sql
src/hetzner_bot/delivery/        Embeds und Pings
src/hetzner_bot/bot/             Bot, Cogs, Texte
tests/                           Unit-Tests, Fixture der echten JSON-Antwort
data/                            SQLite-Datei (im Docker-Volume)
```

## Betrieb

- `Dockerfile` (python:3.12-slim, non-root) + `docker-compose.yml`
- `DISCORD_TOKEN` per `.env`, niemals im Repo
- Volume `./data:/app/data` für die SQLite-Datei
- `restart: unless-stopped`
- Logs als JSON-Zeilen nach stdout; Docker-Healthcheck prüft den letzten
  erfolgreichen Poll. Die Warnung an Menschen übernimmt der Bot selbst im Kanal
  (3 Fehlläufe in Folge), damit kein externer Dienst nötig ist.
- Beim Start: Command-Sync, DB-Migration (einfaches `CREATE TABLE IF NOT EXISTS`)

## Fehlerfälle

| Fall | Verhalten |
|---|---|
| HTTP-Fehler / Timeout | 3 Versuche, dann Lauf überspringen, Log + `/status` |
| JSON-Struktur unerwartet | Lauf abbrechen, ERROR mit Pfad, Healthcheck rot |
| Kanal gelöscht / keine Rechte | Log WARN, Treffer bleibt in `queue`, 3 Versuche, dann mit WARN verwerfen; `/status` zeigt den Fehler |
| Drei Polls in Folge gescheitert | Bot meldet sich im Kanal: „Ich komme seit 30 Minuten nicht an die Daten." Plus Entwarnung beim nächsten Erfolg |
| Discord-Rate-Limit | `discord.py` regelt; max. 15 Posts pro Lauf entschärft es |
| Token fehlt/ungültig | Start bricht mit klarer Meldung ab |

## Datenschutz

Gespeichert werden Guild-ID, Channel-ID, Discord-User-ID, Filter und
Server-IDs. Keine Nachrichteninhalte, keine Profile. Alles in einer SQLite-Datei
auf dem eigenen VPS.

## Tests

- Matching pro Kriterium und in Kombination, mit Fixture-Snapshot der echten
  JSON-Datei
- Dedupe: neu / bekannt / Preis gefallen / Preis gestiegen
- Preisverfall-Embed enthält alten und neuen Preis
- Validierung: leerer Filter, Preis 0, unbekannter Standort
- Parser: fehlende Felder kippen nicht um

## Meine Entscheidungen (dürfen korrigiert werden)

- SQLite statt JSON-Datei oder Redis.
- `posts` pro Guild und Server-ID, nicht pro Filter: Doppel-Post-Schutz und
  Ping-Logik bleiben eindeutig, zweite Server funktionieren ohne Extraarbeit.
- Baseline beim Filter-Anlegen liegt in `seen` (pro Filter), nicht in `posts`.
- Erster Lauf nach Filtererstellung postet nicht, sondern antwortet ephemer.
- `/watch` mit vorhandenem Namen ersetzt den Filter komplett.
- Max. 15 Posts pro Lauf, Rest in `queue` nachholen.
- Ein Filter-Name pro Person, Default `standard`, überschreibbar.
- Höchstens 5 Filter pro Person (`MAX_FILTERS_PER_USER`), nur für neue Namen.
- Logs als echte JSON-Zeilen über `json.dumps`.
- Deutsch als einzige Sprache.
- Ping auch beim Preisfall, wenn `mention` aktiv ist.
- `mention` ist kein Kriterium und zählt nicht als „mindestens eines gesetzt".
- `min_disk` zählt nutzbare Kapazität, außer bei gesetztem `disk_type` — dann
  die Rohsumme dieses Typs.
- `min_cores` über eine gepflegte CPU-Tabelle (24 Modelle). Unbekannte CPU heißt
  „passt nicht" plus Warnung in `/status`, nicht „passt".
- Ein Post zählt erst nach erfolgreicher Zustellung; Fehlschläge werden
  dreimal versucht, dann verworfen.
- Bot meldet Ausfälle selbst im Kanal, statt einen externen Watchdog zu
  verlangen.

## Offen / beim Bauen zu klären

- Filtert `https://www.hetzner.com/sb/?freetext=<ID>` tatsächlich vor? **Ja,
  geprüft im Browser: die Seite zeigt damit genau einen Treffer.** Der Bot nutzt
  diesen Link in Embeds und `/matches`.
- Ob `Timer.ReduceNextTimestamp` im Embed als „nächster Preisfall ca. 14:20"
  angezeigt wird — nice-to-have, keine Pflicht.
- Die CPU-Tabelle muss bei neuen Auktionsmodellen nachgezogen werden. Ein
  Wächter-Test schlägt fehl, sobald ein unbekannter CPU-Name in der Fixture
  auftaucht — das ist der Erinnerungsmechanismus.
