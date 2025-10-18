"""Binary sensors reporting cheaper price windows."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CHEAPER_THRESHOLD_CENT, DOMAIN
from .coordinator import PriceCoordinator, PriceSlot, RuntimeData
from .helpers import current_slot, format_slot_time, slot_for_time

HORIZONS_MINUTES: tuple[int, ...] = (15, 30, 45, 60) + tuple(range(120, 1441, 60))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up binary sensors for a config entry."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    entities = [
        CheaperPriceBinarySensor(
            entry_id=entry.entry_id,
            entry_title=entry.title,
            coordinator=runtime.price,
            minutes=minutes,
        )
        for minutes in HORIZONS_MINUTES
    ]
    async_add_entities(entities)


class CheaperPriceBinarySensor(CoordinatorEntity[PriceCoordinator], BinarySensorEntity):
    """Indicate if a cheaper price appears within the horizon."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:trending-down"
    _attr_translation_key = "cheaper_within"

    def __init__(
        self,
        *,
        entry_id: str,
        entry_title: str | None,
        coordinator: PriceCoordinator,
        minutes: int,
    ) -> None:
        super().__init__(coordinator)
        self._horizon_minutes = minutes
        if minutes in (15, 30, 45):
            window = f"{minutes} min"
        else:
            hours = minutes // 60
            window = f"{hours} h"
        self._window_label = window
        self._offsets: tuple[int, ...] = tuple(range(0, minutes + 15, 15))
        self._cached_attributes: dict[str, Any] | None = None

        self._attr_translation_placeholders = {"window": self._window_label}
        self._attr_unique_id = f"{entry_id}_cheaper_{minutes}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": entry_title or "Heating Optimizer",
            "manufacturer": "porssisahko.net",
            "configuration_url": "https://api.porssisahko.net/",
        }

    @property
    def available(self) -> bool:
        return current_slot(self.coordinator.data, now=dt_util.utcnow()) is not None

    @property
    def is_on(self) -> bool:
        state, metadata = self._evaluate()
        self._cached_attributes = metadata
        return state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self._cached_attributes is None:
            _, metadata = self._evaluate()
            self._cached_attributes = metadata
        return self._cached_attributes or {}

    def _evaluate(self) -> tuple[bool, dict[str, Any] | None]:
        slots = self.coordinator.data
        now = dt_util.utcnow()
        current = current_slot(slots, now=now)
        if slots is None or current is None:
            return False, None

        baseline = current.price
        evaluated: list[PriceSlot] = []
        cheaper_match: PriceSlot | None = None

        for offset in self._offsets:
            target = current.start + timedelta(minutes=offset)
            slot = slot_for_time(slots, target)
            if slot is None or slot in evaluated:
                continue
            evaluated.append(slot)
            if baseline - slot.price >= CHEAPER_THRESHOLD_CENT:
                cheaper_match = slot
                break

        attributes: dict[str, Any] = {
            "minutes": self._horizon_minutes,
            "window": self._window_label,
            "reference_price": round(baseline, 4),
            "reference_raw_price": round(current.raw_price, 4),
            "reference_surcharge": round(current.surcharge, 4),
            "reference_start": format_slot_time(current.start),
            "reference_end": format_slot_time(current.end),
            "slots_checked": len(evaluated),
            "threshold": CHEAPER_THRESHOLD_CENT,
        }

        if cheaper_match:
            attributes.update(
                {
                    "cheaper_price": round(cheaper_match.price, 4),
                    "cheaper_raw_price": round(cheaper_match.raw_price, 4),
                    "cheaper_surcharge": round(cheaper_match.surcharge, 4),
                    "cheaper_start": format_slot_time(cheaper_match.start),
                    "cheaper_end": format_slot_time(cheaper_match.end),
                }
            )

        return cheaper_match is not None, attributes
