import logging
import time
from typing import Any

from homeassistant import config_entries, core
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

from iolite.client import Client
from iolite.entity import RadiatorValve
from iolite.oauth_handler import OAuthHandler

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup from config entry."""

    config = config_entry.data

    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]

    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)

    # Get SID
    oauth_handler = OAuthHandler(username, password)
    sid = await get_sid(config[CONF_CODE], config[CONF_NAME], oauth_handler, store)

    client = Client(sid, username, password)
    await client._async_discover()

    # Map radiator valves
    devices = []
    for device in client.discovered:
        if isinstance(device, RadiatorValve):
            devices.append(RadiatorValveEntity(device, client))

    async_add_entities(devices, True)


async def get_sid(
    code: str,
    name: str,
    oauth_handler: OAuthHandler,
    store: core.HomeAssistant.helpers.storage.Store,
):
    access_token = await store.async_load()
    if access_token is None:
        _LOGGER.debug("No access token in storage, requesting")
        access_token = oauth_handler.get_access_token(code, name)
        await store.async_save(access_token)

    if access_token["expires_at"] < time.time():
        _LOGGER.debug("Access token expired, refreshing")
        refreshed_token = oauth_handler.get_new_access_token(
            access_token["refresh_token"]
        )
        await store.async_save(refreshed_token)
        token = refreshed_token["access_token"]
    else:
        token = access_token["access_token"]

    _LOGGER.debug("Fetched access token")

    return oauth_handler.get_sid(token)


class RadiatorValveEntity(ClimateEntity):

    _attr_temperature_unit: str = TEMP_CELSIUS
    _attr_target_temperature_step: float = 0.5
    _attr_hvac_modes: list = [HVAC_MODE_HEAT]
    _attr_supported_features: int = SUPPORT_FLAGS

    def __init__(self, valve: RadiatorValve, client: Client):
        self.valve = valve
        self.client = client
        self._attr_unique_id = valve.identifier
        self._attr_name = valve.name
        self._attr_min_temp = self._heater.get_min_temp()
        self._attr_max_temp = self._heater.get_max_temp()
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "manufacturer": valve.manufacturer,
        }

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
