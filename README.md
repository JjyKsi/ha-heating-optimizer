# Heating Optimizer

Custom Home Assistant integration that fetches quarter-hour electricity prices from [porssisahko.net v2](https://api.porssisahko.net/) and exposes them as sensor data for automations, dashboards, or further processing.

## Features
- Config-entry based setup that creates a single integration instance.
- Price polling via a `DataUpdateCoordinator` with cached API responses.
- Sensor `sensor.heating_optimizer_current_price` showing the current price (c/kWh) plus upcoming slots, min/max/average helpers, and attribution.
- Automatic day/night delivery adders (2.55 ¢ between 07:00–22:00, 1.12 ¢ overnight) applied to every slot.
- Binary sensors that reveal whether a cheaper or more expensive slot exists within horizons from 15 minutes up to 24 hours.
- HACS-ready layout (`custom_components/heating_optimizer`, `hacs.json`, rendered README).
- Test harness built on `pytest-homeassistant-custom-component`.

## Installation
1. Zip the repository contents or publish it to GitHub.
2. In Home Assistant, open HACS → Integrations → ⋮ → Custom repositories.
3. Add the repository URL, choose the **Integration** category, and install *Heating Optimizer*.
4. Restart Home Assistant and add the integration via *Settings → Devices & services → Add integration*.

## Configuration
Only one instance is supported. Starting the config flow immediately creates the integration entry—no additional fields are required.

## Development
- Create a Python 3.11+ environment.
- Install development dependencies with `pip install -r requirements_dev.txt`.
- Run tests with `pytest` (or `poetry run pytest` if you manage dependencies with Poetry).
- Update the manifest version before tagging releases for HACS.

See the modules under `custom_components/heating_optimizer` for the coordinator and sensor implementations.
