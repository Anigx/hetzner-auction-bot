"""Deutsche Texte für Commands und Antworten."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from hetzner_bot.delivery import server_url
from hetzner_bot.domain import Criteria, FilterRecord, Server

BERLIN = ZoneInfo("Europe/Berlin")


def format_local(moment: datetime) -> str:
    return moment.astimezone(BERLIN).strftime("%d.%m.%Y %H:%M")


def criteria_parts(criteria: Criteria) -> list[str]:
    parts: list[str] = []
    if criteria.max_price is not None:
        parts.append(f"≤ {criteria.max_price} €/Monat")
    if criteria.min_ram is not None:
        parts.append(f"≥ {criteria.min_ram} GB RAM")
    if criteria.min_cores is not None:
        parts.append(f"≥ {criteria.min_cores} Kerne")
    if criteria.cpu_contains is not None:
        parts.append(f"CPU enthält '{criteria.cpu_contains}'")
    if criteria.min_disk is not None:
        suffix = "" if criteria.disk_type == "egal" else f" {criteria.disk_type.upper()}"
        parts.append(f"≥ {criteria.min_disk} TB{suffix}")
    elif criteria.disk_type != "egal":
        parts.append(criteria.disk_type.upper())
    if criteria.location != "egal":
        parts.append(criteria.location)
    if criteria.ecc == "ja":
        parts.append("ECC")
    if criteria.no_setup:
        parts.append("ohne Setup")
    if criteria.min_bandwidth is not None:
        parts.append(f"≥ {criteria.min_bandwidth} Mbit/s")
    return parts or ["alles"]


def describe_filter(record: FilterRecord, match_count: int) -> str:
    text = f"**{record.name}** — " + ", ".join(criteria_parts(record.criteria))
    text += f" · {match_count} passende Server"
    if record.mention:
        text += " · Ping an"
    if not record.active:
        text += " · pausiert"
    return text


def channel_warning(channel_id: int | None) -> str | None:
    """Hinweis, wenn fuer diese Guild noch kein Kanal eingerichtet ist."""
    if channel_id is None:
        return "Noch kein Kanal eingerichtet — ein Admin muss `/setup` ausführen."
    return None


def format_match_line(server: Server) -> str:
    """Eine Zeile für /matches — mit Direktlink auf den Server."""
    return (
        f"**{server.cpu_name}** · {server.ram_gb} GB RAM · "
        f"{server.storage_total_gb} GB Platten · {server.price_month_eur} €/Monat — "
        f"[ID {server.id}]({server_url(server.id)})"
    )


HELP_TEXT = """**Hetzner Auction Bot**

Ich beobachte die Hetzner-Serverbörse alle 10 Minuten und melde nur Server, die \
zu deinen Filtern passen.

**Befehle**
`/watch` — Filter anlegen oder überschreiben
`/matches` — was gerade zu deinen Filtern passt, mit Direktlink
`/filters` — deine Filter ansehen
`/pause` · `/resume` — Filter pausieren oder wieder anschalten
`/unwatch` — Filter löschen
`/status` — Zustand des Bots
`/setup` — Zielkanal festlegen (nur Server-Verwaltung)

**Filter** (mindestens eins nötig)
`max_price` €/Monat · `min_ram` GB · `min_cores` Kerne · `cpu` Text im CPU-Namen ·
`min_disk` TB · `disk_type` nvme/sata/hdd · `location` FSN/NBG/HEL · `ecc` ·
`no_setup` · `min_bandwidth` Mbit/s

**Zustellung**
`delivery:kanal` (Standard) — Treffer gehen in den Kanal, mit `mention:true` wirst du getaggt.
`delivery:dm` — Treffer kommen nur dir als Direktnachricht, nichts geht in den Kanal.

**Preise**
Angezeigt wird der Nettopreis der Börse; ist ein Steuersatz hinterlegt \
(`VAT_PERCENT`), zusätzlich brutto. `max_price` vergleicht dann den Bruttopreis.

**Beim Anlegen** bekommst du nur eine Zahl: was jetzt schon passt, wird nicht \
gepostet. Danach melde ich neue Server und Preisfälle."""


def guild_count_warning(guild_count: int) -> str | None:
    """Hinweis, wenn der Bot in keinem Server Mitglied ist.

    Leicht zu verwechseln: Eine Einladung nur mit dem Scope ``applications.commands``
    installiert die Commands, macht den Bot aber nicht zum Mitglied — er steht dann
    unter Integrationen und kann keinen Kanal sehen.
    """
    if guild_count == 0:
        return (
            "Bot ist in keinem Server Mitglied. Die Einladung braucht den Scope "
            "'bot' (nicht nur 'applications.commands') und die Rechte Kanaele "
            "ansehen, Nachrichten senden, Links einbetten."
        )
    return None
