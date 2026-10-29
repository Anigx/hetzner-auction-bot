# 02 — Architektur

## Die eine Regel

Kernlogik kennt weder Discord noch Netzwerk. Deshalb lässt sich alles, was über
Treffer entscheidet, ohne Token und ohne Server testen.

```
Discord ──▶ bot/cogs/*.py ──▶ storage/store.py (SQLite)
                   │
                   ▼
              engine/poller.py ──▶ engine/candidates.py
                   │                      │
                   │                      └──▶ engine/matching.py  (rein)
                   ▼                                   │
         auction/client.py ──▶ domain/server.py        └──▶ auction/cpus.py (rein)
                   │
                   ▼
              delivery/embeds.py ──▶ Discord
```

## Dateien und ihre Aufgabe

| Datei | Aufgabe | Kennt Discord? |
|---|---|---|
| `src/hetzner_bot/__main__.py` | Einstieg für `python -m hetzner_bot` | nein |
| `src/hetzner_bot/config.py` | Env lesen und prüfen, `Config` | nein |
| `src/hetzner_bot/healthcheck.py` | Docker-Healthcheck über `data/last_poll` | nein |
| `src/hetzner_bot/domain/server.py` | `Server` als frozen dataclass | nein |
| `src/hetzner_bot/domain/criteria.py` | `Criteria`, Validierung, JSON | nein |
| `src/hetzner_bot/domain/records.py` | `FilterRecord`, `Candidate`, `QueuedItem` | nein |
| `src/hetzner_bot/auction/client.py` | HTTP mit Retry, JSON → `Server`, `ParseError`/`FetchError` | nein |
| `src/hetzner_bot/auction/cpus.py` | CPU-Name → physische Kerne | nein |
| `src/hetzner_bot/engine/matching.py` | `matches()` | nein |
| `src/hetzner_bot/engine/candidates.py` | `find_candidates()` — reine Funktion | nein |
| `src/hetzner_bot/engine/poller.py` | `Poller`: Ablauf, Warteschlange, Zustellung | ja (nur `get_channel`/`send`) |
| `src/hetzner_bot/storage/store.py` + `schema.sql` | SQLite: Kanal, Filter, `seen`, `posts`, `baselines`, `queue` | nein |
| `src/hetzner_bot/delivery/embeds.py` | Embed bauen, Ping-Text | nur `discord.Embed` |
| `src/hetzner_bot/bot/app.py` | Kompositionswurzel: Bot, Poll-Loop, Einstieg | ja |
| `src/hetzner_bot/bot/guards.py` | Rechteprüfungen | ja |
| `src/hetzner_bot/bot/texts.py` | Deutsche Texte, Filterbeschreibung | nein |
| `src/hetzner_bot/bot/cogs/setup.py` | `/setup` | ja |
| `src/hetzner_bot/bot/cogs/watch.py` | `/watch` + Baseline | ja |
| `src/hetzner_bot/bot/cogs/manage.py` | `/filters`, `/unwatch`, `/pause`, `/resume`, `/status` | ja |
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
- Neue Tabelle/Spalte → `storage/schema.sql` **und** Migration in `init_schema()`.
- Neuer Command → eigenes Modul in `bot/cogs/`; Logik, die testbar sein soll, als
  freie Funktion daneben (`build_criteria`, `snap_to_current`).

---

Zurück: [01 — Überblick](01-ueberblick.md) · Weiter: [03 — Datenquelle](03-datenquelle.md)
