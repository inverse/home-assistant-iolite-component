"""Support for IOLITE sensors."""

import logging

from homeassistant import config_entries
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from iolite_client.entity import HumiditySensor, Room

from . import IoliteDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


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
            if isinstance(device, HumiditySensor):
                devices.append(
                    HumiditySensorEntity(coordinator, device, room)
                )
                devices.append(
                    HumidityTemperatureSensorEntity(coordinator, device, room)
                )

    for device in devices:
        _LOGGER.info(f"Adding {device}")

    async_add_entities(devices)


class HumiditySensorEntity(CoordinatorEntity, SensorEntity):
    """Map HumiditySensor humidity_level to a HA sensor entity."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self, coordinator, sensor: HumiditySensor, room: Room
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.sensor = sensor
        self._attr_unique_id = f"{sensor.identifier}_humidity"
        self._attr_name = f"{self.sensor.name} Humidity ({room.name})"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, sensor.identifier)},
            "name": self.sensor.name,
            "manufacturer": self.sensor.manufacturer,
        }
        self._update_state()

    @property
    def room(self) -> Room:
        """Return device data object from coordinator."""
        return self.coordinator.data[self.sensor.place_identifier]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self):
        """Update state from coordinator data."""
        device: HumiditySensor = self.room.devices[self.sensor.identifier]
        self._attr_native_value = device.humidity_level


class HumidityTemperatureSensorEntity(CoordinatorEntity, SensorEntity):
    """Map HumiditySensor current_env_temp to a HA sensor entity."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self, coordinator, sensor: HumiditySensor, room: Room
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.sensor = sensor
        self._attr_unique_id = f"{sensor.identifier}_temperature"
        self._attr_name = f"{self.sensor.name} Temperature ({room.name})"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, sensor.identifier)},
            "name": self.sensor.name,
            "manufacturer": self.sensor.manufacturer,
        }
        self._update_state()

    @property
    def room(self) -> Room:
        """Return device data object from coordinator."""
        return self.coordinator.data[self.sensor.place_identifier]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state()
        self.async_write_ha_state()

    def _update_state(self):
        """Update state from coordinator data."""
        device: HumiditySensor = self.room.devices[self.sensor.identifier]
        self._attr_native_value = device.current_env_temp
