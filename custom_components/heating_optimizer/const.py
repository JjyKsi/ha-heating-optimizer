"""Constants for the Heating Optimizer integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

DOMAIN: Final = "heating_optimizer"

PRICE_API_URL: Final = "https://api.porssisahko.net/v2/latest-prices.json"
PRICE_CACHE_DURATION: Final = timedelta(hours=1)
ATTRIBUTION: Final = "Data provided by porssisahko.net"

LOGGER = logging.getLogger(__package__)
