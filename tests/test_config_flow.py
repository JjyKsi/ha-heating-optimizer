"""Test the Heating Optimizer config flow."""

from __future__ import annotations

import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.heating_optimizer.const import (
    CONF_DEVICE_NAME,
    CONF_TEMPERATURE_SENSOR,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_user_flow_single_instance(hass: HomeAssistant) -> None:
    """Ensure the user flow creates a single config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    user_input = {CONF_TEMPERATURE_SENSOR: "sensor.tank_temp"}
    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == DEFAULT_DEVICE_NAME
    assert result2["data"] == {
        CONF_DEVICE_NAME: DEFAULT_DEVICE_NAME,
        CONF_TEMPERATURE_SENSOR: "sensor.tank_temp",
    }

    # Second attempt should abort because only one instance is allowed.
    result3 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result3["type"] == data_entry_flow.FlowResultType.ABORT
    assert result3["reason"] == "already_configured"
