# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionen nach
[SemVer](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt
- 2026-10-29: CI-Workflow (Tests bei Push und PR) und Release-Workflow: ein Tag
  `v*` baut das Container-Image nach `ghcr.io/anigx/hetzner-auction-bot` und legt
  das Release mit den Notes aus `docs/releases/notes.md` an. `v0.1.0` ist
  veröffentlicht, Image öffentlich ziehbar.
- 2026-10-29: Bot umgesetzt: Parser, CPU-Tabelle, Filter, SQLite-Speicher,
  Dedupe/Preisverfall, Embeds, Slash-Commands, Poll-Loop, Docker, Healthcheck,
  README. 74 Tests grün.
- 2026-10-29: Umsetzungsplan mit 14 Tasks
  (`docs/superpowers/plans/2026-10-29-hetzner-auktion-discord-bot.md`).
- 2026-10-29: Projekt-Wiki angelegt (`AGENTS.md`, `TASKS.md`, `CHANGELOG.md`).
- 2026-10-29: Design-Dokument für den Discord-Bot zur Hetzner-Serverbörse
  (`docs/superpowers/specs/2026-10-29-hetzner-auktion-discord-bot-design.md`).

### Behoben
- 2026-10-29 (Review): `/watch cpu:...` warf einen `TypeError`, weil die
  Validierung Textfelder wie Zahlen prüfte.
- 2026-10-29 (Review): Preisrückgänge von Servern aus der Baseline wurden nie
  gemeldet. Baseline-Preise liegen jetzt in `baselines`.
- 2026-10-29 (Review): Fehlversuche wurden falsch gezählt und verworfene Treffer
  kamen in der nächsten Runde zurück.
- 2026-10-29 (Review): Ausfallmeldung ging pro Filter statt pro Server raus.
- 2026-10-29 (Review): Leere oder kaputte JSON-Antwort galt als erfolgreicher
  Lauf und leerte die Warteschlange. Ist jetzt ein Fehler.
- 2026-10-29 (Review): `/watch` speicherte bei fehlgeschlagener Baseline einen
  Filter ohne Baseline — jetzt wird sie beim nächsten Lauf nachgeholt.
- 2026-10-29 (Review): `/watch` und `/status` weisen auf einen fehlenden Kanal
  hin; Zustellfehler landen in `/status`.
- 2026-10-29 (Review): Unbekannte CPUs werden geloggt und in `/status` genannt.
- 2026-10-29 (Review): Kaputter `ReduceNextTimestamp` bricht den Lauf nicht mehr ab.

### Geändert
- 2026-10-29: Review-Runde eingearbeitet: Baseline getrennt von `posts` (`seen`
  pro Filter), `posts` pro Guild, Warteschlange für Nachzügler, Ersetzen statt
  Mischen bei `/watch`, Filter-Semantik für Platten und Kerne festgeschrieben,
  Ausfallmeldung im Kanal statt externem Watchdog.

### Erkenntnisse
- 2026-10-29: `Hardware.CPU.CoreCount` ist die Sockelzahl (immer `1`), nicht die
  Kerne. Der Kern-Filter braucht eine Tabelle CPU-Name → Kerne (24 Modelle).
- 2026-10-29: Die Auktionsseite lädt ihre Daten aus
  `/_resources/app/data/app/live_data_sb.json` — öffentlich, ohne Key, ~105 KB,
  ~100 Server, alle Specs und Preise enthalten. Kein Scraping nötig.
- 2026-10-29: Es gibt keinen Deep-Link auf einen einzelnen Auktionsserver.
  Der Bestell-Button ist ein POST-Formular an
  `robot.hetzner.com/order/marketConfirm`; ein GET leitet auf die
  Auktionsseite um. Embeds zeigen deshalb die Server-ID.
- 2026-10-29: Discord-Bots können nicht in echte Gruppen-DMs eingeladen
  werden. Der „Gruppenchat" muss ein privater Discord-Server sein.
