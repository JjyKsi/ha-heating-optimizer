"""Heating Optimizer price integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, LOGGER
from .coordinator import RuntimeData, async_setup_runtime

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration via YAML (not supported)."""
    hass.data.setdefault(DOMAIN, {})
    LOGGER.debug("YAML setup invoked; nothing to configure yet.")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})
    runtime = await async_setup_runtime(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    LOGGER.debug("Config entry %s ready.", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        runtime: RuntimeData | None = hass.data[DOMAIN].pop(entry.entry_id, None)
        if runtime:
            await runtime.async_shutdown()
        LOGGER.debug("Config entry %s unloaded.", entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle reloading a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
