from .const import DOMAIN, BASE_URL, GROHE_SENSE_GUARD_TYPE, GROHE_BLUE_HOME_TYPE, LOGGER
from homeassistant.const import (STATE_UNKNOWN)
from homeassistant.util import Throttle
from homeassistant.components.switch import SwitchEntity
from datetime import (timedelta)


VALVE_UPDATE_DELAY = timedelta(minutes=1)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    LOGGER.debug("Starting Grohe Sense valve switch")
    auth_session = hass.data[DOMAIN]['session']
    entities = []

    for device in filter(lambda d: d.type == GROHE_SENSE_GUARD_TYPE, hass.data[DOMAIN]['devices']):
        entities.append(GroheSenseGuardValve(auth_session, device.locationId, device.roomId, device.applianceId, device.name))
    if entities:
        async_add_entities(entities)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    LOGGER.debug("Starting Grohe Blue Home tap")
    auth_session = hass.data[DOMAIN]['session']
    entities = []

    for device in filter(lambda d: d.type == GROHE_BLUE_HOME_TYPE, hass.data[DOMAIN]['devices']):
        entities.append(GroheBlueHomeTap(auth_session, device.locationId, device.roomId, device.applianceId, device.name))
    if entities:
        async_add_entities(entities)


class GroheSenseGuardValve(SwitchEntity):
    def __init__(self, auth_session, locationId, roomId, applianceId, name):
        self._auth_session = auth_session
        self._locationId = locationId
        self._roomId = roomId
        self._applianceId = applianceId
        self._name = name
        self._is_on = STATE_UNKNOWN

    @property
    def name(self):
        return '{} valve'.format(self._name)

    @property
    def is_on(self):
        return self._is_on

    @property
    def icon(self):
        return 'mdi:water'

    @property
    def device_class(self):
        return 'switch'

    @Throttle(VALVE_UPDATE_DELAY)
    async def async_update(self):
        command_response = await self._auth_session.get(BASE_URL + f'locations/{self._locationId}/rooms/{self._roomId}/appliances/{self._applianceId}/command')
        if 'command' in command_response and 'valve_open' in command_response['command']:
            self._is_on = command_response['command']['valve_open']
        else:
            LOGGER.error('Failed to parse out valve_open from commands response: %s', command_response)

    async def _set_state(self, state):
        data = {'type': GROHE_SENSE_GUARD_TYPE, 'command': {'valve_open': state}}
        command_response = await self._auth_session.post(BASE_URL + f'locations/{self._locationId}/rooms/{self._roomId}/appliances/{self._applianceId}/command', data)
        if 'command' in command_response and 'valve_open' in command_response['command']:
            self._is_on = command_response['command']['valve_open']
        else:
            LOGGER.warning('Got unknown response back when setting valve state: %s', command_response)

    async def async_turn_on(self, **kwargs):
        LOGGER.info('Turning on water for %s', self._name)
        await self._set_state(True)

    async def async_turn_off(self, **kwargs):
        LOGGER.info('Turning off water for %s', self._name)
        await self._set_state(False)


class GroheBlueHomeTap(SwitchEntity):
    def __init__(self, auth_session, locationId, roomId, applianceId, name):
        self._auth_session = auth_session
        self._locationId = locationId
        self._roomId = roomId
        self._applianceId = applianceId
        self._name = name
        self._is_on = STATE_UNKNOWN

    @property
    def name(self):
        return '{} valve'.format(self._name)

    @property
    def is_on(self):
        return self._is_on

    @property
    def icon(self):
        return 'mdi:water'

    @property
    def device_class(self):
        return 'switch'

    @Throttle(VALVE_UPDATE_DELAY)
    async def async_update(self):
        command_response = await self._auth_session.get(BASE_URL + f'locations/{self._locationId}/rooms/{self._roomId}/appliances/{self._applianceId}/command')
        if 'command' in command_response and 'valve_open' in command_response['command']:
            self._is_on = command_response['command']['valve_open']
        else:
            self._is_on = False
            LOGGER.error('Failed to parse out valve_open from commands response: %s', command_response)

    async def _set_state(self, state):
        data = {'command': {'tap_type': 1, "tap_amount": 20}}
        command_response = await self._auth_session.post(BASE_URL + f'locations/{self._locationId}/rooms/{self._roomId}/appliances/{self._applianceId}/command', data)
        if 'command' in command_response and 'valve_open' in command_response['command']:
            self._is_on = command_response['command']['valve_open']
        else:
            LOGGER.warning('Got unknown response back when setting valve state: %s', command_response)

    async def async_turn_on(self, **kwargs):
        LOGGER.info('Turning on water for %s', self._name)
        await self._set_state(True)

    async def async_turn_off(self, **kwargs):
        LOGGER.info('Turning off water for %s', self._name)
        await self._set_state(False)
