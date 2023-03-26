"""DataUpdateCoordinator for integration_blueprint."""
from __future__ import annotations
import asyncio
import collections
import datetime
from datetime import (datetime, timezone, timedelta)

from .oauth_session import OauthSession, TokenExpiredError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .oauth_session import (
    OauthSession,
    OauthException,
)
from .const import DOMAIN, GROHE_SENSE_TYPE, LOGGER, SENSOR_TYPES_PER_UNIT, STATE_UNKNOWN

GroheDevice = collections.namedtuple('GroheDevice', ['locationId', 'roomId', 'applianceId', 'type', 'name'])


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class GroheDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: OauthSession,
    ) -> None:
        """Initialize."""
        self.client = client
        self._data_fetch_completed = datetime.min
        self._poll_from = datetime.now(tz=timezone.utc) - timedelta(7)
        self._fetching_data = None
        self._fetching_devices = None
        self._locationId = None
        self._applianceId = None
        self._devices = None
        self._device_data = {}

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=4),
        )

    async def get_devices(self):
        return await self.async_get_devices()

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.async_get_data()
        except OauthException as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except TokenExpiredError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except Exception as exception:
            raise UpdateFailed(exception) from exception

    def consumption(self, applianceId, since):
        if self.data is not None:
            # XXX: As self._withdrawals is sorted, we could speed this up by a binary search,
            #      but most likely data sets are small enough that a linear scan is fine.
            return sum((w['waterconsumption'] for w in self.data[applianceId]['withdrawals'] if w['starttime'] >= since))
        return STATE_UNKNOWN

    def measurement(self, applianceId, key):
        if self.data is not None and key in self.data[applianceId]['measurements']:
            return self.data[applianceId]['measurements'][key]
        return STATE_UNKNOWN

    async def async_get_devices(self):

        if self._devices is not None:
            return self._devices

        if self._fetching_devices is not None:
            await self._fetching_devices.wait()
            return self._devices
        self._fetching_devices = asyncio.Event()

        devices = []
        LOGGER.debug('fetching locations')

        locations = await self.client.get_locations()
        LOGGER.debug('Found locations %s', locations)

        for location in locations:
            LOGGER.debug('Found location %s', location)
            locationId = location['id']
            rooms = await self.client.get_rooms(locationId)
            for room in rooms:
                LOGGER.debug('Found room %s', room)
                roomId = room['id']
                appliances = await self.client.get_appliances(locationId, roomId)
                for appliance in appliances:
                    LOGGER.debug('Found appliance %s', appliance)
                    applianceId = appliance['appliance_id']
                    devices.append(GroheDevice(locationId, roomId, applianceId, appliance['type'], appliance['name']))
        self._devices = devices

        self._fetching_devices.set()
        self._fetching_devices = None
        return self._devices

    async def async_get_data(self):
        if self._fetching_data is not None:
            await self._fetching_data.wait()
            return self._device_data

        # XXX: Hardcoded 15 minute interval for now. Would be prettier to set this a bit more dynamically
        # based on the json response for the sense guard, and probably hardcode something longer for the sense.
        if datetime.now() - self._data_fetch_completed < timedelta(minutes=5):
            LOGGER.debug('Skipping fetching new data, time since last fetch was only %s', datetime.now() - self._data_fetch_completed)
            return self._device_data

        self._fetching_data = asyncio.Event()
        await self.async_get_devices()

        device_data = {}
        for device in self._devices:
            device_data[device.applianceId] = await self.async_get_data_for_device(device)
        self._device_data = device_data

        self._data_fetch_completed = datetime.now()

        self._fetching_data.set()
        self._fetching_data = None

        return self._device_data

    async def async_get_data_for_device(self, device):
        data = {
            "measurements": {},
            "withdrawals": []
        }
        LOGGER.debug("Fetching new data for appliance %s", device.applianceId)

        def parse_time(s):
            # XXX: Fix for python 3.6 - Grohe emits time zone as "+HH:MM", python 3.6's %z only accepts the format +HHMM
            # So, some ugly code to remove the colon for now...
            if s.rfind(':') > s.find('+'):
                s = s[:s.rfind(':')] + s[s.rfind(':')+1:]
            return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f%z')

        poll_from = self._poll_from.strftime('%Y-%m-%d')

        measurements_response = await self.client.get_measurements_response(device.locationId, device.roomId, device.applianceId, poll_from)

        if 'withdrawals' in measurements_response['data']:
            withdrawals = measurements_response['data']['withdrawals']
            LOGGER.debug('Received %d withdrawals in response', len(withdrawals))
            for w in withdrawals:
                w['starttime'] = parse_time(w['starttime'])
            withdrawals = [w for w in withdrawals if w['starttime'] > self._poll_from]
            withdrawals.sort(key=lambda x: x['starttime'])

            LOGGER.debug('Got %d new withdrawals totaling %f volume', len(withdrawals), sum((w['waterconsumption'] for w in withdrawals)))
            data['withdrawals'] += withdrawals
            if len(data['withdrawals']) > 0:
                self._poll_from = max(self._poll_from, data['withdrawals'][-1]['starttime'])
        elif self._type != GROHE_SENSE_TYPE:
            LOGGER.info('Data response for appliance %s did not contain any withdrawals data', device.applianceId)

        if 'measurement' in measurements_response['data']:
            measurements = measurements_response['data']['measurement']
            measurements.sort(key=lambda x: x['timestamp'])
            if len(measurements):
                for key in SENSOR_TYPES_PER_UNIT[device.type]:
                    if key in measurements[-1]:
                        data['measurements'][key] = measurements[-1][key]
                self._poll_from = max(self._poll_from, parse_time(measurements[-1]['timestamp']))
        else:
            LOGGER.info('Data response for appliance %s did not contain any measurements data', device.applianceId)

        return data
