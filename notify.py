"""Discord-Embeds für Treffer."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

import discord

from hetzner.cpus import cores_for
from hetzner.models import Server

BRAND_COLOR = 0x00A88F
AUCTION_URL = "https://www.hetzner.com/sb/"


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


def _price_text(server: Server, previous_price: Decimal | None) -> str:
    current = (
        f"{server.price_month_eur} €/Monat · "
        f"{server.price_hour_eur} €/Std · Setup {server.setup_eur} €"
    )
    if previous_price is not None and previous_price > server.price_month_eur:
        return f"vorher ~~{previous_price} €~~ → jetzt **{current}**"
    return current


def build_embed(server: Server, previous_price: Decimal | None = None) -> discord.Embed:
    cores = cores_for(server.cpu_name)
    ram = f"{server.ram_gb} GB" + (" ECC" if server.ecc else "")

    embed = discord.Embed(
        title=f"{server.cpu_name} · {server.storage_total_gb} GB",
        color=BRAND_COLOR,
        url=AUCTION_URL,
    )
    embed.add_field(name="Kerne", value=str(cores) if cores is not None else "unbekannt", inline=True)
    embed.add_field(name="RAM", value=ram, inline=True)
    embed.add_field(name="Standort", value=server.datacenter or "unbekannt", inline=True)
    embed.add_field(name="Platten", value=_disk_summary(server), inline=False)
    embed.add_field(
        name="Anbindung",
        value=f"{server.bandwidth_mbit} Mbit/s · {server.traffic or 'unbekannt'}",
        inline=True,
    )
    embed.add_field(name="Server-ID", value=str(server.id), inline=True)
    embed.add_field(name="Preis", value=_price_text(server, previous_price), inline=False)
    embed.set_footer(text=f"Hetzner Serverbörse · ID {server.id}")
    return embed


def mention_prefix(user_ids: Sequence[int]) -> str:
    return " ".join(f"<@{user_id}>" for user_id in sorted(set(user_ids)))
