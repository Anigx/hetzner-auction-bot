"""Gemeinsame Testfabriken — eine Quelle für Server- und Filter-Objekte."""

from __future__ import annotations

from decimal import Decimal

from hetzner_bot.domain import Criteria, FilterRecord, Server


def build_server(id: int = 10, price: str = "45", **over) -> Server:
    data = dict(
        id=id,
        cpu_name="AMD Ryzen 9 5950X",
        sockets=1,
        ram_gb=64,
        ecc=True,
        storage_total_gb=4096,
        nvme_gb=0,
        sata_gb=0,
        hdd_gb=8000,
        location="FSN",
        datacenter="FSN1-DC14",
        bandwidth_mbit=1000,
        traffic="unlimited",
        price_month_eur=Decimal(price),
        price_hour_eur=Decimal("0.05"),
        setup_eur=Decimal("0"),
        extra_ips=1,
        reduce_next_at=None,
    )
    data.update(over)
    return Server(**data)


def build_filter(
    id: int = 1,
    guild: int = 1,
    user: int = 2,
    mention: bool = True,
    active: bool = True,
    name: str | None = None,
    delivery: str = "channel",
    **criteria,
) -> FilterRecord:
    return FilterRecord(
        id=id,
        guild_id=guild,
        user_id=user,
        name=name or f"f{id}",
        criteria=Criteria(**criteria),
        mention=mention,
        active=active,
        delivery=delivery,
    )
