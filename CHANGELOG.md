# Changelog

All notable changes to this project will be documented in this file.

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
