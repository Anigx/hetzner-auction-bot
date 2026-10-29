# 04 — Filter und Matching

## Der Filter

Ein Filter gehört einer Person auf einem Discord-Server und hat einen Namen
(Default `standard`). Kriterien sind alle optional, aber **mindestens eines muss
gesetzt sein**. `mention` ist kein Kriterium, sondern eine Einstellung.

| Kriterium | Typ | Bedeutung |
|---|---|---|
| `max_price` | Euro/Monat | `≤` |
| `min_ram` | GB | `≥` |
| `min_cores` | Anzahl | `≥`, aus der CPU-Tabelle |
| `cpu_contains` | Text | Teilstring im CPU-Namen, ohne Groß/Klein |
| `min_disk` | TB | siehe Plattensemantik |
| `disk_type` | `egal/nvme/sata/hdd` | mindestens eine Platte dieses Typs |
| `location` | `egal/FSN/NBG/HEL` | Rechenzentrum-Standort |
| `ecc` | `egal/ja` | nur ECC-RAM |
| `no_setup` | Ja/Nein | Setup-Gebühr `0` |
| `min_bandwidth` | Mbit/s | `≥` |

Gespeichert wird JSON in `filters.criteria_json`; die Struktur ist erweiterbar
ohne Migration.

## Kernzahlen: warum eine Tabelle

`Hardware.CPU.CoreCount` ist die **Sockelzahl** (immer `1`). Es gibt kein Feld für
Kerne oder Threads. Deshalb steht in `src/hetzner_bot/auction/cpus.py` eine
gepflegte Tabelle
CPU-Modell → physische Kerne (aktuell 24 Modelle).

Unbekannte CPU heißt: `min_cores` greift **nicht** (kein stiller Treffer), dafür
gibt es eine Log-Warnung und eine Zeile in `/status`. Der Test
`test_every_cpu_in_fixture_is_known` schlägt fehl, sobald ein neues Modell in der
Auktion auftaucht — das ist der Erinnerungsmechanismus.

## Plattensemantik

- `disk_type: egal` → `min_disk` prüft die **nutzbare** Summe
  (`Hardware.Storage.Size`).
- `disk_type: nvme|sata|hdd` → mindestens eine Platte dieses Typs **und**
  `min_disk` prüft die **Rohsumme dieses Typs** (`Details.<typ>`).
- Gemischte Server erfüllen mehrere Typen gleichzeitig.
- **Kein Aufrunden:** 1966 GB sind 1,92 TB und fallen bei `min_disk: 2` raus.

## Wann gepostet wird

Pro Guild und Server:

1. Alle aktiven Filter der Guild gegen den Server prüfen.
2. Keiner passt → nichts.
3. Server wurde in dieser Guild **noch nie** gepostet:
   - Preis unter dem Baseline-Preis? → posten (neuer Treffer, ohne „vorher")
   - sonst: erst posten, wenn mindestens ein passender Filter ihn noch nicht
     gesehen hat.
4. Server wurde schon gepostet: nur posten, wenn der Preis **echt kleiner** ist
   als der zuletzt gepostete. Gleichstand zählt nicht.

Ein Server wird einmal gepostet, auch wenn fünf Filter passen. Getaggt werden alle
Personen, deren Filter gepasst hat und die `mention` aktiv haben — jede Person
höchstens einmal.

## Baseline

Beim Anlegen oder Ändern eines Filters werden alle aktuell passenden Server als
gesehen markiert **und ihr Preis als Baseline gespeichert**. Der Kanal bekommt
keine Altlast; die Person sieht nur „Aktuell passen 3 Server".

Konnte die Auktion dabei nicht geladen werden, wird der Filter mit
`baseline_pending` gespeichert und die Baseline beim nächsten erfolgreichen Lauf
nachgeholt. Sonst würde der nächste Poll 15 alte Server posten.

## Preisverfall

Jeder Rückgang zählt, auch ein Cent. Verglichen wird gegen den zuletzt
**erfolgreich im Kanal** stehenden Preis (`posts`), nicht gegen den letzten
gesehenen. Ein Server, der an der 15er-Grenze scheiterte und inzwischen günstiger
wurde, erscheint als normaler neuer Treffer — es gab ja nie einen alten Preis zu
sehen.

## Beispiele

```
/watch max_price:100 min_ram:64 min_cores:8 mention:true
/watch name:ryzen cpu:"Ryzen 9" min_disk:2 disk_type:nvme mention:true
/watch name:storage min_disk:8 disk_type:hdd location:FSN no_setup:true
```

## Grenzen

- Höchstens 5 Filter pro Person (`MAX_FILTERS_PER_USER`). Ein vorhandener Name
  darf immer überschrieben werden; die Grenze gilt nur für neue Namen.
- Kein Filter auf Traffic-Volumen (nur `unlimited` vorhanden).
- Keine Zusatz-IP-Anzahl im Filter (wird geparst, nicht angeboten).
- Keine Preishistorie — nur der letzte gepostete Preis.

---

Zurück: [03 — Datenquelle](03-datenquelle.md) · Weiter: [05 — Betrieb](05-betrieb.md)
