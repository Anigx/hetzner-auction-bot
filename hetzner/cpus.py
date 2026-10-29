"""Physische Kerne je CPU-Modell der Serverbörse.

`Hardware.CPU.CoreCount` aus der Hetzner-JSON ist die Anzahl der Sockel (immer 1),
nicht die Kerne. Deshalb steht die Kernzahl hier als gepflegte Tabelle.
Der Fixture-Test in `tests/test_cpus.py` schlaegt fehl, sobald eine neue CPU
in der Auktion auftaucht.
"""

from __future__ import annotations

CORES_BY_CPU: dict[str, int] = {
    "AMD EPYC 7502P": 32,
    "AMD Ryzen 5 3600": 6,
    "AMD Ryzen 7 1700X": 8,
    "AMD Ryzen 7 3700X": 8,
    "AMD Ryzen 7 7700": 8,
    "AMD Ryzen 7 PRO 1700X": 8,
    "AMD Ryzen 9 3900": 12,
    "AMD Ryzen 9 5950X": 16,
    "Intel Core i5-12500": 6,
    "Intel Core i5-13500": 14,
    "Intel Core i7-6700": 4,
    "Intel Core i7-7700": 4,
    "Intel Core i7-8700": 6,
    "Intel Core i9-12900K": 16,
    "Intel Core i9-13900": 24,
    "Intel Core i9-9900K": 8,
    "Intel Xeon E3-1270V3": 4,
    "Intel Xeon E3-1271V3": 4,
    "Intel Xeon E3-1275v5": 4,
    "Intel Xeon E3-1275V6": 4,
    "Intel Xeon E5-1650V3": 6,
    "Intel Xeon Gold 5412U": 24,
    "Intel Xeon W-2145": 8,
    "Intel Xeon W-2295": 18,
}

_LOOKUP = {name.strip().lower(): cores for name, cores in CORES_BY_CPU.items()}


def cores_for(cpu_name: str) -> int | None:
    """Liefert die Kernzahl oder `None`, wenn das Modell unbekannt ist."""
    if not cpu_name:
        return None
    return _LOOKUP.get(cpu_name.strip().lower())
