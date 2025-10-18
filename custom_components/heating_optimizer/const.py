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
DAY_RATE_SURCHARGE: Final = 0.0255
NIGHT_RATE_SURCHARGE: Final = 0.0112
CHEAPER_THRESHOLD: Final = 0.01  # € (>=1 cent lower)

LOGGER = logging.getLogger(__package__)
