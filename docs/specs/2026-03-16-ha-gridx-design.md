# ha-gridx: Native Home Assistant Integration for gridX Energy Management

## Overview

A HACS-compatible Home Assistant integration for gridX-based energy management systems. Polls the gridX cloud API for live energy data and exposes it as HA entities with proper device grouping.

Also known as: Viessmann Gridbox, E.ON Home Manager, gridX energy management.

Inspired by [unl0ck's Viessmann Gridbox Connector add-on](https://github.com/unl0ck/homeassistant-addon-viessmann-gridbox) and [gridx-connector library](https://github.com/unl0ck/gridx-connector). Clean-room implementation — no code copied.

## Scope

- Live energy data only (no historical — HA handles its own statistics)
- E.ON Home realm only (Viessmann realm dropped; architecture allows adding it later)
- Cloud polling at 60s intervals
- HACS distribution as custom repository

## Repository Structure

```
ha-gridx/
├── custom_components/
│   └── gridx/
│       ├── __init__.py           # Entry setup/unload
│       ├── api.py                # Async API client (Auth0 + gridX)
│       ├── config_flow.py        # Credentials form + reauth
│       ├── const.py              # Constants, defaults
│       ├── coordinator.py        # DataUpdateCoordinator
│       ├── models.py             # Dataclasses (no HA dependency)
│       ├── sensor.py             # Entity descriptions + platform setup
│       ├── diagnostics.py        # Config entry diagnostics
│       ├── manifest.json         # Integration + HACS metadata
│       ├── icons.json            # Custom icons
│       ├── strings.json          # Translations
│       └── quality_scale.yaml    # Quality checklist
├── tests/
│   └── components/
│       └── gridx/
│           ├── conftest.py
│           ├── test_api.py
│           ├── test_models.py
│           ├── test_config_flow.py
│           ├── test_coordinator.py
│           ├── test_sensor.py
│           ├── test_diagnostics.py
│           └── fixtures/
│               ├── live_data.json
│               ├── live_data_minimal.json
│               ├── live_data_multi.json
│               └── gateways.json
├── hacs.json
├── LICENSE                       # Apache 2.0
└── README.md
```

Key boundaries:
- `api.py` — pure async, no HA imports, uses `aiohttp.ClientSession` passed in
- `models.py` — pure dataclasses, no HA dependency
- These two files form the pluggable extraction point for a standalone library

## Authentication

The gridX API uses Auth0 with a Resource Owner Password grant (not standard OAuth2 Authorization Code flow). The Auth0 `/authorize` endpoint returns 403 for the E.ON client — browser-based OAuth is not available.

### Auth0 Configuration (E.ON Home)

| Parameter | Value |
|-----------|-------|
| Token URL | `https://gridx.eu.auth0.com/oauth/token` |
| Grant type | `http://auth0.com/oauth/grant-type/password-realm` |
| Client ID | `mG0Phmo7DmnvAqO7p6B0WOYBODppY3cc` |
| Client secret | (empty) |
| Audience | `my.gridx` |
| Realm | `eon-home-authentication-db` |
| Scope | `email openid offline_access` |

### Token Handling

- The `offline_access` scope requests a refresh token from Auth0
- Tokens stored with `expires_at` and `refresh_token`
- 60s before expiry: attempt Auth0 `refresh_token` grant
- If refresh token grant fails: re-authenticate with stored email/password (full password-realm grant)
- If re-auth also fails: raise `GridxAuthenticationError` → triggers HA reauth flow
- Auth cooldown: no more than one auth attempt per 60s (protect Auth0 from spam)

## API Client (`api.py`)

```python
class GridxApi:
    def __init__(self, session: aiohttp.ClientSession, email: str, password: str)
    async def authenticate(self) -> None
    async def async_get_gateways(self) -> list[dict]
    async def async_get_live_data(self, system_id: str) -> GridxSystemData
```

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST https://gridx.eu.auth0.com/oauth/token` | Authentication |
| `GET https://api.gridx.de/gateways` | Discover systems |
| `GET https://api.gridx.de/systems/{id}/live` | Live energy data |

### Error Hierarchy

```
GridxError (base)
├── GridxAuthenticationError    → 401/403, bad credentials
├── GridxConnectionError        → timeout, DNS, connection refused
└── GridxApiError               → 5xx, unexpected response
```

No retries within the client. The coordinator handles all backoff logic.

## Data Models (`models.py`)

Pure dataclasses, no HA dependency.

```python
@dataclass
class GridxBattery:
    appliance_id: str
    state_of_charge: float      # 0.0-1.0
    capacity: float             # Wh
    nominal_capacity: float     # Wh
    power: float                # W
    remaining_charge: float     # Wh
    charge: float               # W
    discharge: float            # W

@dataclass
class GridxHeatPump:
    appliance_id: str
    power: float                # W
    sg_ready_state: str         # "AUTO", "BOOST", etc.

@dataclass
class GridxEVChargingStation:
    appliance_id: str
    power: float                # W
    state_of_charge: float      # 0.0-1.0
    current_l1: float           # A
    current_l2: float           # A
    current_l3: float           # A
    reading_total: float        # kWh cumulative

@dataclass
class GridxHeater:
    appliance_id: str
    power: float                # W
    temperature: float          # °C

@dataclass
class GridxSystemData:
    production: float           # W
    photovoltaic: float         # W
    consumption: float          # W
    total_consumption: float    # W
    grid: float                 # W (positive = importing from grid, negative = exporting)
    self_consumption: float     # W
    self_supply: float          # W
    self_consumption_rate: float    # 0.0-1.0 from API, displayed as % (×100)
    self_sufficiency_rate: float    # 0.0-1.0 from API, displayed as % (×100)
    direct_consumption_household: float
    direct_consumption_heat_pump: float
    direct_consumption_ev: float
    direct_consumption_heater: float
    direct_consumption_rate: float
    heat_pump: float            # W aggregate
    grid_meter_reading_negative: float  # Wh cumulative (export)
    grid_meter_reading_positive: float  # Wh cumulative (import)
    measured_at: datetime       # ISO 8601 timestamp from API, parsed
    batteries: list[GridxBattery]
    heat_pumps: list[GridxHeatPump]
    ev_charging_stations: list[GridxEVChargingStation]
    heaters: list[GridxHeater]
```

`parse_live_data(data: dict) -> GridxSystemData` handles camelCase→snake_case and defaults missing fields to 0.0 / empty lists. Unknown fields are silently ignored.

## Config Flow (`config_flow.py`)

### Setup Flow

1. User enters email + password
2. Validate: call `authenticate()` + `async_get_gateways()`
3. Success → create config entry, unique ID = first system ID
4. Auth failure → "Invalid credentials" error
5. Connection error → "Cannot connect" error
6. All systems from the account are auto-added (single config entry)

### Reauth Flow

- Triggered by coordinator on `GridxAuthenticationError`
- Shows prefilled email, asks for new password
- Validates and updates config entry

### No Options Flow

Polling interval is fixed at 60s. Options flow can be added later if needed.

## Coordinator (`coordinator.py`)

`GridxCoordinator(DataUpdateCoordinator[dict[str, GridxSystemData]])`

Data keyed by system ID. Supports multiple systems from one account.

### Polling & Error Handling

| Scenario | Action |
|----------|--------|
| Normal poll | Every 60s, returns typed data |
| Connection error / 5xx | Raise `UpdateFailed`, entities go unavailable |
| Backoff | Dynamically set `update_interval`: 120s → 240s → 480s → cap at 900s. Reset to 60s on success. Track consecutive failure count in coordinator. |
| Auth error (401/403) | Call `config_entry.async_start_reauth()`, stop polling |
| First setup failure | Raise `ConfigEntryNotReady` (HA retries automatically) |

### API Respect

- No immediate retries on any exception
- Exponential backoff with 15-minute cap
- Auth cooldown (max 1 attempt per 60s) in API client
- Single shared `aiohttp` session (connection pooling)

## Devices & Entities (`sensor.py`)

### Device Hierarchy

| Device | Created when | Identifiers | Model |
|--------|-------------|-------------|-------|
| gridX (system) | Always | `(gridx, {system_id})` | "gridX Gateway" |
| Battery | `batteries` non-empty | `(gridx, {appliance_id})` | "Battery" |
| Heat Pump | `heat_pumps` non-empty | `(gridx, {appliance_id})` | "Heat Pump" |
| EV Charger | `ev_charging_stations` non-empty | `(gridx, {appliance_id})` | "EV Charger" |
| Heater | `heaters` non-empty | `(gridx, {appliance_id})` | "Heater" |

### Appliance Naming

- 1 appliance: `heat_pump` → device "Heat Pump"
- 2+ appliances: `heat_pump` → "Heat Pump", `heat_pump_2` → "Heat Pump 2"

### System Entities (on system device)

| Entity | Unit | Device class | State class | Category |
|--------|------|-------------|-------------|----------|
| Production | W | power | measurement | — |
| Photovoltaic | W | power | measurement | — |
| Consumption | W | power | measurement | — |
| Total Consumption | W | power | measurement | — |
| Grid | W | power | measurement | — |
| Self Consumption | W | power | measurement | — |
| Self Supply | W | power | measurement | — |
| Self Consumption Rate | % | — | measurement | — |
| Self Sufficiency Rate | % | — | measurement | — |
| Direct Consumption Household | W | power | measurement | — |
| Direct Consumption Heat Pump | W | power | measurement | — |
| Direct Consumption EV | W | power | measurement | — |
| Direct Consumption Heater | W | power | measurement | — |
| Direct Consumption Rate | % | — | measurement | hidden default |
| Heat Pump (aggregate) | W | power | measurement | — |
| Grid Meter Export | Wh | energy | total_increasing | — |
| Grid Meter Import | Wh | energy | total_increasing | — |

### Battery Entities (per battery device)

| Entity | Unit | Device class | State class | Category |
|--------|------|-------------|-------------|----------|
| State of Charge | % | battery | measurement | — |
| Power | W | power | measurement | — |
| Charge | W | power | measurement | — |
| Discharge | W | power | measurement | — |
| Remaining Charge | Wh | energy_storage | measurement | — |
| Capacity | Wh | energy_storage | measurement | diagnostic |
| Nominal Capacity | Wh | energy_storage | measurement | diagnostic |

### Heat Pump Entities (per heat pump device)

| Entity | Unit | Device class | State class | Category |
|--------|------|-------------|-------------|----------|
| Power | W | power | measurement | — |
| SG Ready State | — | enum | — | — |

SG Ready State options: `["AUTO", "BOOST", "OFF", "BLOCK"]` (standard SG Ready states from the gridX API). Unknown values passed through as-is.

### EV Charger Entities (per charger device)

| Entity | Unit | Device class | State class | Category |
|--------|------|-------------|-------------|----------|
| Power | W | power | measurement | — |
| State of Charge | % | battery | measurement | — |
| Current L1 | A | current | measurement | — |
| Current L2 | A | current | measurement | — |
| Current L3 | A | current | measurement | — |
| Total Energy | kWh | energy | total_increasing | — |

### Heater Entities (per heater device)

| Entity | Unit | Device class | State class | Category |
|--------|------|-------------|-------------|----------|
| Power | W | power | measurement | — |
| Temperature | °C | temperature | measurement | — |

### Entity Description Architecture

**System entities** use a description with a value extractor from `GridxSystemData`:

```python
@dataclass(frozen=True)
class GridxSystemSensorDescription(SensorEntityDescription):
    value_fn: Callable[[GridxSystemData], StateType]
```

**Appliance entities** use a generic description parameterized by appliance type:

```python
@dataclass(frozen=True)
class GridxApplianceSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Any], StateType]  # receives GridxBattery, GridxHeatPump, etc.
```

**How appliance entities find their data:**

Each appliance entity stores its `appliance_id` and `system_id`. On coordinator update:
1. Entity reads `coordinator.data[system_id]` → `GridxSystemData`
2. Looks up its appliance in the corresponding list (e.g., `data.batteries`)
3. Matches by `appliance_id`
4. Calls `description.value_fn(appliance)` to extract the value

**Platform setup (`async_setup_entry`):**
1. Read initial coordinator data
2. For each system: create system entities from `SYSTEM_SENSOR_DESCRIPTIONS`
3. For each appliance array (batteries, heat_pumps, etc.):
   - Skip if array is empty
   - For each appliance: create entities from the corresponding description list
   - First appliance: no suffix in device name. Second+: `_2`, `_3`
4. Register a coordinator listener to detect newly appearing appliances on future updates

**Multi-system disambiguation:**
Each entity's unique ID includes the system ID: `{system_id}_{entity_key}` for system entities, `{appliance_id}_{entity_key}` for appliance entities. Device names include the system name if multiple systems exist.

### Display Precision

| Sensor type | Precision |
|------------|-----------|
| Power (W) | 0 decimals |
| Energy (Wh, kWh) | 0 decimals |
| Percentage (%) | 1 decimal |
| Temperature (°C) | 1 decimal |
| Current (A) | 1 decimal |

Set via `suggested_display_precision` on entity descriptions.

## HACS Compatibility

**`hacs.json`:**
```json
{
  "name": "gridX Energy Management",
  "render_readme": true
}
```

**`manifest.json`:**
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

Installation: add `lackas/ha-gridx` as custom repository in HACS, category "Integration".

## Testing

All API calls mocked via `aiohttp` fixtures. No real network calls.

### Test Files

| File | Covers |
|------|--------|
| `test_api.py` | Auth success, token refresh, bad credentials, timeout, 5xx, auth cooldown |
| `test_models.py` | Full parsing, missing fields default to 0, empty arrays, unknown fields ignored |
| `test_config_flow.py` | Setup happy path, bad credentials error, connection error, reauth flow |
| `test_coordinator.py` | Normal update, `UpdateFailed` on connection error, reauth trigger, backoff |
| `test_sensor.py` | Correct values, device assignment, dynamic naming (1 vs 2+), diagnostic entities, no entities for empty arrays |
| `test_diagnostics.py` | Diagnostics dump with redacted credentials |

### Diagnostics Redaction

Fields redacted in diagnostics output: `email`, `password`, `access_token`, `refresh_token`, `id_token`, `appliance_id` (partial). System IDs shown in full (needed for debugging).

### Test Fixtures

| File | Purpose |
|------|---------|
| `live_data.json` | Full response with battery, heat pump (based on real system) |
| `live_data_minimal.json` | No battery, no heat pump, no EV — base sensors only |
| `live_data_multi.json` | 2 batteries, 2 heat pumps — tests dynamic naming |
| `gateways.json` | Gateway discovery response |

## Future Considerations

- **Viessmann realm:** Add config flow step to select OEM, swap Auth0 constants
- **Options flow:** User-configurable polling interval
- **Standalone lib extraction:** `api.py` + `models.py` have no HA dependency, can become `gridx-connector` v2
- **HA Core submission:** If quality and test coverage are sufficient, consider upstreaming
