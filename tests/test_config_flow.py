"""Test the Heating Optimizer config flow."""

from __future__ import annotations

import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.heating_optimizer.const import DOMAIN

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_user_flow_single_instance(hass: HomeAssistant) -> None:
    """Ensure the user flow creates a single config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Heating Optimizer"
    assert result2["data"] == {}

    # Second attempt should abort because only one instance is allowed.
    result3 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result3["type"] == data_entry_flow.FlowResultType.ABORT
    assert result3["reason"] == "already_configured"
