"""Constants for the Heating Optimizer integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

DOMAIN: Final = "heating_optimizer"

CONF_TEMPERATURE_SENSOR: Final = "temperature_sensor"
CONF_DEVICE_NAME: Final = "device_name"

DEFAULT_DEVICE_NAME: Final = "Water Tank"
DEFAULT_MIN_TEMP: Final = 60.0
DEFAULT_COMFORT_TEMP: Final = 75.0
DEFAULT_MAX_TEMP: Final = 90.0
DEFAULT_CHEAP_PRICE: Final = 4.0  # c/kWh
DEFAULT_EXPENSIVE_PRICE: Final = 15.0  # c/kWh

PRICE_API_URL: Final = "https://api.porssisahko.net/v2/latest-prices.json"
PRICE_CACHE_DURATION: Final = timedelta(hours=12)
PLAN_GENERATION_INTERVAL: Final = timedelta(minutes=15)
PLAN_HORIZON: Final = timedelta(hours=24)
PLAN_SLOT_MINUTES: Final = 15

LOGGER = logging.getLogger(__package__)
