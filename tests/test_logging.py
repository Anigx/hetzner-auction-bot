import json
import logging
import sys

from hetzner_bot.logging_setup import JsonFormatter


def test_formatter_emits_valid_json_for_awkward_messages():
    record = logging.LogRecord(
        "hetzner_bot.test", logging.INFO, __file__, 1, 'sag "hallo"\nund weiter', None, None
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["msg"] == 'sag "hallo"\nund weiter'
    assert payload["level"] == "INFO"
    assert payload["logger"] == "hetzner_bot.test"
    assert "time" in payload


def test_formatter_includes_traceback():
    try:
        raise ZeroDivisionError("boom")
    except ZeroDivisionError:
        record = logging.LogRecord(
            "hetzner_bot.test", logging.ERROR, __file__, 1, "kaputt", None, sys.exc_info()
        )
    payload = json.loads(JsonFormatter().format(record))
    assert "ZeroDivisionError" in payload["exception"]
