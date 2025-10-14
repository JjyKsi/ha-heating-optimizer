"""Coordinators for the Heating Optimizer integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
from typing import Any, Callable

import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DEVICE_NAME,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_CHEAP_PRICE,
    DEFAULT_COMFORT_TEMP,
    DEFAULT_EXPENSIVE_PRICE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    LOGGER,
    PLAN_GENERATION_INTERVAL,
    PRICE_API_URL,
    PRICE_CACHE_DURATION,
)
from .planner import PlanResult, PriceSlot, generate_water_tank_plan


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
            price = float(item["price"])
            start = dt_util.parse_datetime(item["startDate"])
            end = dt_util.parse_datetime(item["endDate"])
        except (KeyError, TypeError, ValueError) as err:
            raise UpdateFailed(f"Invalid price payload: {item}") from err

        if start is None or end is None:
            raise UpdateFailed(f"Invalid timestamp in price payload: {item}")

        slots.append(
            PriceSlot(
                start=start.astimezone(timezone.utc),
                end=end.astimezone(timezone.utc),
                price=price,
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


class PlanCoordinator(DataUpdateCoordinator[PlanResult]):
    """Coordinator that simulates heating plans based on prices and temperature."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, price: PriceCoordinator) -> None:
        self._entry = entry
        self._price = price
        self._temperature_entity = entry.data[CONF_TEMPERATURE_SENSOR]
        self._device_name = entry.data.get(CONF_DEVICE_NAME, entry.title)
        self._unsub_price: Callable[[], None] | None = None
        self._unsub_temperature: Callable[[], None] | None = None

        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}_plan_{entry.entry_id}",
            update_interval=PLAN_GENERATION_INTERVAL,
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Ensure prices are available before running the first plan."""
        await self._price.async_config_entry_first_refresh()
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self) -> PlanResult:
        prices = self._price.data
        if not prices:
            raise UpdateFailed("Price data unavailable")

        temp_state = self.hass.states.get(self._temperature_entity)
        if temp_state is None or temp_state.state in {STATE_UNKNOWN, STATE_UNAVAILABLE}:
            raise UpdateFailed("Temperature sensor unavailable")

        try:
            current_temp = float(temp_state.state)
        except ValueError as err:
            raise UpdateFailed("Temperature sensor provides non-numeric value") from err

        now = dt_util.utcnow()
        plan = generate_water_tank_plan(
            now=now,
            current_temperature=current_temp,
            prices=prices,
            cheap_threshold=DEFAULT_CHEAP_PRICE,
            expensive_threshold=DEFAULT_EXPENSIVE_PRICE,
            comfort_temp=DEFAULT_COMFORT_TEMP,
            min_temp=DEFAULT_MIN_TEMP,
            max_temp=DEFAULT_MAX_TEMP,
            device_name=self._device_name,
        )
        return plan

    async def async_start(self) -> None:
        """Begin listening to upstream updates to keep plan fresh."""
        if self._unsub_price is None:
            self._unsub_price = self._price.async_add_listener(self._handle_price_update)
        if self._unsub_temperature is None:
            self._unsub_temperature = async_track_state_change_event(
                self.hass,
                [self._temperature_entity],
                self._handle_temperature_update,
            )

    async def async_stop(self) -> None:
        """Cleanup listeners."""
        if self._unsub_price is not None:
            self._unsub_price()
            self._unsub_price = None
        if self._unsub_temperature is not None:
            self._unsub_temperature()
            self._unsub_temperature = None

    @callback
    def _handle_price_update(self) -> None:
        self.async_set_update_error(None)
        self.async_request_refresh()

    @callback
    def _handle_temperature_update(self, _event) -> None:
        self.async_set_update_error(None)
        self.async_request_refresh()

    @property
    def device_name(self) -> str:
        return self._device_name


@dataclass
class RuntimeData:
    """Runtime objects stored in hass.data."""

    price: PriceCoordinator
    plan: PlanCoordinator

    async def async_shutdown(self) -> None:
        await self.plan.async_stop()
        await self.plan.async_shutdown()
        await self.price.async_shutdown()


async def async_setup_runtime(hass: HomeAssistant, entry: ConfigEntry) -> RuntimeData:
    """Initialise coordinators and perform first refresh."""
    price_coordinator = PriceCoordinator(hass)
    plan_coordinator = PlanCoordinator(hass, entry, price_coordinator)

    await plan_coordinator.async_config_entry_first_refresh()
    await plan_coordinator.async_start()

    return RuntimeData(price=price_coordinator, plan=plan_coordinator)
