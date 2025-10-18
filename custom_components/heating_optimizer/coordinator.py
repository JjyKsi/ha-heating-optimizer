"""Coordinators for the Heating Optimizer integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    LOGGER,
    PRICE_API_URL,
    PRICE_CACHE_DURATION,
    DAY_TIME_START_HOUR,
    DAY_TIME_END_HOUR,
    DAY_RATE_SURCHARGE_CENT,
    NIGHT_RATE_SURCHARGE_CENT,
)


@dataclass(slots=True)
class PriceSlot:
    """Electricity price for a specific interval."""

    start: datetime
    end: datetime
    price: float
    raw_price: float
    surcharge: float


async def async_fetch_prices(session) -> dict[str, Any]:
    """Fetch raw price payload from porssisahko.net API."""
    async with async_timeout.timeout(10):
        response = await session.get(PRICE_API_URL)
        response.raise_for_status()
        return await response.json()


def _parse_price_slots(prices: list[dict[str, Any]]) -> list[PriceSlot]:
    """Parse API payload into structured slots."""
    prices = prices or []
    slots: list[PriceSlot] = []
    for item in prices:
        try:
            raw_price = float(item["price"])
            start = dt_util.parse_datetime(item["startDate"])
            end = dt_util.parse_datetime(item["endDate"])
        except (KeyError, TypeError, ValueError) as err:
            raise UpdateFailed(f"Invalid price payload: {item}") from err

        if start is None or end is None:
            raise UpdateFailed(f"Invalid timestamp in price payload: {item}")

        local_hour = dt_util.as_local(start).hour
        if DAY_TIME_START_HOUR <= local_hour <= DAY_TIME_END_HOUR:
            surcharge = DAY_RATE_SURCHARGE_CENT
        else:
            surcharge = NIGHT_RATE_SURCHARGE_CENT
        price = raw_price + surcharge

        slots.append(
            PriceSlot(
                start=start.astimezone(timezone.utc),
                end=end.astimezone(timezone.utc),
                price=price,
                raw_price=raw_price,
                surcharge=surcharge,
            )
        )
    return slots


class PriceCoordinator(DataUpdateCoordinator[list[PriceSlot]]):
    """Coordinator responsible for refreshing electricity prices."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._session = async_get_clientsession(hass)
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}_price",
            update_interval=PRICE_CACHE_DURATION,
        )

    async def _async_update_data(self) -> list[PriceSlot]:
        payload = await async_fetch_prices(self._session)
        prices = payload.get("prices")
        if not prices:
            raise UpdateFailed("No price data returned")
        return _parse_price_slots(prices)


@dataclass
class RuntimeData:
    """Runtime objects stored in hass.data."""

    price: PriceCoordinator

    async def async_shutdown(self) -> None:
        """Handle teardown for runtime objects."""
        return


async def async_setup_runtime(hass: HomeAssistant, _entry: ConfigEntry) -> RuntimeData:
    """Initialise the price coordinator and perform the first refresh."""
    price_coordinator = PriceCoordinator(hass)

    await price_coordinator.async_config_entry_first_refresh()

    return RuntimeData(price=price_coordinator)
