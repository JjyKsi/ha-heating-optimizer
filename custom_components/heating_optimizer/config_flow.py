"""Config flow for the Heating Optimizer integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LOGGER


class HeatingOptimizerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Heating Optimizer."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            LOGGER.debug("Config flow aborted; integration already configured.")
            return self.async_abort(reason="already_configured")

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                description_placeholders={},
            )

        return self.async_create_entry(title="Heating Optimizer", data={})
