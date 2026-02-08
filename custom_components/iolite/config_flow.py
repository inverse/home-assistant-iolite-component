"""Config flow for IOLITE."""

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CLIENT_ID,
    CONF_CODE,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from iolite_client.oauth_handler import AsyncOAuthHandler
from voluptuous import Range

from . import HaOAuthStorageInterface
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)

MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 120

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_CLIENT_ID): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_CODE): cv.string,
        vol.Required(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_SECONDS
        ): vol.All(
            vol.Coerce(int), Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
        ),
        vol.Optional(CONF_VERIFY_SSL, default=True): cv.boolean,
    },
)


async def validate_and_persist_auth(
    hass: HomeAssistant,
    username: str,
    password: str,
    client_id: str,
    name: str,
    code: str,
    verify_ssl: bool = True,
):
    """Validate that the given inputs are correct and persist access token."""
    _LOGGER.debug("Validation IOLITE auth")

    web_session = async_get_clientsession(hass)
    oauth_handler = AsyncOAuthHandler(
        username, password, web_session, client_id, verify_ssl=verify_ssl
    )
    access_token = await oauth_handler.get_access_token(code, name)
    storage = HaOAuthStorageInterface(hass)
    await storage.store_access_token(access_token)


class IoliteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """IOLITE config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Initiate Options Flow Instance"""
        return IoliteOptionsFlow(config_entry)

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""

        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                await validate_and_persist_auth(
                    self.hass,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_CLIENT_ID],
                    user_input[CONF_NAME],
                    user_input[CONF_CODE],
                    user_input.get(CONF_VERIFY_SSL, True),
                )
            except Exception as e:
                errors["base"] = "auth"
                _LOGGER.error(f"Failed to validate auth: {e}")

            if not errors:
                return self.async_create_entry(title="IOLITE", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )


class IoliteOptionsFlow(config_entries.OptionsFlow):
    """IOLITE options flow"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize Hue options flow."""
        # The config_entry parameter is passed to the constructor but not stored directly
        # as self.config_entry, which is deprecated in Home Assistant 2025.12

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Hue options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL_SECONDS
                    ): vol.All(
                        vol.Coerce(int),
                        Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_VERIFY_SSL,
                        default=self.config_entry.options.get(
                            CONF_VERIFY_SSL,
                            self.config_entry.data.get(CONF_VERIFY_SSL, True),
                        ),
                    ): cv.boolean,
                }
            ),
        )
