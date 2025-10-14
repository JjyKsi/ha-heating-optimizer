# Heating Optimizer

Custom Home Assistant integration intended to orchestrate more efficient heating strategies. The first iteration focuses on modelling quarter-hour electricity prices and simulating heating plans for a domestic hot-water tank without actuating any relays yet.

## Features
- Config-entry based setup with per-device metadata stored in Home Assistant.
- Price ingestion from [porssisahko.net v2](https://api.porssisahko.net/) via a cached coordinator.
- Heuristic water-tank planner that respects comfort/min/max temperatures and price thresholds.
- Diagnostic sensor exposing the upcoming heating plan (actions, prices, predicted temperatures).
- Ready for HACS distribution (`hacs.json`, versioned manifest, README rendering).
- Test harness based on `pytest-homeassistant-custom-component` to validate the config flow and planner logic.

## Installation
1. Zip the repository contents or publish it to GitHub.
2. In Home Assistant, open HACS → Integrations → ⋮ → Custom repositories.
3. Add the repository URL, choose the **Integration** category, and install *Heating Optimizer*.
4. Restart Home Assistant and add the integration via *Settings → Devices & services → Add integration*.

## Configuration
The current config flow asks for the water-tank temperature sensor entity ID and creates a single integration instance. The integration publishes a plan sensor only; it does not toggle the underlying switches yet. Extend `config_flow.py` and `planner.py` as additional profiles and controls are implemented.

## Development
- Use a Python 3.11+ environment.
- Install development dependencies: `pip install -r requirements_dev.txt`.
- Run tests with `pytest`.
- Keep the manifest version in sync with your tags before releasing updates through HACS.

Refer to the inline comments in `custom_components/heating_optimizer` for guidance on where to add sensors, coordinators, or services as the integration evolves.
