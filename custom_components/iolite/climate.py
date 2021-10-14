"""Support for IOLITE heating."""

import logging
import time
from typing import Any

from homeassistant import config_entries
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_CODE,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from iolite_client.client import Client
from iolite_client.entity import RadiatorValve
from iolite_client.oauth_handler import AsyncOAuthHandler

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup from config entry."""

    config = config_entry.data
    web_session = async_get_clientsession(hass)

    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]

    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)

    # Get SID
    oauth_handler = AsyncOAuthHandler(username, password, web_session)
    sid = await get_sid(config[CONF_CODE], config[CONF_NAME], oauth_handler, store)

    client = Client(sid, username, password)
    await client.async_discover()

    # Map radiator valves
    devices = []
    for room in client.discovered.get_rooms():
        for device in room.devices.values():
            if isinstance(device, RadiatorValve):
                devices.append(RadiatorValveEntity(device, client))

    for device in devices:
        _LOGGER.info(f"Adding {device}")

    async_add_entities(devices, update_before_add=True)


async def get_sid(code: str, name: str, oauth_handler: AsyncOAuthHandler, store: Store):
    """Get SID."""
    access_token = await store.async_load()
    if access_token is None:
        _LOGGER.debug("No access token in storage, requesting")
        access_token = await oauth_handler.get_access_token(code, name)
        expires_at = time.time() + access_token["expires_in"]
        access_token.update({"expires_at": expires_at})
        await store.async_save(access_token)

    if access_token["expires_at"] < time.time():
        _LOGGER.debug("Access token expired, refreshing")
        refreshed_token = await oauth_handler.get_new_access_token(
            access_token["refresh_token"]
        )
        await store.async_save(refreshed_token)
        token = refreshed_token["access_token"]
    else:
        token = access_token["access_token"]

    _LOGGER.debug("Fetched access token")

    return await oauth_handler.get_sid(token)


class RadiatorValveEntity(ClimateEntity):
    """Map RadiatorValue to Climate entity."""

    _attr_temperature_unit: str = TEMP_CELSIUS
    _attr_target_temperature_step: float = 0.5
    _attr_hvac_modes: list = [HVAC_MODE_HEAT]
    _attr_supported_features: int = SUPPORT_FLAGS

    def __init__(self, valve: RadiatorValve, client: Client):
        """Initialize the valve."""
        self.valve = valve
        self.client = client
        self._attr_unique_id = valve.identifier
        self._attr_min_temp = 0
        self._attr_max_temp = 30
        self._update_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        await self.client.async_set_temp(self.valve.identifier, temperature)

    @property
    def hvac_mode(self):
        """Return hvac operation."""
        return HVAC_MODE_HEAT

    async def async_update(self) -> None:
        """Retrieve latest state."""
        await self.client.async_discover()

        matched = self.client.discovered.find_device_by_identifier(
            self.valve.identifier
        )

        if not matched:
            _LOGGER.warn(f"Failed to resolve RadiatorValue for {self.valve.identifier}")
            return

        self.valve = matched
        self._update_state()

    def _update_state(self):
        self._attr_name = self.valve.name
        self._attr_current_temperature = self.valve.current_env_temp
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": self.valve.manufacturer,
        }
