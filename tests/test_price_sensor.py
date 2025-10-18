"""Integration test for the price sensor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.heating_optimizer.const import (
    ATTRIBUTION,
    DOMAIN,
    DAY_RATE_SURCHARGE_CENT,
    DAY_TIME_END_HOUR,
    DAY_TIME_START_HOUR,
    NIGHT_RATE_SURCHARGE_CENT,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _build_price_payload(start: datetime, prices: list[float]) -> dict:
    entries: list[dict[str, object]] = []
    slot = timedelta(minutes=15)
    cursor = start
    for price in prices:
        end = cursor + slot
        entries.append(
            {
                "price": price,
                "startDate": cursor.isoformat().replace("+00:00", "Z"),
                "endDate": end.isoformat().replace("+00:00", "Z"),
            }
        )
        cursor = end
    return {"prices": entries}


async def test_price_sensor_exposes_current_and_future_prices(hass: HomeAssistant) -> None:
    """Verify the price sensor publishes the current price and metadata."""
    await hass.config.async_set_time_zone("UTC")

    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Heating Optimizer")
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    prices = [8.0, 3.0, 12.0, 5.0, 4.0, 6.0, 10.0, 7.0]
    payload = _build_price_payload(now.replace(minute=0, second=0, microsecond=0), prices)

    with (
        patch(
            "custom_components.heating_optimizer.coordinator.async_fetch_prices",
            AsyncMock(return_value=payload),
        ),
        patch(
            "custom_components.heating_optimizer.coordinator.dt_util.utcnow",
            return_value=now,
        ),
        patch(
            "custom_components.heating_optimizer.sensor.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    def _surcharge_for(index: int) -> float:
        slot_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(minutes=15 * index)
        local_hour = slot_time.astimezone(timezone.utc).hour
        if DAY_TIME_START_HOUR <= local_hour <= DAY_TIME_END_HOUR:
            return DAY_RATE_SURCHARGE_CENT
        return NIGHT_RATE_SURCHARGE_CENT

    adjusted_prices = [base + _surcharge_for(idx) for idx, base in enumerate(prices)]

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_current_price"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert float(state.state) == pytest.approx(adjusted_prices[0], abs=1e-4)

    attributes = state.attributes
    assert attributes["attribution"] == ATTRIBUTION
    assert attributes["min_price"] == pytest.approx(min(adjusted_prices), abs=1e-4)
    assert attributes["max_price"] == pytest.approx(max(adjusted_prices), abs=1e-4)
    assert attributes["average_price"] == pytest.approx(sum(adjusted_prices) / len(adjusted_prices), abs=1e-4)
    assert attributes["current_raw_price"] == pytest.approx(prices[0], abs=1e-4)
    assert attributes["current_surcharge"] == pytest.approx(_surcharge_for(0), abs=1e-4)

    assert attributes["current_start"] == "2024-06-01T06:00+00:00"
    assert attributes["current_end"] == "2024-06-01T06:15+00:00"
    assert attributes["next_change"] == "2024-06-01T06:15+00:00"

    upcoming = attributes["upcoming_slots"]
    assert isinstance(upcoming, list)
    assert upcoming
    # First upcoming slot corresponds to the second entry (3.0 c/kWh).
    assert upcoming[0]["price"] == pytest.approx(adjusted_prices[1], abs=1e-4)
    assert upcoming[0]["raw_price"] == pytest.approx(prices[1], abs=1e-4)
    assert upcoming[0]["surcharge"] == pytest.approx(_surcharge_for(1), abs=1e-4)
    assert upcoming[0]["start"] == "2024-06-01T06:15+00:00"
