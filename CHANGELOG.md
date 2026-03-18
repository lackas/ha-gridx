# Changelog

All notable changes to this project will be documented in this file.

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
