"""Sensors exposing electricity prices from porssisahko.net."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION, DOMAIN
from .coordinator import PriceCoordinator, PriceSlot, RuntimeData
from .helpers import current_slot, format_slot_time


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up price sensors for a config entry."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PorssisahkoPriceSensor(
                entry_id=entry.entry_id,
                entry_title=entry.title,
                coordinator=runtime.price,
            )
        ]
    )


class PorssisahkoPriceSensor(CoordinatorEntity[PriceCoordinator], SensorEntity):
    """Sensor reporting the current electricity price."""

    _attr_has_entity_name = True
    _attr_translation_key = "current_price"
    _attr_native_unit_of_measurement = "c/kWh"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:currency-eur"

    def __init__(self, entry_id: str, entry_title: str | None, coordinator: PriceCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_current_price"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": entry_title or "Porssisahko",
            "manufacturer": "porssisahko.net",
            "configuration_url": "https://api.porssisahko.net/",
        }

    @property
    def native_value(self) -> float | None:
        now = dt_util.utcnow()
        slot = current_slot(self.coordinator.data, now=now)
        if slot is None:
            return None
        return round(slot.price, 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {"attribution": ATTRIBUTION}
        slots = self.coordinator.data or []
        now = dt_util.utcnow()

        current = current_slot(slots, now=now)
        if current:
            attributes["current_start"] = format_slot_time(current.start)
            attributes["current_end"] = format_slot_time(current.end)

        upcoming = [slot for slot in slots if slot.start > now]
        if upcoming:
            attributes["next_change"] = format_slot_time(upcoming[0].start)
            attributes["upcoming_slots"] = _serialize_slots(upcoming[:8])

        if slots:
            prices = [slot.price for slot in slots]
            attributes["min_price"] = round(min(prices), 4)
            attributes["max_price"] = round(max(prices), 4)
            attributes["average_price"] = round(sum(prices) / len(prices), 4)

        return attributes


def _serialize_slots(slots: Iterable[PriceSlot]) -> list[dict[str, Any]]:
    return [
        {
            "start": format_slot_time(slot.start),
            "end": format_slot_time(slot.end),
            "price": round(slot.price, 4),
        }
        for slot in slots
    ]
