"""GroheEntity class"""

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPES, LOGGER, MANUFACTURER, DOMAIN, NAME, VERSION, STATE_UNKNOWN


class GroheEntity(CoordinatorEntity):
    def __init__(self, coordinator, device):
        super().__init__(coordinator)
        self._locationId = device.locationId
        self._roomId = device.roomId
        self._applianceId = device.applianceId
        self._type = device.type
        self._name = device.name

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return self._applianceId

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._applianceId)},
            "name": NAME,
            "model": DEVICE_TYPES[self._type],
            "manufacturer": MANUFACTURER,
        }

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            "id": str(self._applianceId),
            "integration": DOMAIN,
        }

    def applianceId(self):
        """ returns the appliance Identifier, looks like a UUID, so hopefully unique """
        return self._applianceId

    @property
    def name(self):
        """ returns the name """
        return self._name

    def _toCamelCase(self, word):
        return ' '.join(x.capitalize() or '_' for x in word.split('_'))
