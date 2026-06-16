# CLAUDE.md

## Project Overview

ha-gridx is a HACS-compatible Home Assistant integration for gridX-based energy management systems (E.ON Home Manager, formerly Viessmann Gridbox).

- **Design spec**: `docs/specs/2026-03-16-ha-gridx-design.md`
- **Domain**: `gridx`
- **Distribution**: HACS default (merged 2026-05-15 via hacs/default#6353)

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

## Releasing

1. Make sure tests + ruff are clean:
   `~/src/venv/ha/bin/python -m pytest tests/components/gridx/ --timeout=10 -q`
   `~/src/venv/ha/bin/ruff format custom_components/gridx/ tests/ && ~/src/venv/ha/bin/ruff check custom_components/gridx/ tests/`
2. Bump `version` in `custom_components/gridx/manifest.json` (semver: patch for bug fixes, minor for new sensors/features).
3. Update `CHANGELOG.md`: insert a new `## [1.x.x] - YYYY-MM-DD` section above the previous release and move/pull relevant items into it. Keep `## [Unreleased]` as an empty header on top. Carry forward any `[Unreleased]` items that should ship.
4. **Show the commit message and GitHub release notes to the user for approval before publishing** (per the public-communication policy — releases are public). Only continue once approved.
5. Stage exactly the touched files and commit:
   `git add custom_components/gridx/manifest.json CHANGELOG.md ...` then `git commit -m "..."`.
6. Push: `git push origin main`.
7. Tag and push the tag: `git tag v1.x.x && git push origin v1.x.x`.
8. Create the GitHub release: `gh release create v1.x.x --title "v1.x.x" --notes-file <(...)` — use the approved notes verbatim. HACS picks up the tagged release automatically; no further action.

HACS picks up new releases automatically — no PR needed (the hacs/default registration was a one-time step).

### CI Checks (must pass before releasing)

- **CI** (`ci.yml`) — ruff lint + pytest
- **HACS Validation** (`hacs.yml`) — validates HACS structure
- **Hassfest** (`hassfest.yml`) — validates HA manifest (keys must be sorted: domain, name, then alphabetical)

### Manifest Key Order

hassfest requires: `domain` first, `name` second, then all other keys alphabetically sorted.

## Key Design Decisions

- **Historical sensors are opt-in** — 4 historical system sensors (battery charge/discharge, heat pump energy, direct-consumption heat pump) are registered but `entity_registry_enabled_default=False`; HA's own statistics from live sensors are the default path. Historical coordinator failures must not block setup or sensor creation — see `__init__.py` (swallows first-refresh exception) and `_build_historical_entities` in `sensor.py` (builds entities from `entry.data["system_ids"]`, not `coordinator.data`).
- **E.ON only** — Viessmann realm dropped; architecture supports adding it later via constants
- **API respect** — exponential backoff (120s → 15min cap), auth cooldown (max 1 attempt/60s), no immediate retries
- **Device-per-appliance** — batteries, heat pumps, EV chargers, heaters each get their own HA device
- **Dynamic naming** — first appliance: no suffix, second+: `_2`, `_3`
- **Clean-room** — independently implemented as a native HA integration
