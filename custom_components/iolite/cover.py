"""Support for IOLITE heating."""

import logging
import asyncio
from typing import Any

from homeassistant import config_entries
from homeassistant.components.cover import CoverEntity, ATTR_POSITION, CoverEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from iolite_client.client import Client
from iolite_client.entity import Blind, Room

from . import IoliteDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION

COVER_MIN = 0
COVER_MAX = 100


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: config_entries.ConfigEntry,
        async_add_entities,
):
    """Setup from config entry."""

    coordinator: IoliteDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    devices = []
    for room in coordinator.data.values():
        for device in room.devices.values():
            if isinstance(device, Blind):
                devices.append(
                    BlindEntity(coordinator, device, room, coordinator.client)
                )

    for device in devices:
        _LOGGER.info(f"Adding {device}")

    async_add_entities(devices)


# Failed to call service climate/set_temperature. asyncio.run() cannot be called from a running event loop

class BlindEntity(CoordinatorEntity, CoverEntity):
    """Map RadiatorValue to Climate entity."""

    _attr_current_position: int = COVER_MIN
    _attr_supported_features: int = SUPPORT_FLAGS

    def __init__(self, coordinator, blind: Blind, room: Room, client: Client):
        super().__init__(coordinator)
        self.blind = blind
        self.client = client
        self._attr_unique_id = blind.identifier
        self._attr_name = f"{self.blind.name} ({room.name})"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": self.blind.manufacturer,
        }

    @property
    def room(self) -> Room:
        """Return device data object from coordinator."""
        return self.coordinator.data[self.blind.place_identifier]

    @property
    def current_cover_position(self):
        blind: Blind = self.room.devices[self.blind.identifier]
        return (100 - blind.blind_level)

    @property
    def is_closed(self) -> bool:
        blind: Blind = self.room.devices[self.blind.identifier]
        return (100 - blind.blind_level) == COVER_MIN

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        position = kwargs.get(ATTR_POSITION)
        if position is None:
            return

        await self.client.async_set_property(self.blind.identifier, 'blindLevel', 100 - position)
        await asyncio.sleep(35)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        await self.client.async_set_property(self.blind.identifier, 'blindLevel', COVER_MAX)
        await asyncio.sleep(35)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs):
        await self.client.async_set_property(self.blind.identifier, 'blindLevel', COVER_MIN)
        await asyncio.sleep(35)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
