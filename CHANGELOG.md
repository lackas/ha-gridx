# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.1.0] - 2026-06-16

### Added

- **Multi-provider support.** The config flow now lets you pick the portal you log in through. Supported OEMs: 1KOMMA5°, EFA-Home, empavo, enviaM, E.ON FEH (NL), E.ON Home Manager (default), EVM, EWV, Giedorf, Greenblocks, Heimwatt, hemos, **IBC HomeOne Hub**, KlarSolar, LEW, Octopus Energy, PV Green, Stadtwerke Norderstedt, upVolt, Viessmann GridBox (legacy), Zero 1.

  Background: the gridX backend (`api.gridx.de`) is shared across 21+ white-labeled OEM portals. Every portal uses the same Auth0 tenant — only the `client_id` and `realm` differ. Until this release, the integration hard-coded the E.ON Home values, so users of other portals (like IBC HomeOne) got a 401 at login even though their data was reachable. Picking the right provider in the config flow routes the Auth0 password-realm grant against the correct user pool.

  Existing entries default to E.ON Home Manager — no migration or reauthentication required.

- `scripts/update_providers.py` extracts the OEM list verbatim from the live multi-tenant SPA bundle at `homeone.gridx.de`. A weekly GitHub Action re-runs it with `--check` so stale `client_id`s surface as CI failures rather than user reports.

## [1.0.16] - 2026-06-09

### Fixed

- Sensor platform setup no longer crashes with `TypeError: 'NoneType' object is not iterable` when the historical-data API call fails on integration startup. Historical entities are now built from the configured `system_ids` rather than from `coordinator.data`, so they appear as "unknown" until the next successful poll instead of preventing platform setup entirely. The historical sensor's `native_value` also tolerates `coordinator.data is None`.

### Added

- Now available directly in HACS default — no custom repository setup needed. Just search "gridX Energy Management" in HACS to install. (This was already true since the HACS default merge on 2026-05-15 but was never moved out of the changelog's `[Unreleased]` section.)

## [1.0.15] - 2026-06-05

### Fixed

- Transient DNS / connection timeouts to `gridx.eu.auth0.com` and `api.gridx.de` no longer immediately fail the coordinator update. The API client now retries up to 3 times with exponential backoff (1s, 2s, 4s) on `TimeoutError` and `aiohttp.ClientConnectionError` before bubbling up as `GridxConnectionError`. HTTP-level errors (4xx, 5xx) are still raised immediately without retry.

  Background: `gridx.eu.auth0.com` resolves via a 3-level CNAME chain (Auth0 → auth0edge → Cloudflare CDN) with TTLs as short as 2 seconds on intermediate hops, making it noticeably more brittle to DNS hiccups than direct-A-record cloud APIs. Brief retries absorb most transient failures.

  Refresh-token grants are intentionally NOT wrapped in this retry — Auth0 rotates refresh tokens by default, and replaying a refresh token that was consumed by the server (but the response was lost in transit) can trigger refresh-token-reuse detection and invalidate the entire token family. On transient refresh failures, the integration falls back to a full password re-auth (which IS retried, because it's idempotent).

## [1.0.14] - 2026-04-20

### Fixed

- Battery charge/discharge energy sensors stuck at 0 kWh
- Battery energy sensors no longer appear as separate devices — they now live under the existing Battery device

## [1.0.13] - 2026-04-01

### Added

- Built-in energy accumulator sensor for heaters: **Heater energy** (kWh)

## [1.0.12] - 2026-04-01

### Added

- Built-in energy accumulator sensors for batteries: **Battery charge energy** and **Battery discharge energy** (kWh), always-on like the existing heat pump and photovoltaic energy sensors

## [1.0.11] - 2026-04-01

### Added

- Historical energy sensors (disabled by default): battery charge today, battery discharge today, heat pump energy today, direct consumption heat pump today — all in Wh, sourced from the gridX `/historical` API endpoint and updated hourly. Enable them in Settings → Devices & Services → gridX.

## [1.0.10] - 2026-03-25

### Fixed

- Fix grid meter reading unit: gridX API returns values in Ws (watt-seconds), not Wh — readings were 3600x too high, inflating Energy Dashboard statistics

### ⚠️ Action required after update

The corrected values will be 3600x smaller. HA will interpret this as a meter reset and add phantom energy to the statistics. To fix: go to **Developer Tools → Statistics**, find `gridx_grid_meter_import` and `gridx_grid_meter_export`, and click "Fix issue" to reset their accumulated values.

## [1.0.9] - 2026-03-20

### Fixed

- Fix energy sensor names all showing as "gridX Energy" instead of distinct names (missing translations in en.json)

## [1.0.8] - 2026-03-20

### Added

- System-level energy sensors (kWh) for the Energy Dashboard: photovoltaic, production, consumption, total consumption, grid import/export, self consumption, self supply

## [1.0.7] - 2026-03-18

### Fixed

- Fix heat pump energy sensor permanently unavailable (was using `RestoreEntity` instead of `RestoreSensor`, causing `async_get_last_sensor_data` to fail silently)

## [1.0.6] - 2026-03-18

### Fixed

- Fix SG Ready states: use correct values from gridX API (`UNKNOWN`, `OFF`, `AUTO`, `RECOMMEND_ON`, `ON`) instead of wrong placeholder values
- Handle unknown future SG Ready states gracefully (show as unavailable instead of crashing)
- Add state translations for SG Ready sensor

## [1.0.4] - 2026-03-17

### Fixed

- Retry authentication on 401 instead of immediately triggering reauth flow

## [1.0.3] - 2026-03-17

### Added

- HACS and hassfest validation workflows
- Brand assets (icon, logo)
- Update instructions in README

### Fixed

- Prefix appliance device names with "gridX" for unique entity IDs
- Sort manifest keys per hassfest requirements

## [1.0.2] - 2026-03-17

### Added

- Initial release: sensors for PV, battery, grid, consumption, heat pump, EV charger, heater
- Auth0 authentication with token refresh and exponential backoff
- Device-per-appliance grouping
- Diagnostics with credential redaction
- HACS compatible
