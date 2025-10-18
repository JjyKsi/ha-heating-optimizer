"""Config flow for the Heating Optimizer integration."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, LOGGER

DEFAULT_TITLE = "Heating Optimizer"


class HeatingOptimizerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            LOGGER.debug("Config flow aborted; integration already configured.")
            return self.async_abort(reason="already_configured")

        LOGGER.debug("Creating config entry for %s", DOMAIN)
        return self.async_create_entry(title=DEFAULT_TITLE, data={})
