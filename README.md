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

## Energy Sensors (Wh) via HA Helpers

The gridX live API provides **power values (W)** for battery charge/discharge and heat pump consumption. If you need cumulative **energy sensors (Wh/kWh)** — e.g. for custom dashboards or tracking daily usage — you can derive them using Home Assistant's built-in [Riemann Sum Integral helper](https://www.home-assistant.io/integrations/integration/).

Add the following to your `configuration.yaml`:

```yaml
sensor:
  - platform: integration
    source: sensor.gridx_battery_charge
    name: "Battery Charge Energy"
    unit_prefix: k
    round: 2
    method: trapezoidal

  - platform: integration
    source: sensor.gridx_battery_discharge
    name: "Battery Discharge Energy"
    unit_prefix: k
    round: 2
    method: trapezoidal

  - platform: integration
    source: sensor.gridx_heat_pump_power
    name: "Heat Pump Energy Consumption"
    unit_prefix: k
    round: 2
    method: trapezoidal
```

> **Note:** Replace the `source` entity IDs with the actual entity IDs from your setup (visible in Settings → Devices & Services → gridX). The sensors above assume default entity naming.

If you want daily/monthly totals that reset at midnight, add a [Utility Meter helper](https://www.home-assistant.io/integrations/utility_meter/) on top of each integration sensor.

> **Why not built into the integration?** The gridX live API only exposes instantaneous power (W) for these values — not cumulative energy meters. Only the grid import/export (`gridMeterReadingPositive`/`gridMeterReadingNegative`) are true hardware meter readings. Historical energy data from the gridX API is planned as a future feature.

## Disclaimer

This is an unofficial, community-maintained integration. It is not affiliated with, endorsed by, or supported by gridX GmbH or E.ON SE.

## Credits

Inspired by and based on the work of:
- [unl0ck's Viessmann Gridbox Connector add-on](https://github.com/unl0ck/homeassistant-addon-viessmann-gridbox)
- [unl0ck's gridx-connector library](https://github.com/unl0ck/gridx-connector)

This is a clean-room reimplementation as a native HA integration. No code was copied from the original projects.

## License

Apache License 2.0 — see [LICENSE](LICENSE)
