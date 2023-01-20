"""Support for IOLITE heating."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_BATTERY_LEVEL, ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from iolite_client.client import Client
from iolite_client.entity import RadiatorValve, Room

from . import IoliteDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


SUPPORTED_HVAC_MODES = [
    # HVAC_MODE_OFF,
    # HVAC_MODE_HEAT
]

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup from config entry."""

    coordinator: IoliteDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Map radiator valves
    devices = []
    for room in coordinator.data.values():
        for device in room.devices.values():
            if isinstance(device, RadiatorValve):
                devices.append(
                    RadiatorValveEntity(coordinator, device, room, coordinator.client)
                )

    for device in devices:
        _LOGGER.info(f"Adding {device}")

    async_add_entities(devices)


class RadiatorValveEntity(CoordinatorEntity, ClimateEntity):
    """Map RadiatorValue to Climate entity."""

    _attr_temperature_unit: str = TEMP_CELSIUS
    _attr_target_temperature_step: float = 0.5
    _attr_hvac_modes: list = SUPPORTED_HVAC_MODES
    _attr_supported_features: int = SUPPORT_FLAGS

    def __init__(self, coordinator, valve: RadiatorValve, room: Room, client: Client):
        """Initialize the valve."""
        super().__init__(coordinator)
        self.valve = valve
        self.client = client
        self._attr_unique_id = valve.identifier
        self._attr_min_temp = 0
        self._attr_max_temp = 30
        self._attr_name = f"{self.valve.name} ({room.name})"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": self.valve.manufacturer,
        }
        self._update_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        await self.client.async_set_temp(self.valve.identifier, temperature)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    @property
    def hvac_mode(self):
        """Return hvac target hvac state."""
        if self._attr_current_temperature == self._attr_target_temperature:
            return HVAC_MODE_OFF

        return HVAC_MODE_HEAT

    def _update_state(self):
        room: Room = self.coordinator.data[self.valve.place_identifier]
        self._attr_current_temperature = room.devices[
            self.valve.identifier
        ].current_env_temp
        if room.heating:
            self._attr_target_temperature = room.heating.target_temp

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        extra_state_attributes = {
            ATTR_BATTERY_LEVEL: self.valve.battery_level,
        }

        return extra_state_attributes
