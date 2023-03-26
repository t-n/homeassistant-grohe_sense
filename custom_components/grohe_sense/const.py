import logging
import collections
from datetime import timedelta

from homeassistant.const import (STATE_UNAVAILABLE, STATE_UNKNOWN, TEMP_CELSIUS,
                                 DEVICE_CLASS_TEMPERATURE, PERCENTAGE, DEVICE_CLASS_HUMIDITY,
                                 VOLUME_FLOW_RATE_CUBIC_METERS_PER_HOUR, PRESSURE_MBAR,
                                 DEVICE_CLASS_PRESSURE, TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE,
                                 VOLUME_LITERS, Platform,  UnitOfTime, DEVICE_CLASS_DATE)


LOGGER = logging.getLogger(__name__)


DOMAIN = "grohe_sense"
NAME = "Grohe Sense"
MANUFACTURER = "Grohe"
VERSION = "1.1.0"

CONF_USERNAME = 'username'
CONF_PASSWORD = 'password'

PLATFORMS = ['sensor']

UNDO_UPDATE_LISTENER = "undo_update_listener"

#

GROHE_BASE_URL = 'https://idp2-apigw.cloud.grohe.com/'
BASE_URL = GROHE_BASE_URL + 'v3/iot/'


GROHE_SENSE_TYPE = 101  # Type identifier for the battery powered water detector
GROHE_SENSE_GUARD_TYPE = 103  # Type identifier for sense guard, the water guard installed on your water pipe
GROHE_BLUE_HOME_TYPE = 104  # Type identifier for Grohe Blue Home, chiled water tap

DEVICE_TYPES = {
    GROHE_BLUE_HOME_TYPE: "Grohe Blue Home",
    GROHE_SENSE_GUARD_TYPE: "Grohe Sense Guard",
    GROHE_SENSE_TYPE: "Grohe Sense",
}

SensorType = collections.namedtuple('SensorType', ['unit', 'device_class', 'function'])

SENSOR_TYPES = {
    'temperature': SensorType(TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, lambda x: x),
    'humidity': SensorType(PERCENTAGE, DEVICE_CLASS_HUMIDITY, lambda x: x),
    'flowrate': SensorType(VOLUME_FLOW_RATE_CUBIC_METERS_PER_HOUR, None, lambda x: x * 3.6),
    'pressure': SensorType(PRESSURE_MBAR, DEVICE_CLASS_PRESSURE, lambda x: x * 1000),
    'temperature_guard': SensorType(TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, lambda x: x),
    'open_close_cycles_still': SensorType(None, None, lambda x: x),
    'open_close_cycles_carbonated': SensorType(None, None, lambda x: x),
    'water_running_time_still': SensorType(UnitOfTime.MINUTES, None, lambda x: x),
    'water_running_time_medium': SensorType(UnitOfTime.MINUTES, None, lambda x: x),
    'water_running_time_carbonated': SensorType(UnitOfTime.MINUTES, None, lambda x: x),
    'remaining_filter': SensorType(None, None, lambda x: x),
    'remaining_co2': SensorType(None, None, lambda x: x),
    'date_of_filter_replacement': SensorType(None, DEVICE_CLASS_DATE, lambda x: x),
    'date_of_co2_replacement': SensorType(None, DEVICE_CLASS_DATE, lambda x: x),
    'date_of_cleaning': SensorType(None, DEVICE_CLASS_DATE, lambda x: x),
    'power_cut_count': SensorType(None, None, lambda x: x),
    'time_since_last_withdrawal': SensorType(UnitOfTime.MINUTES, None, lambda x: x),
    'filter_change_count': SensorType(None, None, lambda x: x),
    'cleaning_count': SensorType(None, None, lambda x: x)
}

SENSOR_TYPES_PER_UNIT = {
    GROHE_SENSE_TYPE: [
        'temperature',
        'humidity'
    ],
    GROHE_SENSE_GUARD_TYPE: [
        'flowrate',
        'pressure',
        'temperature_guard'
    ],
    GROHE_BLUE_HOME_TYPE: [
        'open_close_cycles_still',
        'open_close_cycles_carbonated',
        'water_running_time_still',
        'water_running_time_medium',
        'water_running_time_carbonated',
        'remaining_filter',
        'remaining_co2',
        'date_of_filter_replacement',
        'date_of_co2_replacement',
        'date_of_cleaning',
        'power_cut_count',
        'time_since_last_withdrawal',
        'filter_change_count',
        'cleaning_count'
    ]
}
# GROHE_BLUE_HOME_TYPE: [
# 'open_close_cycles_still',
# 'open_close_cycles_carbonated',
# 'water_running_time_still',
# 'water_running_time_medium',
# 'water_running_time_carbonated',
# 'operating_time',
# 'max_idle_time',
# 'pump_count',
# 'pump_running_time',
# 'remaining_filter',
# 'remaining_co2',
# 'date_of_filter_replacement',
# 'date_of_co2_replacement',
# 'date_of_cleaning',
#  'power_cut_count',
# 'time_since_restart',
# 'time_since_last_withdrawal',
# 'filter_change_count',
# 'cleaning_count' ]

NOTIFICATION_UPDATE_DELAY = timedelta(minutes=1)

NOTIFICATION_TYPES = {  # The protocol returns notification information as a (category, type) tuple, this maps to strings
    (10, 10): 'Integration successful',
    (10, 60): 'Firmware update sense',
    (10, 410): 'Integration successful guard',
    (10, 460): 'Firmware update guard',
    (10, 555): 'Blue auto flush active',
    (10, 556): 'Blue auto flush inactive',
    (10, 560): 'Firmware update blue',
    (10, 560): 'Firmware update blue professional',
    (10, 601): 'Nest awaymode automaticcontrol off',
    (10, 602): 'Nest homemode automaticcontrol off',
    (10, 557): 'Empty cartridge',
    (10, 566): 'Order partially shipped',
    (10, 561): 'Order fully shipped',
    (10, 563): 'Order fully delivered',
    (10, 559): 'Cleaning completed',
    (20, 11): 'Battery low',
    (20, 12): 'Battery empty',
    (20, 20): 'Undercut temperature threshold',
    (20, 21): 'Exceed temperature threshold',
    (20, 30): 'Undercut humidity threshold',
    (20, 31): 'Exceed humidity threshold',
    (20, 40): 'Frost sense',
    (20, 80): 'Device lost wifi to cloud sense',
    (20, 320): 'Unusual water consumption',
    (20, 321): 'Unusual water consumption no shut off',
    (20, 330): 'Micro leakage',
    (20, 332): 'Micro leakage test impossible',
    (20, 340): 'Frost guard',
    (20, 380): 'Device lost wifi to cloud guard',
    (20, 420): 'Blind spot',
    (20, 421): 'Blind spot no shut off',
    (20, 550): 'Blue filter low',
    (20, 551): 'Blue co2 low',
    (20, 580): 'Blue no connection',
    (20, 603): 'Nest noresponse guard open',
    (20, 604): 'Nest noresponse guard close',
    (20, 552): 'Empty filter blue',
    (20, 553): 'Empty co2 blue',
    (20, 564): 'Filter emptystock',
    (20, 565): 'Co2 emptystock',
    (20, 558): 'Cleaning',
    (30, 0): 'Flooding',
    (30, 310): 'Pipe break',
    (30, 400): 'Max volume',
    (30, 430): 'Triggered by sense',
    (30, 431): 'Triggered by sense no shut off',
    (30, 50): 'Sensor moved',
    (30, 90): 'system error 90',
    (30, 390): 'System error 390',
    (30, 101): 'System rtc error',
    (30, 102): 'System acceleration sensor',
    (30, 103): 'System out of service',
    (30, 104): 'System memory error',
    (30, 105): 'System relative temperature',
    (30, 106): 'System water detection error',
    (30, 107): 'System button error',
    (30, 100): 'System error',
}
