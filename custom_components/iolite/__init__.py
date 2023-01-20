import logging
import time
from datetime import timedelta
from typing import Any, Dict, Optional

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from iolite_client.client import Client
from iolite_client.oauth_handler import AsyncOAuthHandler, AsyncOAuthStorageInterface

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    username: str = entry.data[CONF_USERNAME]
    password: str = entry.data[CONF_PASSWORD]

    web_session = async_get_clientsession(hass)

    storage = HaOAuthStorageInterface(hass)
    coordinator = IoliteDataUpdateCoordinator(
        hass, web_session, username, password, storage
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


async def get_sid(
    oauth_handler: AsyncOAuthHandler, storage: AsyncOAuthStorageInterface
):
    """Get SID."""
    access_token = await storage.fetch_access_token()

    if access_token["expires_at"] < time.time():
        _LOGGER.debug("Access token expired, refreshing")
        token = await refresh_token(oauth_handler, storage, access_token)
    else:
        token = access_token["access_token"]

    _LOGGER.debug("Fetched access token")

    try:
        return await oauth_handler.get_sid(token)
    except BaseException as e:
        _LOGGER.warning(f"Invalid token, attempt refresh: {e}")
        token = await refresh_token(oauth_handler, storage, access_token)
        return await oauth_handler.get_sid(token)


async def refresh_token(
    oauth_handler: AsyncOAuthHandler,
    storage: AsyncOAuthStorageInterface,
    access_token: dict,
) -> str:
    """Refresh token."""
    refreshed_token = await oauth_handler.get_new_access_token(
        access_token["refresh_token"]
    )
    await storage.store_access_token(refreshed_token)

    return refreshed_token["access_token"]


class HaOAuthStorageInterface(AsyncOAuthStorageInterface):
    """Storage abstraction for tokens."""

    def __init__(self, hass: HomeAssistant):
        """Init."""
        self.store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
        super().__init__()

    async def store_access_token(self, payload: dict):
        """Store access token."""
        await self.store.async_save(payload)

    async def fetch_access_token(self) -> Optional[dict]:
        """Fetch access token."""
        return await self.store.async_load()


class IoliteDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching IOLITE data."""

    def __init__(
        self,
        hass: HomeAssistant,
        web_session: ClientSession,
        username: str,
        password: str,
        storage: AsyncOAuthStorageInterface,
    ):
        """Initializer."""
        self.hass = hass
        self.web_session = web_session
        self.username = username
        self.password = password
        self.storage = storage
        self.client = None

        update_interval = timedelta(seconds=30)
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        oauth_handler = AsyncOAuthHandler(
            self.username, self.password, self.web_session
        )
        sid = await get_sid(oauth_handler, self.storage)

        self.client = Client(sid, self.username, self.password)
        await self.client.async_discover()

        rooms = {}
        for room in self.client.discovered.get_rooms():
            rooms[room.identifier] = room

        return rooms
