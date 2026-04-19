"""Water heater platform for clage_homeserver."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries, core
from homeassistant.components.water_heater import (
    STATE_ECO,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HEATER_ID,
    CONF_HOMESERVER_ID,
    CONF_HOMESERVER_IP_ADDRESS,
    CONF_HOMESERVERS,
    CONF_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _create_water_heater(
    hass: core.HomeAssistant,
    homeserver_name: str,
    homeserver_ip_address: str,
    homeserver_id: str,
    heater_id: str,
) -> "ClageWaterHeater":
    """Create a water heater entity for a configured homeserver."""
    return ClageWaterHeater(
        coordinator=hass.data[DOMAIN]["coordinator"],
        hass=hass,
        homeserver_name=homeserver_name,
        homeserver_ip_address=homeserver_ip_address,
        homeserver_id=homeserver_id,
        heater_id=heater_id,
    )


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
) -> None:
    """Set up Clage water heater entities from a config entry."""
    config = config_entry.as_dict()["data"]

    async_add_entities(
        [
            _create_water_heater(
                hass=hass,
                homeserver_name=config[CONF_NAME],
                homeserver_ip_address=config[CONF_HOMESERVER_IP_ADDRESS],
                homeserver_id=config[CONF_HOMESERVER_ID],
                heater_id=config[CONF_HEATER_ID],
            )
        ]
    )


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Clage water heater entities."""
    if discovery_info is None:
        return

    entities = []
    homeservers = discovery_info[CONF_HOMESERVERS]

    for homeserver in homeservers:
        homeserver_name = homeserver[0][CONF_NAME]
        entities.append(
            _create_water_heater(
                hass=hass,
                homeserver_name=homeserver_name,
                homeserver_ip_address=homeserver[0][CONF_HOMESERVER_IP_ADDRESS],
                homeserver_id=homeserver[0][CONF_HOMESERVER_ID],
                heater_id=homeserver[0][CONF_HEATER_ID],
            )
        )

    async_add_entities(entities)


class ClageWaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Representation of a CLAGE water heater."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = WaterHeaterEntityFeature.TARGET_TEMPERATURE
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 20.0
    _attr_max_temp = 60.0
    _attr_operation_list = [STATE_ECO]
    _attr_current_operation = STATE_ECO

    def __init__(
        self,
        coordinator,
        hass,
        homeserver_name: str,
        homeserver_ip_address: str,
        homeserver_id: str,
        heater_id: str,
    ) -> None:
        """Initialize the water heater."""
        super().__init__(coordinator)

        self.hass = hass
        self.homeservername = homeserver_name
        self.homeserver_ip_address = homeserver_ip_address
        self.homeserver_id = homeserver_id
        self.heater_id = heater_id

        self._attr_name = f"{homeserver_name} Water Heater"
        self._attr_unique_id = f"{homeserver_name}_water_heater"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.homeservername)},
            "name": self.homeservername,
            "manufacturer": "CLAGE GmbH",
            "model": f"DSX Touch {self.heater_id}@{self.homeserver_id}",
            "configuration_url": f"https://{self.homeserver_ip_address}",
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False

        data = self.coordinator.data.get(self.homeservername, {})
        return data.get("heater_connected", True)

    @property
    def current_temperature(self) -> float | None:
        """Return current outlet temperature."""
        data = self.coordinator.data.get(self.homeservername, {})
        return data.get("heater_status_tOut")

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        data = self.coordinator.data.get(self.homeservername, {})
        return data.get("heater_status_setpoint")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        homeserver = self.hass.data[DOMAIN]["api"][self.homeservername]

        _LOGGER.debug(
            "Setting temperature for %s to %s °C",
            self.homeservername,
            temperature,
        )

        await self.hass.async_add_executor_job(
            homeserver.setTemperature, float(temperature)
        )
        await self.coordinator.async_request_refresh()
