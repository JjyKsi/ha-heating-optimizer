"""Constants for the Heating Optimizer integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

DOMAIN: Final = "heating_optimizer"

PRICE_API_URL: Final = "https://api.porssisahko.net/v2/latest-prices.json"
PRICE_CACHE_DURATION: Final = timedelta(hours=1)
ATTRIBUTION: Final = "Data provided by porssisahko.net"
DAY_TIME_START_HOUR: Final = 7
DAY_TIME_END_HOUR: Final = 22
DAY_RATE_SURCHARGE_CENT: Final = 2.55  # c/kWh
NIGHT_RATE_SURCHARGE_CENT: Final = 1.12  # c/kWh
CHEAPER_THRESHOLD_CENT: Final = 1.0  # c/kWh difference

LOGGER = logging.getLogger(__package__)
