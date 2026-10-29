"""Discord-Embeds für Treffer."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

import discord

from hetzner_bot.auction.cpus import cores_for
from hetzner_bot.domain import Server
from hetzner_bot.pricing import format_eur, with_vat

BRAND_COLOR = 0x00A88F
AUCTION_URL = "https://www.hetzner.com/sb/"


def server_url(server_id: int) -> str:
    """Direktlink auf einen Server: die Auktionsseite filtert per freetext-Parameter."""
    return f"{AUCTION_URL}?freetext={server_id}"


def _disk_summary(server: Server) -> str:
    parts: list[str] = []
    for label, size in (
        ("NVMe", server.nvme_gb),
        ("SATA", server.sata_gb),
        ("HDD", server.hdd_gb),
    ):
        if size > 0:
            parts.append(f"{size} GB {label}")
    return ", ".join(parts) if parts else "–"


def _price_text(
    server: Server,
    previous_price: Decimal | None,
    vat_rates: Sequence[float] = (),
    gross_first: bool = False,
) -> str:
    net = server.price_month_eur
    rate = vat_rates[0] if vat_rates else 0.0
    gross = with_vat(net, rate) if rate else net
    tail = f"{server.price_hour_eur} €/Std · Setup {server.setup_eur} €"

    if gross_first and rate:
        text = f"**{format_eur(gross)}/Monat brutto** · {tail}"
        if previous_price is not None and previous_price > net:
            text = f"vorher ~~{format_eur(with_vat(previous_price, rate))}~~ → " + text
        return text + f"\nnetto: {net} €/Monat ({rate:g} % MwSt.)"

    current = f"{net} €/Monat · {tail}"
    if previous_price is not None and previous_price > net:
        text = f"vorher ~~{previous_price} €~~ → jetzt **{current}**"
    else:
        text = current

    for shown in list(vat_rates)[:2]:
        text += (
            f"\nbrutto: **{format_eur(with_vat(net, shown))}/Monat** "
            f"({shown:g} % MwSt.)"
        )
    return text


def build_embed(
    server: Server,
    previous_price: Decimal | None = None,
    vat_rates: Sequence[float] = (),
    gross_first: bool = False,
) -> discord.Embed:
    cores = cores_for(server.cpu_name)
    ram = f"{server.ram_gb} GB" + (" ECC" if server.ecc else "")

    embed = discord.Embed(
        title=f"{server.cpu_name} · {server.storage_total_gb} GB",
        color=BRAND_COLOR,
        url=server_url(server.id),
    )
    embed.add_field(
        name="Kerne", value=str(cores) if cores is not None else "unbekannt", inline=True
    )
    embed.add_field(name="RAM", value=ram, inline=True)
    embed.add_field(name="Standort", value=server.datacenter or "unbekannt", inline=True)
    embed.add_field(name="Platten", value=_disk_summary(server), inline=False)
    embed.add_field(
        name="Anbindung",
        value=f"{server.bandwidth_mbit} Mbit/s · {server.traffic or 'unbekannt'}",
        inline=True,
    )
    embed.add_field(name="Server-ID", value=str(server.id), inline=True)
    embed.add_field(
        name="Zum Server",
        value=f"[In der Serverbörse öffnen]({server_url(server.id)})",
        inline=True,
    )
    embed.add_field(name="Preis", value=_price_text(server, previous_price, vat_rates, gross_first), inline=False)
    embed.set_footer(text=f"Hetzner Serverbörse · ID {server.id}")
    return embed


def mention_prefix(user_ids: Sequence[int]) -> str:
    return " ".join(f"<@{user_id}>" for user_id in sorted(set(user_ids)))
