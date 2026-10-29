"""Gemeinsame Fixtures."""

import pytest

from hetzner_bot.storage import Store
from tests.factories import build_filter, build_server


@pytest.fixture
def make_server():
    return build_server


@pytest.fixture
def make_filter():
    return build_filter


@pytest.fixture
def store(tmp_path):
    database = Store(tmp_path / "test.sqlite3")
    database.init_schema()
    yield database
    database.close()
