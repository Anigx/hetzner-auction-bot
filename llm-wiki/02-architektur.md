# 02 — Architektur

## Die eine Regel

Kernlogik kennt weder Discord noch Netzwerk. Deshalb lässt sich alles, was über
Treffer entscheidet, ohne Token und ohne Server testen.

```
Discord ──▶ cogs/commands.py ──▶ store.py (SQLite)
                   │
                   ▼
              poller.py ──▶ find_candidates()  ◀── filters.py (rein)
                   │              │
                   │              └────────────── hetzner/cpus.py (rein)
                   ▼
         hetzner/client.py ──▶ hetzner/models.py
                   │
                   ▼
              notify.py (Embed) ──▶ Discord
```

## Dateien und ihre Aufgabe

| Datei | Aufgabe | Kennt Discord? |
|---|---|---|
| `bot.py` | Kompositionswurzel: Config, Bot, Poll-Loop, Logging | ja |
| `config.py` | Env lesen und prüfen, `Config` | nein |
| `hetzner/models.py` | `Server` als frozen dataclass | nein |
| `hetzner/client.py` | HTTP mit Retry, JSON → `Server`, `ParseError`/`FetchError` | nein |
| `hetzner/cpus.py` | CPU-Name → physische Kerne | nein |
| `filters.py` | `Criteria`, Validierung, `matches()`, `FilterRecord` | nein |
| `poller.py` | `find_candidates()` (rein) und `Poller` (Ablauf, Zustellung) | nur im Poller-Teil |
| `store.py` | SQLite: Kanal, Filter, `seen`, `posts`, `baselines`, `queue` | nein |
| `notify.py` | Embed bauen, Ping-Text | nur `discord.Embed` |
| `cogs/commands.py` | Slash-Commands, Rechte, Antworten | ja |
| `healthcheck.py` | Docker-Healthcheck über `data/last_poll` | nein |
| `tools/make_banner.py` | README-Banner rendern (nur Build-Zeit) | nein |

## Warum diese Schnitte

- **`find_candidates()` ist eine reine Funktion.** Sie bekommt Server, Filter und
  zwei Nachschlage-Funktionen (`is_seen`, `last_price`) — damit ist sie mit
  Wörterbüchern statt SQLite testbar.
- **`Poller` besitzt den Ablauf, nicht die Regeln.** Er holt, vergleicht,
  begrenzt, stellt zu. Die Regeln stehen in `find_candidates()`.
- **`store.py` ist die einzige Stelle mit SQL.** Alle anderen fragen über
  Methoden.
- **Embeds sind eine pure Funktion.** `build_embed()` braucht keinen Client,
  `discord.Embed` funktioniert allein.

## Datenbank

| Tabelle | Schlüssel | Inhalt |
|---|---|---|
| `guilds` | `guild_id` | Zielkanal pro Discord-Server |
| `filters` | `id`, eindeutig `(guild_id, user_id, name)` | Kriterien als JSON, `mention`, `active`, `baseline_pending` |
| `seen` | `(filter_id, server_id)` | Was dieser Filter schon kennt (Baseline) |
| `posts` | `(guild_id, server_id)` | Zuletzt **erfolgreich geposteter** Preis |
| `baselines` | `(guild_id, server_id)` | Preis beim Anlegen/Ändern des Filters |
| `queue` | `(guild_id, server_id)` | Treffer, die noch nicht zugestellt sind |

Warum `posts` pro Guild und Server, nicht pro Filter: Ein Server wird pro Kanal
genau einmal gepostet, auch wenn fünf Filter passen. Die Ping-Liste ist die
Vereinigung aller passenden Filter.

Warum `seen` pro Filter: Die Baseline gehört zum Filter. Ein zweiter Filter darf
nicht davon profitieren — und beim Anlegen eines neuen Filters muss der Kanal
nicht erneut geflutet werden.

Warum `baselines` getrennt von `posts`: Ein baselineter Server stand nie im Kanal.
Fällt er unter den Baseline-Preis, ist die Meldung ein *neuer Treffer*, keine
Preiskorrektur — sonst würde ein „vorher 45 €" erscheinen, das niemand gesehen hat.

## Wo neue Dinge hingehören

- Neues Kriterium → `filters.Criteria` + `matches()` + `/watch`-Option + Test.
- Neue Datenquelle/anderes Feld → `hetzner/` plus Fixture.
- Neue Tabelle/Spalte → `store.py`-Schema **und** Migration in `init_schema()`.
- Neuer Command → `cogs/commands.py`; Logik, die testbar sein soll, als freie
  Funktion daneben.

---

Zurück: [01 — Überblick](01-ueberblick.md) · Weiter: [03 — Datenquelle](03-datenquelle.md)
