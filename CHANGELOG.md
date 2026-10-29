# Changelog

Alle nennenswerten Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionen nach
[SemVer](https://semver.org/lang/de/).

## [Unreleased]

### Hinzugefügt
- 2026-10-29: Umsetzungsplan mit 14 Tasks
  (`docs/superpowers/plans/2026-10-29-hetzner-auktion-discord-bot.md`).
- 2026-10-29: Projekt-Wiki angelegt (`AGENTS.md`, `TASKS.md`, `CHANGELOG.md`).
- 2026-10-29: Design-Dokument für den Discord-Bot zur Hetzner-Serverbörse
  (`docs/superpowers/specs/2026-10-29-hetzner-auktion-discord-bot-design.md`).

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
