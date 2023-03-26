
from datetime import (datetime, timezone, timedelta)
from .const import LOGGER, DOMAIN, BASE_URL, NOTIFICATION_TYPES, NOTIFICATION_UPDATE_DELAY, SENSOR_TYPES, SENSOR_TYPES_PER_UNIT, GROHE_SENSE_GUARD_TYPE

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import Throttle
from homeassistant.const import (STATE_UNAVAILABLE, STATE_UNKNOWN, VOLUME_LITERS)
from homeassistant.helpers import aiohttp_client

from .entity import GroheEntity


MANUFACTURER = "Grohe"


async def async_setup_entry(hass, entry, async_add_devices):
    LOGGER.debug("Starting Grohe Sense sensor")

    entities = []
    coordinator = hass.data[DOMAIN][entry.entry_id]
    devices = await coordinator.get_devices()
    for device in devices:
        entities.append(GroheSenseNotificationEntity(coordinator, device))
        if device.type in SENSOR_TYPES_PER_UNIT:
            entities += [GroheSenseSensorEntity(coordinator, device, key) for key in SENSOR_TYPES_PER_UNIT[device.type]]
            if device.type == GROHE_SENSE_GUARD_TYPE:  # The sense guard also gets sensor entities for water flow
                entities.append(GroheSenseGuardWithdrawalsEntity(coordinator, device, 1))
                entities.append(GroheSenseGuardWithdrawalsEntity(coordinator, device, 7))
        else:
            LOGGER.warning('Unrecognized appliance %s, ignoring.', device)
    if entities:
        async_add_devices(entities)


class GroheSenseNotificationEntity(GroheEntity):
    def __init__(self, coordinator, device):
        super().__init__(coordinator, device)
        self._auth_session = coordinator.client
        self._locationId = device.locationId
        self._roomId = device.roomId
        self._applianceId = device.applianceId
        self._name = device.name
        self._notifications = []

    @property
    def unique_id(self):
        """ returns the unique id """
        return self._name + "-notifications"

    @property
    def name(self):
        return 'Notifications'

    @property
    def state(self):
        def truncate_string(l, s):
            if len(s) > l:
                return s[:l-4] + ' ...'
            return s
        return truncate_string(255, '\n'.join([NOTIFICATION_TYPES.get((n['category'], n['type']), 'Unknown notification: {}'.format(n)) for n in self._notifications]))

    @Throttle(NOTIFICATION_UPDATE_DELAY)
    async def async_update(self):
        self._notifications = await self._auth_session.get(BASE_URL + f'locations/{self._locationId}/rooms/{self._roomId}/appliances/{self._applianceId}/notifications')


class GroheSenseGuardWithdrawalsEntity(GroheEntity):
    def __init__(self, coordinator, device, days):
        super().__init__(coordinator, device)
        self._name = device.name
        self._days = days

    @property
    def unique_id(self):
        return '{}-consumption-{}-days'.format(self._name, self._days)

    @property
    def name(self):
        return 'Consumption {} day(s)'.format(self._days)

    @property
    def unit_of_measurement(self):
        return VOLUME_LITERS

    @property
    def state(self):
        if self._days == 1:  # special case, if we're averaging over 1 day, just count since midnight local time
            since = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # otherwise, it's a rolling X day average
            since = datetime.now(tz=timezone.utc) - timedelta(self._days)
        return self.coordinator.consumption(self._applianceId, since)


class GroheSenseSensorEntity(GroheEntity):
    def __init__(self, coordinator, device, key):
        super().__init__(coordinator, device)
        self._name = device.name
        self._key = key

    @property
    def unique_id(self):
        """ returns the unique id """
        return '{}-{}'.format(self._name, self._key)

    @property
    def name(self):
        return self._toCamelCase(self._key)

    @property
    def unit_of_measurement(self):
        return SENSOR_TYPES[self._key].unit

    @property
    def device_class(self):
        return SENSOR_TYPES[self._key].device_class

    @property
    def state(self):
        raw_state = self.coordinator.measurement(self._applianceId, self._key)
        if raw_state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return raw_state
        else:
            return SENSOR_TYPES[self._key].function(raw_state)
