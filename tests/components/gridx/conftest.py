"""Shared fixtures for gridX integration tests."""

import inspect
import json
from pathlib import Path

import aiohttp
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# aiohttp 3.14 made ClientResponse's stream_writer a required keyword argument.
# aioresponses builds its fake responses without it (still true in 0.7.9), so
# every mocked request raises TypeError. Supply the one attribute aiohttp reads
# from it when writer is None, which is the path aioresponses takes.
if "stream_writer" in inspect.signature(aiohttp.ClientResponse.__init__).parameters:

    class _NoStreamWriter:
        output_size = 0

    _orig_client_response_init = aiohttp.ClientResponse.__init__

    def _client_response_init(self, *args, **kwargs):
        kwargs.setdefault("stream_writer", _NoStreamWriter())
        _orig_client_response_init(self, *args, **kwargs)

    aiohttp.ClientResponse.__init__ = _client_response_init


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file by name."""
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
def gateways_fixture() -> dict:
    """Raw gateways API response."""
    return load_fixture("gateways.json")


@pytest.fixture
def live_data_fixture() -> dict:
    """Raw live data API response."""
    return load_fixture("live_data.json")


@pytest.fixture
def live_data_minimal_fixture() -> dict:
    """Minimal live data API response."""
    return load_fixture("live_data_minimal.json")


@pytest.fixture
def live_data_multi_fixture() -> dict:
    """Multi-appliance live data API response."""
    return load_fixture("live_data_multi.json")


@pytest.fixture
def historical_data_fixture() -> dict:
    """Raw historical API response."""
    return load_fixture("historical_data.json")
