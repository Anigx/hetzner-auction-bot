# 03 — Datenquelle

## Woher

```
https://www.hetzner.com/_resources/app/data/app/live_data_sb.json
```

Das ist die Datei, die die Auktionsseite selbst lädt (per Browser-DevTools
gefunden: `serverboerse.js` ruft sie im `fetch`). Öffentlich, ohne Login, ohne
API-Key, etwa 100 KB, rund 100 Server.

Kein Scraping von HTML: Die Seite rendert clientseitig, die JSON ist die Wahrheit.

## Abrufregeln

- ein GET pro Lauf, alle 10 Minuten
- Timeout 10 s, 3 Versuche, exponentieller Backoff (`1 s`, `2 s`)
- `User-Agent: hetzner-auction-bot/0.1`
- Tests sprechen **nie** mit dem Netz: Fixture oder `httpx.MockTransport`

## Aufbau

```json
{ "server": [ … ], "filter": { … }, "serverCount": 98 }
```

`filter` beschreibt nur die Filter-Optionen der Webseite — der Bot ignoriert es.

## Felder, die der Bot liest

| Pfad | Bedeutung | Fallstrick |
|---|---|---|
| `Id` | Server-ID, stabil | Grundlage für Dedupe |
| `Hardware.CPU.Name` | CPU-Modell | Kernzahl steht **nicht** drin |
| `Hardware.CPU.CoreCount` | **Sockel**, nicht Kerne | immer `1` — siehe [04](04-filter.md) |
| `Hardware.RAM.Size` / `.ecc` | RAM in GB, ECC-Flag | |
| `Hardware.Storage.Size` | nutzbare Gesamtkapazität in GB | 2×4 TB im RAID → 4096 |
| `Hardware.Storage.Details.nvme/sata/hdd` | Rohgrößen je Typ | Summe kann größer sein als `Size` |
| `Details.Datacenter.Name` | z. B. `FSN1-DC14` | Standort ist das Präfix ohne Ziffern |
| `Details.Bandwidth` | Mbit/s | `1000` heißt 1 Gbit/s |
| `Details.Traffic` | z. B. `unlimited` | Text, nicht Zahl |
| `Prices.monthly/hourly/setup.EUR` | Preise | als `Decimal(str(wert))` |
| `IPPrices.Amount` | Anzahl Zusatz-IPs | wird geparst, nicht angezeigt |
| `Timer.ReduceNextTimestamp` | Unix-Zeit des nächsten Preisfalls | kann fehlen oder Unsinn sein |

## Harte Regeln im Parser

1. **Kein Feld darf werfen.** Fehlt etwas, gibt es Defaults (`0`, `False`, `""`,
   `None`) — ein einzelner kaputter Server darf nicht den Lauf abbrechen.
2. **Preise nie über `float`.** `Decimal(str(73.7))` ergibt exakt `73.7`; ein
   Cent Differenz muss erkennbar bleiben.
3. **Zeitstempel absichern.** `datetime.fromtimestamp(10**18)` wirft `OSError` —
   deshalb `_parse_reduce_ts()` mit `try/except`.
4. **Fehlende oder leere `server`-Liste ist ein Fehler** (`ParseError`), keine
   leere Auktion. Sonst würde ein Formatwechsel still die Warteschlange leeren
   und der Healthcheck bliebe grün.

## Was es nicht gibt

**Keinen Deep-Link auf einen einzelnen Server.** Der Bestell-Button der Seite ist
ein POST-Formular auf `robot.hetzner.com/order/marketConfirm`; ein GET darauf
leitet nur auf die Auktionsseite um. Deshalb zeigt das Embed die Server-ID
prominent und verlinkt die Auktionsseite. `?freetext=<ID>` filtert die Seite
nicht vor (geprüft).

## Fixture

`tests/fixtures/auction_snapshot.json` ist ein echter Snapshot und die Grundlage
aller Parser- und Matching-Tests. Erneuern:

```bash
curl.exe -s -o tests/fixtures/auction_snapshot.json \
  "https://www.hetzner.com/_resources/app/data/app/live_data_sb.json"
```

Danach `test_every_cpu_in_fixture_is_known` laufen lassen: neue CPU-Modelle
fallen dort auf.

---

Zurück: [02 — Architektur](02-architektur.md) · Weiter: [04 — Filter](04-filter.md)
