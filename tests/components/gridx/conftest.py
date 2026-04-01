"""Shared fixtures for gridX integration tests."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
