"""Support for IOLITE heating."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from iolite_client.client import Client
from iolite_client.entity import RadiatorValve

from . import IoliteDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

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
    for valve in coordinator.data["valves"].values():
        devices.append(RadiatorValveEntity(coordinator, valve, coordinator.client))

    for device in devices:
        _LOGGER.info(f"Adding {device}")

    async_add_entities(devices)


class RadiatorValveEntity(CoordinatorEntity, ClimateEntity):
    """Map RadiatorValue to Climate entity."""

    _attr_temperature_unit: str = TEMP_CELSIUS
    _attr_target_temperature_step: float = 0.5
    _attr_hvac_modes: list = [HVAC_MODE_HEAT]
    _attr_supported_features: int = SUPPORT_FLAGS

    def __init__(self, coordinator, valve: RadiatorValve, client: Client):
        """Initialize the valve."""
        super().__init__(coordinator)
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
        await self.coordinator.async_request_refresh()

    @property
    def hvac_mode(self):
        """Return hvac operation."""
        return HVAC_MODE_HEAT

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self):
        self.valve = self.coordinator.data["valves"][self._attr_unique_id]
        self._attr_name = self.valve.name
        self._attr_current_temperature = self.valve.current_env_temp
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": self.valve.manufacturer,
        }
