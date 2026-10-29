"""Docker-Healthcheck: war der letzte Poll erfolgreich und frisch genug?"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

DEFAULT_FILE = "data/last_poll"
DEFAULT_MAX_AGE_MINUTES = 30


def main() -> int:
    path = Path(os.environ.get("LAST_POLL_FILE", DEFAULT_FILE))
    max_age = int(os.environ.get("MAX_POLL_AGE_MINUTES", str(DEFAULT_MAX_AGE_MINUTES)))

    if not path.exists():
        print(f"healthcheck: {path} fehlt", file=sys.stderr)
        return 1

    try:
        last = datetime.fromisoformat(path.read_text(encoding="utf-8").strip())
    except ValueError:
        print("healthcheck: Zeitstempel unlesbar", file=sys.stderr)
        return 1

    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)

    age = datetime.now(UTC) - last
    if age > timedelta(minutes=max_age):
        print(f"healthcheck: letzter Poll ist {age} alt", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
