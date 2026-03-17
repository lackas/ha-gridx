# ha-gridx

Home Assistant integration for gridX-based energy management systems.

**Also known as:** E.ON Home Manager, Viessmann Gridbox

## Features

- Live energy data polling (60s intervals)
- Automatic device creation for batteries, heat pumps, EV chargers, and heaters
- Proper state_class metadata for HA Energy dashboard compatibility
- SG Ready state monitoring for heat pumps
- Cumulative grid meter readings (import/export)
- Exponential backoff on API errors (respects the API)

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots menu → Custom repositories
4. Add `lackas/ha-gridx` with category "Integration"
5. Install "gridX Energy Management"
6. Restart Home Assistant

### Manual

Copy the `custom_components/gridx` folder to your Home Assistant `custom_components` directory.

## Configuration

1. Go to Settings → Devices & Services → Add Integration
2. Search for "gridX"
3. Enter your E.ON Home / gridX account email and password

## Updating

1. Open HACS → Integrations → gridX Energy Management
2. Click "Update information" to refresh repository data
3. Click "Redownload" and confirm
4. Go to Settings → System → a "Restart required" repair will appear — click Restart

## Devices & Entities

The integration creates devices based on your system:

| Device | Entities | Created when |
|--------|---------|-------------|
| gridX | 17 sensors (power flows, rates, meter readings) | Always |
| gridX Battery | 7 sensors (SoC, power, charge/discharge, capacity) | If battery present |
| gridX Heat Pump | 2 sensors (power, SG Ready state) | If heat pump present |
| gridX EV Charger | 6 sensors (power, SoC, currents, total energy) | If EV charger present |
| gridX Heater | 2 sensors (power, temperature) | If heater present |

Multiple appliances of the same type are supported (e.g., "gridX Battery" and "gridX Battery 2").

## Disclaimer

This is an unofficial, community-maintained integration. It is not affiliated with, endorsed by, or supported by gridX GmbH or E.ON SE.

## Credits

Inspired by and based on the work of:
- [unl0ck's Viessmann Gridbox Connector add-on](https://github.com/unl0ck/homeassistant-addon-viessmann-gridbox)
- [unl0ck's gridx-connector library](https://github.com/unl0ck/gridx-connector)

This is a clean-room reimplementation as a native HA integration. No code was copied from the original projects.

## License

Apache License 2.0 — see [LICENSE](LICENSE)
