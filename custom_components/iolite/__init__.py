import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.const import CONF_CODE, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

ACTUAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_CODE): cv.string,
    },
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: ACTUAL_SCHEMA},
)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    # Forward the setup to the climate platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the component from yaml configuration."""
    if DOMAIN not in config:
        return True

    return True
