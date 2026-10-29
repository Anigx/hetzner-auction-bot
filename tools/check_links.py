"""Prüft relative Markdown-Links im Wiki und in den Root-Dokumenten."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [ROOT / "llm-wiki", ROOT / "AGENTS.md", ROOT / "README.md", ROOT / "TASKS.md"]
PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def markdown_files() -> list[Path]:
    files: list[Path] = []
    for target in TARGETS:
        if target.is_dir():
            files.extend(sorted(target.glob("*.md")))
        elif target.exists():
            files.append(target)
    return files


def main() -> int:
    broken: list[str] = []
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for match in PATTERN.finditer(text):
            link = match.group(1).strip()
            if link.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = (path.parent / link.split("#", 1)[0]).resolve()
            if not target.exists():
                broken.append(f"{path.relative_to(ROOT)} -> {link}")

    if broken:
        print("\n".join(broken))
        print(f"\n{len(broken)} kaputte Links")
        return 1

    print(f"{len(markdown_files())} Dateien, alle relativen Links ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
