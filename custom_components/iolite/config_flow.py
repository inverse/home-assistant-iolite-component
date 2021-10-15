"""Config flow for IOLITE."""
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_CODE, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_CODE): cv.string,
    },
)


class IoliteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """IOLITE config flow."""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=SCHEMA)

        return self.async_create_entry(title="IOLITE", data=user_input)
