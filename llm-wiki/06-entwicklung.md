# 06 — Entwicklung

## Einmal einrichten

```bash
uv venv --python 3.12 .venv
uv pip install -r requirements.txt --python .venv/Scripts/python.exe
.venv/Scripts/python.exe -m pytest -q
```

Kein System-Python nötig; `uv` holt sich 3.12 selbst. `pyproject.toml` setzt
`pythonpath = ["."]`, damit die Tests die Module im Repo-Root finden.

## Arbeitsweise

- **Test zuerst.** Jede Regel in `filters.py`, jeder Ablauf in `poller.py` und
  `store.py` hat einen Test, der vor der Implementierung rot war.
- **Keine Netzwerkzugriffe in Tests.** Fixture plus `httpx.MockTransport`.
- **`TASKS.md` ist die Wahrheit über den Fortschritt**, `CHANGELOG.md` über die
  Historie. Beides gehört zur Definition von „fertig".

## Tests im Überblick

| Datei | Prüft |
|---|---|
| `test_config.py` | Defaults, fehlender Token, ungültige Zahlen |
| `test_parse.py` | Parser, Decimals, fehlende Felder, Schema-Drift |
| `test_fetch.py` | Retry und Fehler |
| `test_cpus.py` | Kernzahlen, Wächter-Test gegen neue Modelle |
| `test_criteria.py` | Validierung, JSON-Roundtrip |
| `test_matching.py` | jede Kriteriumsregel und Kombinationen |
| `test_store.py` | Schema, CRUD, Baseline, Warteschlange |
| `test_candidates.py` | Dedupe, Preisverfall, Baseline-Preisverfall, Pings |
| `test_notify.py` | Embed-Inhalt und Ping-Text |
| `test_poller.py` | Zustellung, Fehlversuche, Ausfallmeldung, Heartbeat |
| `test_watch_command.py`, `test_manage_commands.py`, `test_setup_command.py` | Command-Logik ohne Discord |
| `test_healthcheck.py` | frisch/alt/fehlend |

## Fixture erneuern

```bash
curl.exe -s -o tests/fixtures/auction_snapshot.json \
  "https://www.hetzner.com/_resources/app/data/app/live_data_sb.json"
.venv/Scripts/python.exe -m pytest tests/test_cpus.py -v
```

Der CPU-Test ist der Wächter: Schlägt er fehl, fehlt ein Modell in
`hetzner/cpus.py`.

## Neue Kriterien

1. Feld in `Criteria` + `_CRITERION_FIELDS`/`_NUMERIC_FIELDS` + `to_json`/`from_json`.
2. Regel in `matches()`.
3. Option in `/watch` und `build_criteria()`.
4. Text in `describe_filter()`.
5. Test in `test_criteria.py` **und** `test_matching.py`.

## Banner

`tools/make_banner.py` rendert `docs/assets/banner.png` mit Pillow (nur
Build-Zeit, nicht in `requirements.txt`):

```bash
uv pip install pillow --python .venv/Scripts/python.exe
.venv/Scripts/python.exe tools/make_banner.py
```

## Release

```bash
git tag -a v0.2.0 -m "v0.2.0 - ..."
git push origin v0.2.0
```

Der Tag startet `.github/workflows/release.yml`: Tests → Image bauen und nach
`ghcr.io/anigx/hetzner-auction-bot` pushen (`X.Y.Z`, `X.Y`, `latest`) → Release
mit `docs/releases/notes.md` anlegen, wobei `__TAG__`, `__VERSION__` und
`__IMAGE__` ersetzt werden.

Jeder Push auf `main` läuft zusätzlich durch `.github/workflows/ci.yml` (Tests,
Badge im README).

## Handwerkszeug

- Preise immer `Decimal(str(...))`.
- Zeiten in UTC speichern, nur zur Anzeige nach `Europe/Berlin`.
- Keine Secrets im Repo; `.env` ist ignoriert, `.env.example` ist die Vorlage.
- Fehler nie still schlucken: Log mit Kontext oder Meldung im Discord.

---

Zurück: [05 — Betrieb](05-betrieb.md) · Weiter: [TASKS](../TASKS.md) und [CHANGELOG](../CHANGELOG.md)
