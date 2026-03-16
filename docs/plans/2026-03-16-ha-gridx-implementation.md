# ha-gridx Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS-compatible HA integration that polls the gridX cloud API for live energy data and exposes sensors with proper device grouping.

**Architecture:** Single DataUpdateCoordinator polls one REST endpoint per system. Typed dataclasses model the response. Device-per-appliance pattern creates separate HA devices for batteries, heat pumps, etc. API client is HA-independent (pure async + aiohttp).

**Tech Stack:** Python 3.12+, aiohttp, Home Assistant 2026.x, pytest, ruff

**Spec:** `docs/specs/2026-03-16-ha-gridx-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `custom_components/gridx/__init__.py` | Entry setup, unload, platform forwarding |
| `custom_components/gridx/const.py` | Domain, URLs, Auth0 config, defaults |
| `custom_components/gridx/models.py` | Pure dataclasses + `parse_live_data()` |
| `custom_components/gridx/api.py` | Async API client (auth, gateways, live data) |
| `custom_components/gridx/coordinator.py` | DataUpdateCoordinator with backoff |
| `custom_components/gridx/config_flow.py` | Setup + reauth flows |
| `custom_components/gridx/sensor.py` | Entity descriptions, platform setup, entity classes |
| `custom_components/gridx/diagnostics.py` | Config entry diagnostics with redaction |
| `custom_components/gridx/manifest.json` | Integration metadata |
| `custom_components/gridx/strings.json` | Translations |
| `custom_components/gridx/icons.json` | Custom icons |
| `hacs.json` | HACS repository config |
| `tests/components/gridx/conftest.py` | Shared fixtures, mock API |
| `tests/components/gridx/fixtures/*.json` | API response samples |
| `tests/components/gridx/test_models.py` | Data model parsing tests |
| `tests/components/gridx/test_api.py` | API client tests |
| `tests/components/gridx/test_config_flow.py` | Config flow tests |
| `tests/components/gridx/test_coordinator.py` | Coordinator tests |
| `tests/components/gridx/test_sensor.py` | Sensor entity tests |
| `tests/components/gridx/test_diagnostics.py` | Diagnostics tests |

---

## Chunk 1: Project Scaffold & Data Models

### Task 1: Project scaffold and static files

**Files:**
- Create: `custom_components/gridx/manifest.json`
- Create: `custom_components/gridx/const.py`
- Create: `custom_components/gridx/__init__.py` (stub)
- Create: `custom_components/gridx/strings.json` (stub)
- Create: `hacs.json`
- Create: `LICENSE`

- [ ] **Step 1: Create manifest.json**

```json
{
  "domain": "gridx",
  "name": "gridX Energy Management",
  "version": "1.0.0",
  "integration_type": "hub",
  "config_flow": true,
  "iot_class": "cloud_polling",
  "codeowners": ["@lackas"],
  "requirements": [],
  "documentation": "https://github.com/lackas/ha-gridx",
  "issue_tracker": "https://github.com/lackas/ha-gridx/issues"
}
```

- [ ] **Step 2: Create const.py**

```python
"""Constants for the gridX integration."""

from typing import Final

DOMAIN: Final = "gridx"

# Auth0 (E.ON Home)
AUTH0_TOKEN_URL: Final = "https://gridx.eu.auth0.com/oauth/token"
AUTH0_CLIENT_ID: Final = "mG0Phmo7DmnvAqO7p6B0WOYBODppY3cc"
AUTH0_AUDIENCE: Final = "my.gridx"
AUTH0_REALM: Final = "eon-home-authentication-db"
AUTH0_SCOPE: Final = "email openid offline_access"
AUTH0_GRANT_TYPE: Final = "http://auth0.com/oauth/grant-type/password-realm"

# gridX API
API_BASE_URL: Final = "https://api.gridx.de"
API_GATEWAYS_URL: Final = f"{API_BASE_URL}/gateways"
API_LIVE_URL: Final = f"{API_BASE_URL}/systems/{{}}/live"

# Polling
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
ERROR_SCAN_INTERVAL_BASE: Final = 120  # seconds
ERROR_SCAN_INTERVAL_MAX: Final = 900  # 15 minutes

# Auth cooldown
AUTH_COOLDOWN_SECONDS: Final = 60

# SG Ready states
SG_READY_STATES: Final = ["AUTO", "BOOST", "OFF", "BLOCK"]
```

- [ ] **Step 3: Create stub `__init__.py`**

```python
"""The gridX Energy Management integration."""
```

- [ ] **Step 4: Create stub strings.json**

```json
{
  "config": {
    "step": {
      "user": {
        "title": "gridX Energy Management",
        "description": "Enter your E.ON Home / gridX account credentials.",
        "data": {
          "email": "Email",
          "password": "Password"
        }
      },
      "reauth_confirm": {
        "title": "Re-authenticate gridX",
        "description": "Your gridX session has expired. Please enter your password again.",
        "data": {
          "password": "Password"
        }
      }
    },
    "error": {
      "invalid_auth": "Invalid credentials",
      "cannot_connect": "Cannot connect to gridX API"
    },
    "abort": {
      "already_configured": "This account is already configured",
      "reauth_successful": "Re-authentication successful"
    }
  }
}
```

- [ ] **Step 5: Create hacs.json**

```json
{
  "name": "gridX Energy Management",
  "render_readme": true
}
```

- [ ] **Step 6: Create LICENSE (Apache 2.0)**

Download standard Apache 2.0 text with `Copyright 2026 Christian Lackas`.

- [ ] **Step 7: Commit**

```bash
git add custom_components/ hacs.json LICENSE
git commit -m "Add project scaffold: manifest, constants, stubs"
```

### Task 2: Test fixtures

**Files:**
- Create: `tests/components/gridx/__init__.py`
- Create: `tests/components/gridx/fixtures/gateways.json`
- Create: `tests/components/gridx/fixtures/live_data.json`
- Create: `tests/components/gridx/fixtures/live_data_minimal.json`
- Create: `tests/components/gridx/fixtures/live_data_multi.json`

- [ ] **Step 1: Create gateways.json**

Based on the real gridX API response structure:

```json
[
  {
    "system": {
      "id": "system-id-001"
    },
    "name": "My Gateway"
  }
]
```

- [ ] **Step 2: Create live_data.json**

Full response with 1 battery, 1 heat pump (based on real system data from Christian's setup):

```json
{
  "batteries": [
    {
      "applianceID": "battery-001",
      "capacity": 15000,
      "charge": 0,
      "discharge": 2285.49,
      "nominalCapacity": 15000,
      "power": 2285.49,
      "remainingCharge": 8700,
      "stateOfCharge": 0.58
    }
  ],
  "battery": {
    "capacity": 15000,
    "charge": 0,
    "discharge": 2285.49,
    "nominalCapacity": 15000,
    "power": 2285.49,
    "remainingCharge": 8700,
    "stateOfCharge": 0.58
  },
  "consumption": 1728.769,
  "directConsumption": 0,
  "directConsumptionEV": 0,
  "directConsumptionHeatPump": 578.954,
  "directConsumptionHeater": 0,
  "directConsumptionHousehold": 0,
  "directConsumptionRate": 0.55,
  "grid": 22.233,
  "gridMeterReadingNegative": 285480000,
  "gridMeterReadingPositive": 1428840000,
  "heatPump": 578.954,
  "heatPumps": [
    {
      "applianceID": "heatpump-001",
      "power": 578.954,
      "sgReadyState": "AUTO"
    }
  ],
  "measuredAt": "2026-03-16T19:27:28Z",
  "photovoltaic": 0,
  "production": 0,
  "selfConsumption": 0,
  "selfConsumptionRate": 0.88,
  "selfSufficiencyRate": 0.97,
  "selfSupply": 2285.49,
  "totalConsumption": 2307.723
}
```

- [ ] **Step 3: Create live_data_minimal.json**

No batteries, no heat pumps, no EV, no heaters:

```json
{
  "consumption": 500.0,
  "directConsumptionEV": 0,
  "directConsumptionHeatPump": 0,
  "directConsumptionHeater": 0,
  "directConsumptionHousehold": 200.0,
  "directConsumptionRate": 0.4,
  "grid": 300.0,
  "gridMeterReadingNegative": 100000,
  "gridMeterReadingPositive": 500000,
  "heatPump": 0,
  "measuredAt": "2026-03-16T12:00:00Z",
  "photovoltaic": 200.0,
  "production": 200.0,
  "selfConsumption": 200.0,
  "selfConsumptionRate": 1.0,
  "selfSufficiencyRate": 0.4,
  "selfSupply": 200.0,
  "totalConsumption": 500.0
}
```

- [ ] **Step 4: Create live_data_multi.json**

2 batteries, 2 heat pumps for dynamic naming tests:

```json
{
  "batteries": [
    {
      "applianceID": "battery-001",
      "capacity": 15000,
      "charge": 100,
      "discharge": 0,
      "nominalCapacity": 15000,
      "power": -100,
      "remainingCharge": 10000,
      "stateOfCharge": 0.67
    },
    {
      "applianceID": "battery-002",
      "capacity": 5000,
      "charge": 0,
      "discharge": 500,
      "nominalCapacity": 5000,
      "power": 500,
      "remainingCharge": 2000,
      "stateOfCharge": 0.4
    }
  ],
  "battery": {
    "capacity": 20000,
    "charge": 100,
    "discharge": 500,
    "nominalCapacity": 20000,
    "power": 400,
    "remainingCharge": 12000,
    "stateOfCharge": 0.6
  },
  "consumption": 2000.0,
  "directConsumptionEV": 0,
  "directConsumptionHeatPump": 800.0,
  "directConsumptionHeater": 0,
  "directConsumptionHousehold": 700.0,
  "directConsumptionRate": 0.75,
  "grid": 500.0,
  "gridMeterReadingNegative": 200000,
  "gridMeterReadingPositive": 800000,
  "heatPump": 800.0,
  "heatPumps": [
    {
      "applianceID": "heatpump-001",
      "power": 600.0,
      "sgReadyState": "AUTO"
    },
    {
      "applianceID": "heatpump-002",
      "power": 200.0,
      "sgReadyState": "BOOST"
    }
  ],
  "measuredAt": "2026-03-16T14:00:00Z",
  "photovoltaic": 1500.0,
  "production": 1500.0,
  "selfConsumption": 1500.0,
  "selfConsumptionRate": 1.0,
  "selfSufficiencyRate": 0.75,
  "selfSupply": 1500.0,
  "totalConsumption": 2000.0
}
```

- [ ] **Step 5: Create tests/__init__.py and tests/components/gridx/__init__.py**

Empty files for Python package structure.

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "Add test fixtures with real-world API response samples"
```

### Task 3: Data models with TDD

**Files:**
- Create: `custom_components/gridx/models.py`
- Create: `tests/components/gridx/test_models.py`

- [ ] **Step 1: Write test_models.py — full parsing test**

```python
"""Tests for gridX data models."""

import json
from pathlib import Path
from datetime import datetime, timezone

from custom_components.gridx.models import (
    GridxSystemData,
    GridxBattery,
    GridxHeatPump,
    parse_live_data,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_parse_full_response():
    data = load_fixture("live_data.json")
    result = parse_live_data(data)

    assert isinstance(result, GridxSystemData)
    assert result.consumption == 1728.769
    assert result.grid == 22.233
    assert result.photovoltaic == 0
    assert result.production == 0
    assert result.self_consumption == 0
    assert result.self_supply == 2285.49
    assert result.self_consumption_rate == 0.88
    assert result.self_sufficiency_rate == 0.97
    assert result.direct_consumption_heat_pump == 578.954
    assert result.direct_consumption_household == 0
    assert result.direct_consumption_ev == 0
    assert result.direct_consumption_heater == 0
    assert result.direct_consumption_rate == 0.55
    assert result.heat_pump == 578.954
    assert result.grid_meter_reading_negative == 285480000
    assert result.grid_meter_reading_positive == 1428840000
    assert result.total_consumption == 2307.723
    assert isinstance(result.measured_at, datetime)

    # Battery
    assert len(result.batteries) == 1
    bat = result.batteries[0]
    assert isinstance(bat, GridxBattery)
    assert bat.appliance_id == "battery-001"
    assert bat.state_of_charge == 0.58
    assert bat.capacity == 15000
    assert bat.nominal_capacity == 15000
    assert bat.power == 2285.49
    assert bat.charge == 0
    assert bat.discharge == 2285.49

    # Heat pump
    assert len(result.heat_pumps) == 1
    hp = result.heat_pumps[0]
    assert isinstance(hp, GridxHeatPump)
    assert hp.appliance_id == "heatpump-001"
    assert hp.power == 578.954
    assert hp.sg_ready_state == "AUTO"


def test_parse_minimal_response():
    data = load_fixture("live_data_minimal.json")
    result = parse_live_data(data)

    assert result.consumption == 500.0
    assert result.batteries == []
    assert result.heat_pumps == []
    assert result.ev_charging_stations == []
    assert result.heaters == []


def test_parse_multi_appliance_response():
    data = load_fixture("live_data_multi.json")
    result = parse_live_data(data)

    assert len(result.batteries) == 2
    assert result.batteries[0].appliance_id == "battery-001"
    assert result.batteries[1].appliance_id == "battery-002"

    assert len(result.heat_pumps) == 2
    assert result.heat_pumps[0].sg_ready_state == "AUTO"
    assert result.heat_pumps[1].sg_ready_state == "BOOST"


def test_parse_missing_fields_default():
    """Unknown/missing fields default to 0.0 or empty list."""
    result = parse_live_data({"measuredAt": "2026-01-01T00:00:00Z"})

    assert result.production == 0.0
    assert result.grid == 0.0
    assert result.batteries == []
    assert result.heat_pumps == []


def test_parse_unknown_fields_ignored():
    """Extra fields in API response should not cause errors."""
    data = load_fixture("live_data_minimal.json")
    data["someNewField"] = 42
    data["anotherNewThing"] = {"nested": True}
    result = parse_live_data(data)

    assert result.consumption == 500.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/src/ha-gridx && python -m pytest tests/components/gridx/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'custom_components.gridx.models'`

- [ ] **Step 3: Implement models.py**

```python
"""Data models for gridX API responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class GridxBattery:
    """Single battery appliance."""

    appliance_id: str
    state_of_charge: float = 0.0
    capacity: float = 0.0
    nominal_capacity: float = 0.0
    power: float = 0.0
    remaining_charge: float = 0.0
    charge: float = 0.0
    discharge: float = 0.0


@dataclass
class GridxHeatPump:
    """Single heat pump appliance."""

    appliance_id: str
    power: float = 0.0
    sg_ready_state: str = ""


@dataclass
class GridxEVChargingStation:
    """Single EV charging station appliance."""

    appliance_id: str
    power: float = 0.0
    state_of_charge: float = 0.0
    current_l1: float = 0.0
    current_l2: float = 0.0
    current_l3: float = 0.0
    reading_total: float = 0.0


@dataclass
class GridxHeater:
    """Single heater appliance."""

    appliance_id: str
    power: float = 0.0
    temperature: float = 0.0


@dataclass
class GridxSystemData:
    """Parsed live data for one gridX system."""

    production: float = 0.0
    photovoltaic: float = 0.0
    consumption: float = 0.0
    total_consumption: float = 0.0
    grid: float = 0.0
    self_consumption: float = 0.0
    self_supply: float = 0.0
    self_consumption_rate: float = 0.0
    self_sufficiency_rate: float = 0.0
    direct_consumption_household: float = 0.0
    direct_consumption_heat_pump: float = 0.0
    direct_consumption_ev: float = 0.0
    direct_consumption_heater: float = 0.0
    direct_consumption_rate: float = 0.0
    heat_pump: float = 0.0
    grid_meter_reading_negative: float = 0.0
    grid_meter_reading_positive: float = 0.0
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    batteries: list[GridxBattery] = field(default_factory=list)
    heat_pumps: list[GridxHeatPump] = field(default_factory=list)
    ev_charging_stations: list[GridxEVChargingStation] = field(default_factory=list)
    heaters: list[GridxHeater] = field(default_factory=list)


def _parse_batteries(raw: list[dict]) -> list[GridxBattery]:
    return [
        GridxBattery(
            appliance_id=b.get("applianceID", ""),
            state_of_charge=b.get("stateOfCharge", 0.0),
            capacity=b.get("capacity", 0.0),
            nominal_capacity=b.get("nominalCapacity", 0.0),
            power=b.get("power", 0.0),
            remaining_charge=b.get("remainingCharge", 0.0),
            charge=b.get("charge", 0.0),
            discharge=b.get("discharge", 0.0),
        )
        for b in raw
    ]


def _parse_heat_pumps(raw: list[dict]) -> list[GridxHeatPump]:
    return [
        GridxHeatPump(
            appliance_id=hp.get("applianceID", ""),
            power=hp.get("power", 0.0),
            sg_ready_state=hp.get("sgReadyState", ""),
        )
        for hp in raw
    ]


def _parse_ev_charging_stations(raw: list[dict]) -> list[GridxEVChargingStation]:
    return [
        GridxEVChargingStation(
            appliance_id=ev.get("applianceID", ""),
            power=ev.get("power", 0.0),
            state_of_charge=ev.get("stateOfCharge", 0.0),
            current_l1=ev.get("currentL1", 0.0),
            current_l2=ev.get("currentL2", 0.0),
            current_l3=ev.get("currentL3", 0.0),
            reading_total=ev.get("readingTotal", 0.0),
        )
        for ev in raw
    ]


def _parse_heaters(raw: list[dict]) -> list[GridxHeater]:
    return [
        GridxHeater(
            appliance_id=h.get("applianceID", ""),
            power=h.get("power", 0.0),
            temperature=h.get("temperature", 0.0),
        )
        for h in raw
    ]


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_live_data(data: dict) -> GridxSystemData:
    """Parse a raw gridX live data API response into typed models."""
    return GridxSystemData(
        production=data.get("production", 0.0),
        photovoltaic=data.get("photovoltaic", 0.0),
        consumption=data.get("consumption", 0.0),
        total_consumption=data.get("totalConsumption", 0.0),
        grid=data.get("grid", 0.0),
        self_consumption=data.get("selfConsumption", 0.0),
        self_supply=data.get("selfSupply", 0.0),
        self_consumption_rate=data.get("selfConsumptionRate", 0.0),
        self_sufficiency_rate=data.get("selfSufficiencyRate", 0.0),
        direct_consumption_household=data.get("directConsumptionHousehold", 0.0),
        direct_consumption_heat_pump=data.get("directConsumptionHeatPump", 0.0),
        direct_consumption_ev=data.get("directConsumptionEV", 0.0),
        direct_consumption_heater=data.get("directConsumptionHeater", 0.0),
        direct_consumption_rate=data.get("directConsumptionRate", 0.0),
        heat_pump=data.get("heatPump", 0.0),
        grid_meter_reading_negative=data.get("gridMeterReadingNegative", 0.0),
        grid_meter_reading_positive=data.get("gridMeterReadingPositive", 0.0),
        measured_at=_parse_timestamp(data["measuredAt"]) if "measuredAt" in data else datetime.now(timezone.utc),
        batteries=_parse_batteries(data.get("batteries", [])),
        heat_pumps=_parse_heat_pumps(data.get("heatPumps", [])),
        ev_charging_stations=_parse_ev_charging_stations(data.get("evChargingStations", [])),
        heaters=_parse_heaters(data.get("heaters", [])),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ~/src/ha-gridx && python -m pytest tests/components/gridx/test_models.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Lint**

```bash
ruff format custom_components/gridx/models.py tests/components/gridx/test_models.py
ruff check custom_components/gridx/models.py tests/components/gridx/test_models.py
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/gridx/models.py tests/components/gridx/test_models.py
git commit -m "Add data models with parsing and tests"
```

---

## Chunk 2: API Client

### Task 4: API client exceptions

**Files:**
- Create: `custom_components/gridx/api.py` (exceptions only first)

- [ ] **Step 1: Define exception hierarchy at top of api.py**

```python
"""Async API client for gridX energy management."""


class GridxError(Exception):
    """Base exception for gridX API errors."""


class GridxAuthenticationError(GridxError):
    """Authentication failed (bad credentials, expired, 401/403)."""


class GridxConnectionError(GridxError):
    """Connection failed (timeout, DNS, refused)."""


class GridxApiError(GridxError):
    """Unexpected API error (5xx, bad response)."""
```

- [ ] **Step 2: Commit**

```bash
git add custom_components/gridx/api.py
git commit -m "Add API exception hierarchy"
```

### Task 5: API client with TDD

**Files:**
- Modify: `custom_components/gridx/api.py`
- Create: `tests/components/gridx/test_api.py`
- Create: `tests/components/gridx/conftest.py`

- [ ] **Step 1: Create conftest.py with shared fixtures**

```python
"""Shared test fixtures for gridX tests."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def gateways_response():
    return load_fixture("gateways.json")


@pytest.fixture
def live_data_response():
    return load_fixture("live_data.json")


@pytest.fixture
def live_data_minimal_response():
    return load_fixture("live_data_minimal.json")


@pytest.fixture
def live_data_multi_response():
    return load_fixture("live_data_multi.json")
```

- [ ] **Step 2: Write test_api.py — auth and data fetching tests**

Tests cover:
- `test_authenticate_success` — mock Auth0 token endpoint, verify token stored
- `test_authenticate_bad_credentials` — 401 response raises `GridxAuthenticationError`
- `test_authenticate_connection_error` — timeout raises `GridxConnectionError`
- `test_get_gateways_success` — returns list of system IDs
- `test_get_live_data_success` — returns `GridxSystemData`
- `test_get_live_data_server_error` — 500 raises `GridxApiError`
- `test_token_refresh` — auto-refresh when token near expiry
- `test_auth_cooldown` — second auth attempt within 60s is blocked

Use `aiohttp` test utilities or `aioresponses` for mocking HTTP calls.

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd ~/src/ha-gridx && python -m pytest tests/components/gridx/test_api.py -v
```

- [ ] **Step 4: Implement GridxApi class**

Key methods:
- `__init__(self, session, email, password)` — store params, init token state
- `async authenticate()` — POST to Auth0, store access_token, id_token, refresh_token, expires_at
- `async _ensure_token()` — check expiry, refresh if needed
- `async _refresh_token()` — try refresh_token grant, fall back to full re-auth
- `async async_get_gateways()` — GET /gateways, extract system IDs
- `async async_get_live_data(system_id)` — GET /systems/{id}/live, return parsed `GridxSystemData`

Error mapping:
- `aiohttp.ClientResponseError` with 401/403 → `GridxAuthenticationError`
- `aiohttp.ClientResponseError` with 5xx → `GridxApiError`
- `aiohttp.ClientError`, `asyncio.TimeoutError` → `GridxConnectionError`

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd ~/src/ha-gridx && python -m pytest tests/components/gridx/test_api.py -v
```

- [ ] **Step 6: Lint and commit**

```bash
ruff format custom_components/gridx/api.py tests/components/gridx/test_api.py tests/components/gridx/conftest.py
ruff check custom_components/gridx/api.py tests/components/gridx/test_api.py tests/components/gridx/conftest.py
git add custom_components/gridx/api.py tests/components/gridx/test_api.py tests/components/gridx/conftest.py
git commit -m "Add async API client with auth, gateway discovery, live data"
```

---

## Chunk 3: Config Flow & Coordinator

### Task 6: Config flow with TDD

**Files:**
- Create: `custom_components/gridx/config_flow.py`
- Create: `tests/components/gridx/test_config_flow.py`
- Modify: `custom_components/gridx/__init__.py`

- [ ] **Step 1: Write test_config_flow.py**

Tests cover:
- `test_user_flow_success` — enter credentials → auth succeeds → entry created with system IDs
- `test_user_flow_invalid_auth` — bad credentials → form shows error, retry → success → entry created
- `test_user_flow_cannot_connect` — timeout → form shows error, retry → success → entry created
- `test_user_flow_already_configured` — same account → abort
- `test_reauth_flow` — trigger reauth → enter new password → success → entry updated

Follow HA patterns: mock the API client, test the flow step by step. Config flow tests must end with `CREATE_ENTRY` or `ABORT`.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement config_flow.py**

```python
"""Config flow for gridX integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GridxApi, GridxAuthenticationError, GridxConnectionError
from .const import DOMAIN


class GridxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for gridX."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            api = GridxApi(
                async_get_clientsession(self.hass),
                user_input["email"],
                user_input["password"],
            )
            try:
                await api.authenticate()
                system_ids = await api.async_get_gateways()
            except GridxAuthenticationError:
                errors["base"] = "invalid_auth"
            except GridxConnectionError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(system_ids[0])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="gridX Energy Management",
                    data={
                        "email": user_input["email"],
                        "password": user_input["password"],
                        "system_ids": system_ids,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("email"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
        errors = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if user_input is not None:
            api = GridxApi(
                async_get_clientsession(self.hass),
                entry.data["email"],
                user_input["password"],
            )
            try:
                await api.authenticate()
            except GridxAuthenticationError:
                errors["base"] = "invalid_auth"
            except GridxConnectionError:
                errors["base"] = "cannot_connect"
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, "password": user_input["password"]}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("password"): str}),
            errors=errors,
        )
```

- [ ] **Step 4: Update __init__.py with setup/unload**

```python
"""The gridX Energy Management integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GridxApi
from .const import DOMAIN
from .coordinator import GridxCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = GridxApi(
        async_get_clientsession(hass),
        entry.data["email"],
        entry.data["password"],
    )
    coordinator = GridxCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
```

- [ ] **Step 5: Run tests, lint, commit**

```bash
python -m pytest tests/components/gridx/test_config_flow.py -v
ruff format custom_components/gridx/config_flow.py custom_components/gridx/__init__.py
ruff check custom_components/gridx/config_flow.py custom_components/gridx/__init__.py
git add custom_components/gridx/config_flow.py custom_components/gridx/__init__.py tests/components/gridx/test_config_flow.py
git commit -m "Add config flow with setup, reauth, and validation"
```

### Task 7: Coordinator with TDD

**Files:**
- Create: `custom_components/gridx/coordinator.py`
- Create: `tests/components/gridx/test_coordinator.py`

- [ ] **Step 1: Write test_coordinator.py**

Tests cover:
- `test_coordinator_update_success` — returns dict of system data
- `test_coordinator_connection_error` — raises `UpdateFailed`
- `test_coordinator_auth_error` — triggers reauth
- `test_coordinator_backoff` — after failure, `update_interval` increases
- `test_coordinator_backoff_reset` — after success, interval resets to 60s

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement coordinator.py**

```python
"""DataUpdateCoordinator for gridX."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GridxApi, GridxAuthenticationError, GridxConnectionError, GridxApiError
from .const import DEFAULT_SCAN_INTERVAL, ERROR_SCAN_INTERVAL_BASE, ERROR_SCAN_INTERVAL_MAX
from .models import GridxSystemData

_LOGGER = logging.getLogger(__name__)


class GridxCoordinator(DataUpdateCoordinator[dict[str, GridxSystemData]]):
    """Coordinate gridX API polling."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, api: GridxApi, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="gridX",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            config_entry=entry,
        )
        self.api = api
        self._consecutive_errors = 0

    async def _async_update_data(self) -> dict[str, GridxSystemData]:
        try:
            await self.api._ensure_token()
            system_ids = self.config_entry.data["system_ids"]
            result = {}
            for system_id in system_ids:
                result[system_id] = await self.api.async_get_live_data(system_id)
            self._consecutive_errors = 0
            self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
            return result
        except GridxAuthenticationError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except (GridxConnectionError, GridxApiError) as err:
            self._consecutive_errors += 1
            backoff = min(
                ERROR_SCAN_INTERVAL_BASE * (2 ** (self._consecutive_errors - 1)),
                ERROR_SCAN_INTERVAL_MAX,
            )
            self.update_interval = timedelta(seconds=backoff)
            raise UpdateFailed(f"Error fetching data: {err}") from err
```

- [ ] **Step 4: Run tests, lint, commit**

```bash
python -m pytest tests/components/gridx/test_coordinator.py -v
ruff format custom_components/gridx/coordinator.py tests/components/gridx/test_coordinator.py
ruff check custom_components/gridx/coordinator.py tests/components/gridx/test_coordinator.py
git add custom_components/gridx/coordinator.py tests/components/gridx/test_coordinator.py
git commit -m "Add DataUpdateCoordinator with exponential backoff"
```

---

## Chunk 4: Sensor Platform

### Task 8: Entity descriptions and sensor platform

**Files:**
- Create: `custom_components/gridx/sensor.py`
- Create: `tests/components/gridx/test_sensor.py`

- [ ] **Step 1: Write test_sensor.py**

Tests cover:
- `test_system_sensors_created` — all 17 system sensors created with correct values
- `test_battery_device_created` — battery device exists with 7 entities
- `test_heat_pump_device_created` — HP device with 2 entities, SG Ready shows "AUTO"
- `test_no_appliance_devices_when_empty` — minimal fixture creates no appliance devices
- `test_multi_appliance_naming` — multi fixture: "Battery" + "Battery 2", "Heat Pump" + "Heat Pump 2"
- `test_diagnostic_entities` — battery capacity/nominal are diagnostic category
- `test_display_precision` — power sensors show 0 decimals, % show 1 decimal
- `test_rate_sensors_percentage` — self_consumption_rate of 0.88 displays as 88.0%

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement sensor.py**

Define:
- `GridxSystemSensorDescription` — with `value_fn: Callable[[GridxSystemData], StateType]`
- `GridxApplianceSensorDescription` — with `value_fn: Callable[[Any], StateType]`
- `SYSTEM_SENSOR_DESCRIPTIONS` — list of 17 system-level descriptions
- `BATTERY_SENSOR_DESCRIPTIONS` — 7 per battery
- `HEAT_PUMP_SENSOR_DESCRIPTIONS` — 2 per heat pump
- `EV_CHARGER_SENSOR_DESCRIPTIONS` — 6 per EV charger
- `HEATER_SENSOR_DESCRIPTIONS` — 2 per heater
- `GridxSystemSensorEntity(CoordinatorEntity, SensorEntity)` — reads from coordinator data
- `GridxApplianceSensorEntity(CoordinatorEntity, SensorEntity)` — reads appliance by ID
- `async_setup_entry()` — creates entities based on coordinator data

Rate sensors (self_consumption_rate, etc.) multiply API value by 100 in their `value_fn`.

- [ ] **Step 4: Run tests, lint, commit**

```bash
python -m pytest tests/components/gridx/test_sensor.py -v
ruff format custom_components/gridx/sensor.py tests/components/gridx/test_sensor.py
ruff check custom_components/gridx/sensor.py tests/components/gridx/test_sensor.py
git add custom_components/gridx/sensor.py tests/components/gridx/test_sensor.py
git commit -m "Add sensor platform with system and appliance entities"
```

---

## Chunk 5: Diagnostics, README, Final Polish

### Task 9: Diagnostics

**Files:**
- Create: `custom_components/gridx/diagnostics.py`
- Create: `tests/components/gridx/test_diagnostics.py`

- [ ] **Step 1: Write test_diagnostics.py**

Test that diagnostics output contains coordinator data and redacts sensitive fields (email, password, tokens).

- [ ] **Step 2: Implement diagnostics.py**

```python
"""Diagnostics for gridX integration."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

REDACT_KEYS = {"email", "password", "access_token", "refresh_token", "id_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return async_redact_data(
        {
            "config_entry": entry.as_dict(),
            "coordinator_data": {
                system_id: {
                    "production": data.production,
                    "consumption": data.consumption,
                    "grid": data.grid,
                    "photovoltaic": data.photovoltaic,
                    "batteries": len(data.batteries),
                    "heat_pumps": len(data.heat_pumps),
                    "ev_charging_stations": len(data.ev_charging_stations),
                    "heaters": len(data.heaters),
                }
                for system_id, data in coordinator.data.items()
            },
        },
        REDACT_KEYS,
    )
```

- [ ] **Step 3: Run tests, lint, commit**

```bash
python -m pytest tests/components/gridx/test_diagnostics.py -v
ruff format custom_components/gridx/diagnostics.py tests/components/gridx/test_diagnostics.py
ruff check custom_components/gridx/diagnostics.py tests/components/gridx/test_diagnostics.py
git add custom_components/gridx/diagnostics.py tests/components/gridx/test_diagnostics.py
git commit -m "Add diagnostics with credential redaction"
```

### Task 10: README and final files

**Files:**
- Create: `README.md`
- Create: `custom_components/gridx/icons.json`

- [ ] **Step 1: Create icons.json**

```json
{
  "entity": {
    "sensor": {
      "sg_ready_state": {
        "default": "mdi:heat-pump"
      }
    }
  }
}
```

- [ ] **Step 2: Create README.md**

Cover:
- What it is (gridX / E.ON Home energy management for HA)
- Also known as: Viessmann Gridbox, E.ON Home Manager
- Installation via HACS (custom repository)
- Configuration (add integration, enter email/password)
- What devices/entities are created
- Credits to unl0ck with links
- License

- [ ] **Step 3: Run full test suite**

```bash
cd ~/src/ha-gridx && python -m pytest tests/ -v --timeout=10
```

All tests must pass.

- [ ] **Step 4: Lint everything**

```bash
ruff format custom_components/ tests/
ruff check custom_components/ tests/
```

- [ ] **Step 5: Commit and verify**

```bash
git add README.md custom_components/gridx/icons.json
git commit -m "Add README, icons, finalize integration"
```

### Task 11: Create GitHub repo and push

- [ ] **Step 1: Create repo on GitHub**

```bash
cd ~/src/ha-gridx && gh repo create lackas/ha-gridx --public --source=. --push
```

- [ ] **Step 2: Verify repo is accessible**

```bash
gh repo view lackas/ha-gridx
```
