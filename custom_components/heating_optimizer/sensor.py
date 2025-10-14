"""Sensors exposing the Heating Optimizer plan."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RuntimeData
from .planner import PlanEntry, PlanResult


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up plan sensors for a config entry."""
    runtime: RuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HeatingPlanSensor(
                entry_id=entry.entry_id,
                device_name=runtime.plan.device_name,
                coordinator=runtime.plan,
            )
        ]
    )


class HeatingPlanSensor(CoordinatorEntity, SensorEntity):
    """Sensor reporting the next planned action."""

    _attr_has_entity_name = True
    _attr_translation_key = "plan"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:chart-timeline"

    def __init__(self, entry_id: str, device_name: str, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_plan"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": device_name,
        }

    @property
    def native_value(self) -> str | None:
        plan: PlanResult | None = self.coordinator.data
        if not plan or not plan.plan:
            return None
        next_entry = plan.plan[0]
        return next_entry.action

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attributes: dict[str, object] = {}
        plan: PlanResult | None = self.coordinator.data
        if not plan:
            return attributes

        attributes["generated_at"] = _format_datetime(plan.generated_at)
        attributes["current_temperature"] = round(plan.current_temperature, 2)
        attributes["horizon_entries"] = [
            _serialize_plan_entry(entry) for entry in plan.plan[:16]
        ]
        return attributes


def _format_datetime(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="minutes")


def _serialize_plan_entry(entry: PlanEntry) -> dict[str, object]:
    return {
        "start": _format_datetime(entry.start),
        "end": _format_datetime(entry.end),
        "action": entry.action,
        "stages": entry.stages,
        "price": round(entry.price, 4),
        "predicted_temp": round(entry.predicted_temp, 2),
        "target_temp": round(entry.target_temp, 2),
        "reason": entry.reason,
    }
