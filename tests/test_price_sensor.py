"""Integration test for the price sensor."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.porssisahko.const import ATTRIBUTION, DOMAIN
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

    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Porssisahko")
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    prices = [8.0, 3.0, 12.0, 5.0, 4.0, 6.0, 10.0, 7.0]
    payload = _build_price_payload(now.replace(minute=0, second=0, microsecond=0), prices)

    with (
        patch(
            "custom_components.porssisahko.coordinator.async_fetch_prices",
            AsyncMock(return_value=payload),
        ),
        patch(
            "custom_components.porssisahko.coordinator.dt_util.utcnow",
            return_value=now,
        ),
        patch(
            "custom_components.porssisahko.sensor.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_current_price"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "8.0"

    attributes = state.attributes
    assert attributes["attribution"] == ATTRIBUTION
    assert attributes["min_price"] == pytest.approx(min(prices), abs=1e-4)
    assert attributes["max_price"] == pytest.approx(max(prices), abs=1e-4)
    assert attributes["average_price"] == pytest.approx(sum(prices) / len(prices), abs=1e-4)

    assert attributes["current_start"] == "2024-06-01T06:00+00:00"
    assert attributes["current_end"] == "2024-06-01T06:15+00:00"
    assert attributes["next_change"] == "2024-06-01T06:15+00:00"

    upcoming = attributes["upcoming_slots"]
    assert isinstance(upcoming, list)
    assert upcoming
    # First upcoming slot corresponds to the second entry (3.0 c/kWh).
    assert upcoming[0]["price"] == 3.0
    assert upcoming[0]["start"] == "2024-06-01T06:15+00:00"
