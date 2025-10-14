# Heating Optimizer

Custom Home Assistant integration intended to orchestrate more efficient heating strategies. The actual optimisation logic is still to be implemented – this repository contains the boilerplate required to iterate quickly with HACS and the Home Assistant config-entry framework.

## Features
- Minimal config-entry based integration scaffold with translations and logging.
- Ready for HACS distribution (`hacs.json`, versioned manifest, README rendering).
- Test harness based on `pytest-homeassistant-custom-component` to validate the config flow.

## Installation
1. Zip the repository contents or publish it to GitHub.
2. In Home Assistant, open HACS → Integrations → ⋮ → Custom repositories.
3. Add the repository URL, choose the **Integration** category, and install *Heating Optimizer*.
4. Restart Home Assistant and add the integration via *Settings → Devices & services → Add integration*.

## Configuration
The initial config flow simply creates a single instance of the integration. Extend `config_flow.py` with any additional options or validation once the optimisation inputs are known.

## Development
- Use a Python 3.11+ environment.
- Install development dependencies: `pip install -r requirements_dev.txt`.
- Run tests with `pytest`.
- Keep the manifest version in sync with your tags before releasing updates through HACS.

Refer to the inline comments in `custom_components/heating_optimizer` for guidance on where to add sensors, coordinators, or services as the integration evolves.
# ha-heating-optimizer
