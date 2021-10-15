import logging
import time
from datetime import timedelta
from typing import Any, Dict

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CODE, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from iolite_client.client import Client
from iolite_client.entity import RadiatorValve
from iolite_client.oauth_handler import AsyncOAuthHandler

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]
    name: str = entry.data[CONF_NAME]
    code: str = entry.data[CONF_CODE]

    websession = async_get_clientsession(hass)

    coordinator = IoliteDataUpdateCoordinator(
        hass, websession, username, password, name, code
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


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


class IoliteDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching IOLITE data."""

    def __init__(
        self,
        hass: HomeAssistant,
        web_session: ClientSession,
        username: str,
        password: str,
        name: str,
        code: str,
    ):
        """Initialiser."""
        self.hass = hass
        self.web_session = web_session
        self.username = username
        self.password = password
        self.name = name
        self.code = code
        self.client = None

        update_interval = timedelta(seconds=30)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        store = self.hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)

        # Get SID
        oauth_handler = AsyncOAuthHandler(
            self.username, self.password, self.web_session
        )
        sid = await get_sid(self.code, self.name, oauth_handler, store)

        self.client = Client(sid, self.username, self.password)
        await self.client.async_discover()

        # Map entities valves
        devices = {}

        devices.setdefault("valves", {})
        for room in self.client.discovered.get_rooms():
            for device in room.devices.values():
                if isinstance(device, RadiatorValve):
                    devices["valves"][device.identifier] = device

        return devices
