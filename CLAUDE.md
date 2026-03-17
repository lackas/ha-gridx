# CLAUDE.md

## Project Overview

ha-gridx is a HACS-compatible Home Assistant integration for gridX-based energy management systems (E.ON Home Manager, formerly Viessmann Gridbox).

- **Design spec**: `docs/specs/2026-03-16-ha-gridx-design.md`
- **Domain**: `gridx`
- **Distribution**: HACS custom repository

## Architecture

- `api.py` + `models.py` — no HA imports, pure async + dataclasses (future lib extraction point)
- `coordinator.py` — single DataUpdateCoordinator, polls `/live` every 60s
- `sensor.py` — entity descriptions, device-per-appliance pattern
- Auth: Auth0 password-realm grant (not standard OAuth2), E.ON Home realm only

## Development

### Virtual Environment

```bash
~/src/venv/ha/bin/python3
~/src/venv/ha/bin/pytest
```

### Running Tests

```bash
# All tests
~/src/venv/ha/bin/python -m pytest tests/components/gridx/ -v

# Single test file
~/src/venv/ha/bin/python -m pytest tests/components/gridx/test_models.py -v

# Single test
~/src/venv/ha/bin/python -m pytest tests/components/gridx/test_models.py::TestParseFullResponse -v

# With timeout (recommended)
~/src/venv/ha/bin/python -m pytest tests/components/gridx/ -v -x --timeout=10
```

Note: Use `~/src/venv/ha/bin/python -m pytest` (not bare `pytest`) to ensure the HA venv with all dependencies is used. The system Python does not have pytest or HA installed.

### Linting

```bash
~/src/venv/ha/bin/ruff format custom_components/gridx/ tests/
~/src/venv/ha/bin/ruff check custom_components/gridx/ tests/
```

## Key Design Decisions

- **No historical data** — HA handles its own statistics from live sensor data
- **E.ON only** — Viessmann realm dropped; architecture supports adding it later via constants
- **API respect** — exponential backoff (120s → 15min cap), auth cooldown (max 1 attempt/60s), no immediate retries
- **Device-per-appliance** — batteries, heat pumps, EV chargers, heaters each get their own HA device
- **Dynamic naming** — first appliance: no suffix, second+: `_2`, `_3`
- **Clean-room** — inspired by unl0ck's work, no code copied

## Attribution

Inspired by [unl0ck's Viessmann Gridbox Connector](https://github.com/unl0ck/homeassistant-addon-viessmann-gridbox) and [gridx-connector](https://github.com/unl0ck/gridx-connector).
