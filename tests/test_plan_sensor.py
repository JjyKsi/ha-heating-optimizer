"""Integration test for the planning sensor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.heating_optimizer.const import (
    CONF_DEVICE_NAME,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
)
from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _build_price_payload(start: datetime, count: int, price: float) -> dict:
    entries: list[dict[str, object]] = []
    slot = timedelta(minutes=15)
    cursor = start
    for _ in range(count):
        end = cursor + slot
        entries.append(
            {
                "price": price,
                "startDate": cursor.isoformat().replace("+00:00", "Z"),
                "endDate": end.isoformat().replace("+00:00", "Z"),
            }
        )
        cursor = end
    # Add a cheap window a few slots ahead to demonstrate planning appetite.
    entries[4]["price"] = 3.0
    entries[5]["price"] = 3.0
    return {"prices": entries}


async def test_plan_sensor_renders_next_action(hass: HomeAssistant) -> None:
    """Verify the plan sensor exposes the next planned action."""
    hass.states.async_set("sensor.tank_temp", "74")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_DEVICE_NAME: DEFAULT_DEVICE_NAME,
            CONF_TEMPERATURE_SENSOR: "sensor.tank_temp",
        },
    )
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    payload = _build_price_payload(now - timedelta(hours=2), 96, 8.0)

    with (
        patch(
            "custom_components.heating_optimizer.coordinator.async_fetch_prices",
            AsyncMock(return_value=payload),
        ),
        patch(
            "custom_components.heating_optimizer.coordinator.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_plan"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state in {"heat_primary", "heat_dual", "idle"}
    assert "horizon_entries" in state.attributes
    assert isinstance(state.attributes["horizon_entries"], list)
    assert state.attributes["horizon_entries"], "Plan list should not be empty"

    # Temperature becomes unavailable -> coordinator should mark sensor unavailable.
    hass.states.async_set("sensor.tank_temp", STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    await hass.async_block_till_done()
    state_after = hass.states.get(entity_id)
    assert state_after is not None
    assert state_after.state == STATE_UNAVAILABLE
