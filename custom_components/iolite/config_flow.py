"""Config flow for IOLITE."""
import logging
import time
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_CODE, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from iolite_client.oauth_handler import AsyncOAuthHandler

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_CODE): cv.string,
    },
)


async def validate_and_persist_auth(
    hass: HomeAssistant, username: str, password: str, name: str, code: str
):
    """Validate that the given inputs are correct and persist access token."""
    _LOGGER.debug("Validation IOLITE auth")

    web_session = async_get_clientsession(hass)
    oauth_handler = AsyncOAuthHandler(username, password, web_session)
    access_token = await oauth_handler.get_access_token(code, name)

    expires_at = time.time() + access_token["expires_in"]
    access_token.update({"expires_at": expires_at})
    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
    await store.async_save(access_token)


class IoliteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """IOLITE config flow."""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=SCHEMA)

        errors: Dict[str, str] = {}

        try:
            validate_and_persist_auth(
                self.hass,
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_NAME],
                user_input[CONF_CODE],
            )
        except Exception as e:
            errors["config"] = "auth"
            _LOGGER.error(f"Failed to validate auth: {e}")

        return self.async_create_entry(title="IOLITE", data=user_input, errors=errors)
