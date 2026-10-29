# LLM-Wiki — Hetzner Auction Bot

Einstieg für Menschen und Agenten. Die Kapitel bauen aufeinander auf: Wer vorne
anfängt, versteht jede Entscheidung, ohne den Code zu lesen.

## Lesereihenfolge

| # | Kapitel | Beantwortet |
|---|---|---|
| 01 | [Überblick](01-ueberblick.md) | Was der Bot tut, für wen, was er bewusst nicht tut |
| 02 | [Architektur](02-architektur.md) | Welche Datei was macht, wie die Daten fließen |
| 03 | [Datenquelle](03-datenquelle.md) | Woher die Server kommen und wo die Fallstricke liegen |
| 04 | [Filter und Matching](04-filter.md) | Was ein Filter bedeutet, bis auf die letzte Semantik |
| 05 | [Betrieb](05-betrieb.md) | Container, Volume, Healthcheck, Updates, Ausfälle |
| 06 | [Entwicklung](06-entwicklung.md) | Tests, Fixture, CPU-Tabelle, Release |

## Lebende Listen

Diese beiden Dateien liegen im Repo-Root, weil GitHub und Werkzeuge sie dort
erwarten. Sie sind Teil des Wikis:

- [TASKS.md](../TASKS.md) — was noch offen ist
- [CHANGELOG.md](../CHANGELOG.md) — was wann passiert ist

## Tiefere Dokumente

- [Design](../docs/superpowers/specs/2026-10-29-hetzner-auktion-discord-bot-design.md) — warum es so aussieht
- [Umsetzungsplan](../docs/superpowers/plans/2026-10-29-hetzner-auktion-discord-bot.md) — wie es gebaut wurde
- [Release Notes](../docs/releases/notes.md) — Vorlage für GitHub-Releases
- [README](../README.md) — die kurze Version für Besucher

## Regel für dieses Wiki

Neues Wissen gehört in das Kapitel, zu dem es inhaltlich passt — nicht als Anhang
ans Ende. Wenn eine Aussage in zwei Kapiteln stehen müsste, steht sie in dem
früheren und wird im späteren verlinkt. Jede Verhaltensänderung zieht das
[Design](../docs/superpowers/specs/2026-10-29-hetzner-auktion-discord-bot-design.md)
und das passende Kapitel nach.

---

Weiter: [01 — Überblick](01-ueberblick.md)
