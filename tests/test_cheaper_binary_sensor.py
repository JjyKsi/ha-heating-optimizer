"""Tests for the cheaper-price binary sensors."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.heating_optimizer.const import (
    CHEAPER_THRESHOLD_CENT,
    DOMAIN,
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


async def test_binary_sensors_detect_cheaper_prices(hass: HomeAssistant) -> None:
    """Binary sensors should turn on when cheaper slots exist within the horizon."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Heating Optimizer")
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    prices = [8.0, 6.5, 8.2, 8.1, 7.0, 6.8, 9.0, 8.6]
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
        patch(
            "custom_components.heating_optimizer.binary_sensor.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    horizons = (15, 60, 180, 1440)

    for minutes in horizons:
        if minutes in (15, 30, 45):
            expected_window = f"{minutes} min"
        else:
            expected_window = f"{minutes // 60} h"
        entity_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_cheaper_{minutes}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "on"
        assert state.attributes.get("minutes") == minutes
        assert state.attributes.get("window") == expected_window
        assert state.attributes.get("reference_raw_price") == pytest.approx(prices[0], abs=1e-4)
        assert state.attributes.get("reference_surcharge") == pytest.approx(NIGHT_RATE_SURCHARGE_CENT, abs=1e-4)
        assert state.attributes.get("threshold") == CHEAPER_THRESHOLD_CENT
        assert "cheaper_price" in state.attributes


async def test_binary_sensors_off_without_cheaper_prices(hass: HomeAssistant) -> None:
    """Binary sensors should stay off when no cheaper slot exists."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Heating Optimizer")
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    prices = [8.0, 8.0, 8.2, 8.5, 8.7, 9.0, 9.5, 10.0]
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
        patch(
            "custom_components.heating_optimizer.binary_sensor.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    horizons = (15, 60, 180, 1440)

    for minutes in horizons:
        if minutes in (15, 30, 45):
            expected_window = f"{minutes} min"
        else:
            expected_window = f"{minutes // 60} h"
        entity_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_cheaper_{minutes}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "off"
        assert state.attributes.get("window") == expected_window
        assert state.attributes.get("reference_raw_price") == pytest.approx(prices[0], abs=1e-4)
        assert state.attributes.get("reference_surcharge") == pytest.approx(NIGHT_RATE_SURCHARGE_CENT, abs=1e-4)
        assert state.attributes.get("threshold") == CHEAPER_THRESHOLD_CENT
        assert "cheaper_price" not in state.attributes


async def test_binary_sensors_threshold_respected(hass: HomeAssistant) -> None:
    """Cheaper price must beat the threshold to trigger."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Heating Optimizer")
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    # The second slot is only 0.005 cheaper (below threshold 0.01).
    prices = [8.0, 7.995, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6]
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
        patch(
            "custom_components.heating_optimizer.binary_sensor.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_cheaper_15"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "off"


async def test_increase_sensors_detect_price_rises(hass: HomeAssistant) -> None:
    """Price rise sensors should turn on when increases exist."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Heating Optimizer")
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    prices = [8.0, 9.5, 9.8, 10.2, 10.0, 9.9, 11.0, 10.5]
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
        patch(
            "custom_components.heating_optimizer.binary_sensor.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    horizons = (15, 60, 180, 1440)

    for minutes in horizons:
        if minutes in (15, 30, 45):
            expected_window = f"{minutes} min"
        else:
            expected_window = f"{minutes // 60} h"
        entity_id = entity_registry.async_get_entity_id(
            "binary_sensor", DOMAIN, f"{entry.entry_id}_increase_{minutes}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "on"
        assert state.attributes.get("minutes") == minutes
        assert state.attributes.get("window") == expected_window
        assert state.attributes.get("reference_raw_price") == pytest.approx(prices[0], abs=1e-4)
        assert state.attributes.get("reference_surcharge") == pytest.approx(NIGHT_RATE_SURCHARGE_CENT, abs=1e-4)
        assert state.attributes.get("threshold") == CHEAPER_THRESHOLD_CENT
        assert "increase_price" in state.attributes


async def test_increase_sensors_off_without_price_rise(hass: HomeAssistant) -> None:
    """Price rise sensors should stay off when no higher slot exists."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Heating Optimizer")
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    prices = [8.0, 7.8, 7.9, 7.6, 7.5, 7.4, 7.2, 7.1]
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
        patch(
            "custom_components.heating_optimizer.binary_sensor.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_increase_{15}"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "off"


async def test_increase_sensors_threshold_respected(hass: HomeAssistant) -> None:
    """Increase sensors require price to rise beyond threshold."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Heating Optimizer")
    entry.add_to_hass(hass)

    now = datetime(2024, 6, 1, 6, 5, tzinfo=timezone.utc)
    prices = [8.0, 8.5, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2]
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
        patch(
            "custom_components.heating_optimizer.binary_sensor.dt_util.utcnow",
            return_value=now,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{entry.entry_id}_increase_{15}"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "off"
