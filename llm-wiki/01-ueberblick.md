# 01 — Überblick

## Das Problem

Gute Server in der Hetzner-Serverbörse sind innerhalb von Minuten weg. Wer nicht
selbst alle paar Minuten die Seite neu lädt, sieht sie nie. Gleichzeitig will
niemand einen Kanal voller Server, die ihn nicht interessieren.

## Die Lösung

Ein Discord-Bot, der die Auktion alle zehn Minuten liest, sie gegen gespeicherte
Filter prüft und **nur Treffer** in einen festgelegten Kanal postet. Jede Person
im Kanal legt ihren eigenen Filter an und entscheidet, ob sie dabei getaggt wird.

## Für wen

Für eine geschlossene Gruppe auf einem Discord-Server — Freunde, ein Verein, ein
kleines Team. Nicht für den öffentlichen Betrieb auf fremden Servern: Der Bot
rechnet mit einer überschaubaren Zahl Filter und einem Kanal pro Server.

## Was der Bot bewusst nicht tut

- Nicht bestellen, nicht klicken. Der Bestellvorgang bleibt beim Menschen.
- Keine Cloud-Server, keine Neubestellung — nur die Auktionsbörse.
- Keine DMs, keine Web-Oberfläche, keine Preisprognose.
- Keine Preisalarme auf *steigende* Preise.

## Woran man Erfolg misst

1. Ein Deal steht im Kanal, bevor er weg ist — die Verzögerung ist höchstens ein
   Poll-Intervall plus Zustellung.
2. Es steht nichts im Kanal, was nicht mindestens einen Filter erfüllt.
3. Jeder Server erscheint einmal; nur ein echter Preisrückgang erzeugt eine
   zweite Meldung.
4. Ein neuer Filter flutet den Kanal nicht mit Altbestand.
5. Fällt die Datenquelle aus, merkt es jemand — der Bot selbst oder der
   Healthcheck.

## Kurzfakten

| Punkt | Wert |
|---|---|
| Prüfintervall | 10 Minuten, ein HTTP-Request pro Lauf |
| Posts pro Lauf | höchstens 15, Rest in einer Warteschlange |
| Speicher | SQLite im Docker-Volume `hetzner-auction-bot-data` |
| Sprache | Deutsch in allen Bot-Antworten |
| Verteilung | Container-Image `ghcr.io/anigx/hetzner-auction-bot` |
| Lizenz | MIT |

## Der Ablauf in einem Satz

Auktions-JSON holen → in `Server`-Objekte parsen → gegen alle aktiven Filter
matchen → pro Server entscheiden, ob neu oder preisgefallen → Embed bauen, pingen,
in den Kanal schreiben → Zustand merken.

Wie das im Code aussieht, steht im nächsten Kapitel.

---

Zurück: [Index](README.md) · Weiter: [02 — Architektur](02-architektur.md)
