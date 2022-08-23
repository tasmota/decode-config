#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
METADATA = {
    'VERSION': '12.1.0.0',
    'DESCRIPTION': 'Backup/restore and decode configuration tool for Tasmota',
    'CLASSIFIER': 'Development Status :: 5 - Production/Stable',
    'URL': 'https://github.com/tasmota/decode-config',
    'AUTHOR': 'Norbert Richter',
    'AUTHOR_EMAIL': 'nr@prsolution.eu',
}

"""
    decode-config.py - Backup/Restore Tasmota configuration data

    Copyright (C) 2022 Norbert Richter <nr@prsolution.eu>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


Requirements:
    - Python 3.x and Pip:
        sudo apt-get install python3 python3-pip

Installation:
    - Using pypi:
        python -m pip install decode-config
    - Manually:
        python -m pip install -r requirements.txt

Instructions:
    Execute decode-config with option -d <host|url> to retrieve config data
    from a Tasmota host or use -f <configfile.dmp> to read the configuration
    data from a file previously saved using Tasmota Web-UI

    For further information see 'README.md'

    For help execute command with argument -h (or -H for advanced help)

Returns:
    0: successful
    1: restore skipped
    2: program argument error
    3: file not found
    4: data size mismatch
    5: data CRC error
    6: unsupported configuration version
    7: configuration file read error
    8: JSON file decoding error
    9: restore file data error
    10: device data download error
    11: device data upload error
    12: invalid configuration data
    20: python module missing
    21: internal error
    22: HTTP connection error
    23: MQTT connection error
    >23: python library exit code
    4xx, 5xx: HTTP errors
"""

class ExitCode:
    """
    Program return codes
    """
    OK = 0
    RESTORE_SKIPPED = 1
    ARGUMENT_ERROR = 2
    FILE_NOT_FOUND = 3
    DATA_SIZE_MISMATCH = 4
    DATA_CRC_ERROR = 5
    UNSUPPORTED_VERSION = 6
    FILE_READ_ERROR = 7
    JSON_READ_ERROR = 8
    RESTORE_DATA_ERROR = 9
    DOWNLOAD_CONFIG_ERROR = 10
    UPLOAD_CONFIG_ERROR = 11
    INVALID_DATA = 12
    MODULE_NOT_FOUND = 20
    INTERNAL_ERROR = 21
    HTTP_CONNECTION_ERROR = 22
    MQTT_CONNECTION_ERROR = 23
    STR = [
        'OK',
        'Restore skipped',
        'Parameter error',
        'File not found',
        'Data size mismatch',
        'Data CRC error',
        'Unsupported version',
        'File read error',
        'JSON read error',
        'Restore data error',
        'Download error',
        'Upload error',
        'Invaid data',
        '', '', '', '', '', '', '',
        'Module not found',
        'Internal error',
        'HTTP connection error',
        'MQTT connection error'
        ]
    @staticmethod
    def str(code):
        """
        Program return string by code

        @param: code
            int number of code
        """
        if 0 <= code < len(ExitCode.STR):
            return ExitCode.STR[code]
        return ''

# ======================================================================
# imports
# ======================================================================
def module_import_error(module):
    """
    Module import error helper
    """
    errstr = str(module)
    print('{}, try "python -m pip install {}"'.format(errstr, errstr.split(' ')[len(errstr.split(' '))-1]), file=sys.stderr)
    sys.exit(ExitCode.MODULE_NOT_FOUND)
# pylint: disable=wrong-import-position
import os.path
import sys
if sys.version_info[0] < 3:
    print('Unsupported python version {}.{}.{} (EOL) - python 3.x required!'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2]), file=sys.stderr)
    sys.exit(ExitCode.UNSUPPORTED_VERSION)
import platform
try:
    from datetime import datetime
    import base64
    import time
    import copy
    import struct
    import socket       # pylint: disable=unused-import
    import re
    import inspect
    import itertools
    import json
    import configargparse
    import requests
    import urllib
    import codecs
    import textwrap
    import hashlib
except ImportError as err:
    module_import_error(err)
try:
    from paho.mqtt import client as mqtt
    MQTT_MODULE = True
except ImportError:
    MQTT_MODULE = False
try:
    import ssl
    SSL_MODULE = True
except ImportError:
    SSL_MODULE = False

# pylint: enable=wrong-import-position

# ======================================================================
# globals
# ======================================================================
METADATA['BUILD'] = ''
METADATA['VERSION_BUILD'] = METADATA['VERSION']
try:
    SHA256 = hashlib.sha256()
    FNAME = sys.argv[0]
    if not os.path.isfile(FNAME):
        FNAME += '.exe'
    with open(FNAME, "rb") as fp:
        for block in iter(lambda: fp.read(4096), b''):
            SHA256.update(block)
        METADATA['BUILD'] = SHA256.hexdigest()[:7]
        METADATA['VERSION_BUILD'] = METADATA['VERSION'] + ' [' + METADATA['BUILD'] + ']'
except:     # pylint: disable=bare-except
    pass

PROG = '{} v{} by {} {}'.format(os.path.basename(sys.argv[0]), METADATA['VERSION_BUILD'], METADATA['AUTHOR'], METADATA['AUTHOR_EMAIL'])

# Tasmota constant
CONFIG_FILE_XOR = 0x5A
BINARYFILE_MAGIC = 0x63576223
MAX_BACKLOG = 30
MAX_BACKLOGLEN = 320
MQTT_MESSAGE_MAX_SIZE = 700
MQTT_TIMEOUT = 5000
MQTT_FILETYPE = 2

# decode-config constant
STR_CODING = 'utf-8'
HIDDEN_PASSWORD = '********'
INTERNAL = 'Internal'
VIRTUAL = '*'
SETTINGVAR = '$SETTINGVAR'
SIMULATING = "* Simulating "

DEFAULT_PORT_HTTP = 80
DEFAULT_PORT_HTTPS = 443
DEFAULT_PORT_MQTT = 1883
DEFAULT_PORT_MQTTS = 8883

DEFAULTS = {
    'source':
    {
        'source':       None,
        'filesource':   None,
        'httpsource':   None,
        'mqttsource':   None,
        'port':         None,
        'username':     'admin',
        'password':     None,
        'fulltopic':    '',
        'cafile':       None,
        'certfile':     None,
        'keyfile':      None,
        'insecure':     False,
        'keepalive':    60,
    },
    'backup':
    {
        'restorefile':  None,
        'backupfile':   None,
        'backupfileformat': 'json',
        'extension':    True,
        'forcerestore': False,
    },
    'jsonformat':
    {
        'indent':       None,
        'compact':      False,
        'sort':         True,
        'hidepw':       False,
    },
    'cmndformat':
    {
        'indent':       2,
        'group':        True,
        'sort':         True,
        'useruleconcat': False,
        'usebacklog':   False,
    },
    'common':
    {
        'output':       False,
        'outputformat': 'json',
        'configfile':   None,
        'dryrun':       False,
        'ignorewarning':False,
        'filter':       None,
    },
}

PARSER = None
ARGS = {}
CONFIG = {}
EXIT_CODE = 0

# ======================================================================
# Settings mapping
# ======================================================================
"""
Settings dictionary

The Tasmota permanent setttings are stored in binary format using
'struct SYSCFG' defined in tasmota/settings.h.

decode-config handles the binary data described by this Settings
dictionary. The processing from/to Tasmota configuration data is
based on this dictionary.


    <setting> = { <name> : <def> }

    <name>: "string"
        key (string)
        for simply identifying value from Tasmota configuration this key has the same
        name as the structure element of tasmota/settings.h

    <def>:  ( <hardware>, <format>, <addrdef>, <datadef> [,<converter>] )
        tuple with 4 or 5 objects which describes the format, address and structure
        of the binary source.
        For optional values there are two possibilities: If the definition object is
        mandatory it could be None, for none-mandatory optional objects it can be omit.

            <hardware>: <int>
                hardware bitmask validation
                determines whether the setting is valid for a specific ESP platform (1) or not (0)

            <format>:   <formatstring> | <setting>
                data type & format definition

                <formatstring>: <string>
                    defines the use of data at <addrdef>
                    format is defined in 'struct module format string'
                    see
                    https://docs.python.org/3.8/library/struct.html#format-strings
                <setting>:      <setting>
                    A dictionary describes a (sub)setting dictonary
                    and can recursively define another <setting>


            <addrdef>:  <baseaddr> | (<baseaddr>, <bits>, <bitshift>) | (<baseaddr>, <strindex>)
                address definition

                <baseaddr>: <uint>
                    The address (starting from 0) within binary config data.

                <bits>:     <uint>
                    number of bits used (positive integer)

                <bitshift>: <int>
                    bit shift <bitshift>:
                    <bitshift> >= 0: shift the result right
                    <bitshift> <  0: shift the result left

                <strindex>: <str>
                    name of the index into a set of strings delimited by \0
                    This will be dynamically extracted from the corresponding hardware index array for strings


            <datadef>:  <arraydef> | (<arraydef>, <validate> [,cmd])
                data definition

                <arraydef>: None | <dim> | [<dim>] | [<dim> ,<dim>...]
                    None:
                        single value
                    <dim>:  <uint>

                    [<dim>]
                        a one-dimensional array of size <n>

                    [<dim> ,<dim>...]
                        a one- or multi-dimensional array

                <validate>: None | <function>
                    value validation function

                <cmd>:  (<group>, <tasmotacmnd>) - optional
                    Tasmota command definition

                    <group>:        <string>
                        command group
                        There exists two special group names
                        INTERNAL - processed but invisible in group output
                        VIRTUAL  - must be used as group name for nested
                                   dict definition - invisible in group output

                    <tasmotacmnd>:   <function> | (<function>,...)
                        convert function into Tasmota cmnd function


            <converter>:    <readconverter> | (<readconverter>, <writeconverter>) -
                read/write converter

                <readconverter>:    None | False | <function>
                    Will be used in bin2mapping to convert values read
                    from the binary data object into mapping dictionary
                    None
                        indicates no read conversion
                    False
                        False indicates the value will be ignored
                    <function>
                        to convert value from binary object to JSON.
                        Can also return None|False with the same result
                        as using the constant above.

                <writeconverter>:   None | False | <function>
                    Will be used in mapping2bin to convert values read
                    from mapping dictionary before write to binary
                    data object
                    None
                        indicates no write conversion
                    False
                        False indicates the value is readonly and is not
                        written back into the binary Tasmota data.
                    <function>
                        to convert value from JSON back to binary object.
                        Can also return None|False with the same result
                        as using the constant above.


        Common definitions

        <function>: <functionname> | <string> | None
            the name of an object to be called or a string to be evaluated

            <functionname>:
                <functionname> will be called with one or three parameter:
                if <arraydef> is None:
                    functionname(<value>)
                if <arraydef> is any <dim>:
                    functionname(<value>, <index>)

                <value>
                    setting value to be processed
                <index>
                    if <arraydef> is a one-dimensional array
                        int array index (starting from 0)
                    if <arraydef> is a multi-dimensional array
                        [int,int(,int...)]
                        array of current index (starting from 0)

            <string>
                A string will be evaluate as is. The following placeholder
                can be used for runtime replacements:
                '$':
                    will be replaced by the object mapping value
                '@':
                    can be used to reference another mapping value
                '#': (for <tasmotacmnd> only)
                    will be replace by
                    - int array index (<arraydef> is a one-dimensional)
                    - array of int array indexes (<arraydef> is a multi-dimensional)


        <string>:   'string' | "string"
            characters enclosed by ' or "

        <int>:      integer
             integer number in the range -2147483648 through 2147483647

        <uint>:     unsigned integer
             integer number in the range 0 through 4294967295

"""
# ----------------------------------------------------------------------
# Settings helper
# ----------------------------------------------------------------------
def passwordread(value):
    """
    Password read helper
    """
    return HIDDEN_PASSWORD if ARGS.jsonhidepw else value

def passwordwrite(value):
    """
    Password write helper
    """
    return None if value == HIDDEN_PASSWORD else value

def scriptread(value):
    """
    Scripter config helper to read script
    """
    if CONFIG['valuemapping'].get('scripting_used', 0) == 1:
        if CONFIG['valuemapping'].get('scripting_compressed', 0) == 1:
            # uncompressed compressed string
            uncompressed_data = bytearray(3072)
            compressed = bytes.fromhex(value)
            try:
                Unishox().decompress(compressed, len(compressed), uncompressed_data, len(uncompressed_data))
            except:     # pylint: disable=bare-except
                return value
            try:
                uncompressed_str = str(uncompressed_data, STR_CODING).split('\x00')[0]
            except UnicodeDecodeError as err:
                exit_(ExitCode.INVALID_DATA, "Compressed string - {}:\n                   {}".format(err, err.args[1]), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))
                uncompressed_str = str(uncompressed_data, STR_CODING, 'backslashreplace').split('\x00')[0]
            return uncompressed_str
        return value
    return False

def scriptwrite(value):
    """
    Scripter config helper to write script
    """
    if CONFIG['valuemapping'].get('scripting_used', 0) == 1:
        if CONFIG['valuemapping'].get('scripting_compressed', 0) == 1:
            # compressed uncompressed string
            fielddef = CONFIG['info']['template'].get('script', None)
            if fielddef is None:
                print("wrong setting for 'script'", file=sys.stderr)
                raise SyntaxError('SETTING error')
            compressed_data = bytearray(get_fieldlength(fielddef))
            if isinstance(value, str):
                uncompressed_data = bytes(value, STR_CODING)
            else:
                uncompressed_data = value
            Unishox().compress(uncompressed_data, len(uncompressed_data), compressed_data, len(compressed_data))
            index0 = compressed_data.find(b'\x00')
            if index0 >= 0:
                compressed_data = compressed_data[:index0]
            return compressed_data
        return value
    return False

def isscript(value):
    """
    Rules config helper
    """
    if CONFIG['valuemapping'].get('scripting_used', 0) == 1:
        return value
    return False

def rulesread(value):
    """
    Scripter config helper to read rules
    """
    if CONFIG['valuemapping'].get('scripting_used', 0) == 0:
        # check if string is compressed
        if len(value) > 2 and value[0] == '\x00':
            # uncompress string
            uncompressed_data = bytearray(3072)
            compressed = bytes.fromhex(value[3:])
            try:
                Unishox().decompress(compressed, len(compressed), uncompressed_data, len(uncompressed_data))
            except:     # pylint: disable=bare-except
                return value
            try:
                uncompressed_str = str(uncompressed_data, STR_CODING).split('\x00')[0]
            except UnicodeDecodeError as err:
                exit_(ExitCode.INVALID_DATA, "Compressed string - {}:\n                   {}".format(err, err.args[1]), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))
                uncompressed_str = str(uncompressed_data, STR_CODING, 'backslashreplace').split('\x00')[0]
            return uncompressed_str

        # return origin str
        return value

    # scripting is enabled, rule space used for script so rule is invalid and disabled
    return False

def ruleswrite(value):
    """
    Scripter config helper to write rules

    compression for Rules, depends on 'compress_rules_cpu' (SetOption93)

    If `SetOption93 0`
      Rule[x][] = 511 char max NULL terminated string (512 with trailing NULL)
      Rule[x][0] = 0 if the Rule<x> is empty
      New: in case the string is empty we also enforce:
      Rule[x][1] = 0   (i.e. we have two conseutive NULLs)

    If `SetOption93 1`
      If the rule is smaller than 511, it is stored uncompressed. Rule[x][0] is not null.
      If the rule is empty, Rule[x][0] = 0 and Rule[x][1] = 0;
      If the rule is bigger than 511, it is stored compressed
         The first byte of each Rule is always NULL.
         Rule[x][0] = 0,  if firmware is downgraded, the rule will be considered as empty

         The second byte contains the size of uncompressed rule in 8-bytes blocks (i.e. (len+7)/8 )
         Maximum rule size is 2KB (2048 bytes per rule), although there is little chances compression ratio will go down to 75%
         Rule[x][1] = size uncompressed in dwords. If zero, the rule is empty.

         The remaining bytes contain the compressed rule, NULL terminated
    """
    if CONFIG['valuemapping'].get('scripting_used', 0) == 0:
        fielddef = CONFIG['info']['template'].get('rules', None)
        if fielddef is None:
            print("wrong setting for 'rule'", file=sys.stderr)
            raise SyntaxError('SETTING error')
        try:
            subfielddef = get_subfielddef(fielddef)
            length = get_fieldlength(subfielddef)
        except:     # pylint: disable=bare-except
            length = 512
        # check if string should be compressed
        try:
            possible_compress = CONFIG['info']['template']['flag4'][1]['compress_rules_cpu']
        except:     # pylint: disable=bare-except
            possible_compress = False
        if possible_compress and len(value) > 0 and value[0] != '\x00' and len(value) >= length:
            # compressed uncompressed string
            compressed_data = bytearray(length)
            if isinstance(value, str):
                uncompressed_data = bytes(value, STR_CODING)
            else:
                uncompressed_data = value
            try:
                Unishox().compress(uncompressed_data, len(uncompressed_data), compressed_data, len(compressed_data))
                index0 = compressed_data.find(b'\x00')
                if index0 >= 0:
                    compressed_data = compressed_data[:index0]
            except:     # pylint: disable=bare-except
                return value

            return b'\x00' + struct.pack("B", int((len(value)+7)/8)) + compressed_data

        if len(value) == 0:
            return b'\x00\x00'

        # return origin str
        return value

    # scripting is enabled, rule space used for script so rule is invalid and disabled
    return False

# ----------------------------------------------------------------------
# Tasmota configuration data definition
# ----------------------------------------------------------------------
# global objects used by eval(<tasmotacmnd>)
SETTING_OBJECTS = {
    'socket': socket,
    'struct': struct,
    'time': time,
    'textwrap': textwrap
}

class Hardware:
    """
    ESPxx configuration data hardware class
    """
    # Bit mask for supported hardware
    ESP82       = 0b00000001        # All ESP82xx
    ESP32ex     = 0b00000010        # ESP32 excluding S3/S2/C3
    ESP82_32ex  = 0b00000011        # ESP82xx + ESP32 excluding ESP32 S3/S2/C3
    ESP32S3     = 0b00000100        # ESP32S3
    ESP32S2     = 0b00001000        # ESP32S2
    ESP32C3     = 0b00010000        # ESP32C3
    ESP32       = 0b00011110        # All ESP32
    ESP         = 0b11111111        # All ESP

    # Hardware bitmask and description
    config = (
        (ESP82,         "ESP82"),
        (ESP32ex,       "ESP32 (excl S3/S2/C3)"),
        (ESP82_32ex,    "ESP82/32 (excl ESP32S3/S2/C3)"),
        (ESP32S3,       "ESP32S3"),
        (ESP32,         "ESP32"),
        (ESP,           "ESP82/32")
    )

    # Tasmota config_version values
    config_versions = (ESP82, ESP32ex, ESP32S3, ESP32S2, ESP32C3)

    def get_bitmask(self, config_version):
        """
        Get hardware bitmask based on Tasmota config_version
        """
        try:
            return self.config_versions[config_version]
        except:     # pylint: disable=bare-except
            return self.ESP

    def hstr(self, setting_hardware):
        """
        Create an dict index string based on hardware

        @param setting_hardware:
            hardware definition value from setting

        @return:
            dict index string
        """
        try:
            return 'TEXTINDEX_'+self.config[[hw[0] for hw in self.config].index(setting_hardware)][1]
        except:     # pylint: disable=bare-except
            return 'TEXTINDEX_'+self.config[len(self.config)-1][1]

    def str(self, config_version):
        """
        Create hardware string

        @param config_version:
            config_version vvalue from Tasmota configuration

        @return:
            hardware string
        """
        hardware = self.get_bitmask(config_version)
        try:
            return self.config[[hw[0] for hw in self.config].index(hardware)][1]
        except:     # pylint: disable=bare-except
            return self.config[len(self.config)-1][1]

    def match(self, setting_hardware, config_version):
        """
        Test match of setting hardware with config data from Tasmota

        @param setting_hardware:
            hardware definition value from setting

        @param config_version:
            config_version vvalue from Tasmota configuration

        @return:
            True if setting hardware matchs Tasmota configuration data
        """
        return (setting_hardware & self.get_bitmask(config_version)) != 0

HARDWARE = Hardware()

# pylint: disable=bad-continuation,bad-whitespace
SETTING_5_10_0 = {
                                   # <hardware>, <format>, <addrdef>,    <datadef>                                                      [,<converter>]
    'cfg_holder':                   (HARDWARE.ESP,   '<L',  0x000,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
    'save_flag':                    (HARDWARE.ESP,   '<L',  0x004,       (None, None,                           (INTERNAL,      None)), (None,      False) ),
    'version':                      (HARDWARE.ESP,   '<L',  0x008,       (None, None,                           ('System',      None)), ('hex($)',  False) ),
    'bootcount':                    (HARDWARE.ESP,   '<L',  0x00C,       (None, None,                           ('System',      None)), (None,      False) ),
    'flag':                         (HARDWARE.ESP, {
        'save_state':               (HARDWARE.ESP,   '<L', (0x010,1, 0), (None, None,                           ('SetOption',   '"SetOption0 {}".format($)')) ),
        'button_restrict':          (HARDWARE.ESP,   '<L', (0x010,1, 1), (None, None,                           ('SetOption',   '"SetOption1 {}".format($)')) ),
        'value_units':              (HARDWARE.ESP,   '<L', (0x010,1, 2), (None, None,                           ('SetOption',   '"SetOption2 {}".format($)')) ),
        'mqtt_enabled':             (HARDWARE.ESP,   '<L', (0x010,1, 3), (None, None,                           ('SetOption',   '"SetOption3 {}".format($)')) ),
        'mqtt_response':            (HARDWARE.ESP,   '<L', (0x010,1, 4), (None, None,                           ('SetOption',   '"SetOption4 {}".format($)')) ),
        'mqtt_power_retain':        (HARDWARE.ESP,   '<L', (0x010,1, 5), (None, None,                           ('MQTT',        '"PowerRetain {}".format($)')) ),
        'mqtt_button_retain':       (HARDWARE.ESP,   '<L', (0x010,1, 6), (None, None,                           ('MQTT',        '"ButtonRetain {}".format($)')) ),
        'mqtt_switch_retain':       (HARDWARE.ESP,   '<L', (0x010,1, 7), (None, None,                           ('MQTT',        '"SwitchRetain {}".format($)')) ),
        'temperature_conversion':   (HARDWARE.ESP,   '<L', (0x010,1, 8), (None, None,                           ('SetOption',   '"SetOption8 {}".format($)')) ),
        'mqtt_sensor_retain':       (HARDWARE.ESP,   '<L', (0x010,1, 9), (None, None,                           ('MQTT',        '"SensorRetain {}".format($)')) ),
        'mqtt_offline':             (HARDWARE.ESP,   '<L', (0x010,1,10), (None, None,                           ('SetOption',   '"SetOption10 {}".format($)')) ),
        'button_swap':              (HARDWARE.ESP,   '<L', (0x010,1,11), (None, None,                           ('SetOption',   '"SetOption11 {}".format($)')) ),
        'stop_flash_rotate':        (HARDWARE.ESP,   '<L', (0x010,1,12), (None, None,                           ('SetOption',   '"SetOption12 {}".format($)')) ),
        'button_single':            (HARDWARE.ESP,   '<L', (0x010,1,13), (None, None,                           ('SetOption',   '"SetOption13 {}".format($)')) ),
        'interlock':                (HARDWARE.ESP,   '<L', (0x010,1,14), (None, None,                           ('SetOption',   '"SetOption14 {}".format($)')) ),
        'pwm_control':              (HARDWARE.ESP,   '<L', (0x010,1,15), (None, None,                           ('SetOption',   '"SetOption15 {}".format($)')) ),
        'ws_clock_reverse':         (HARDWARE.ESP,   '<L', (0x010,1,16), (None, None,                           ('SetOption',   '"SetOption16 {}".format($)')) ),
        'decimal_text':             (HARDWARE.ESP,   '<L', (0x010,1,17), (None, None,                           ('SetOption',   '"SetOption17 {}".format($)')) ),
                                    },                      0x010,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
    'save_data':                    (HARDWARE.ESP,   '<h',  0x014,       (None, '0 <= $ <= 3600',               ('Management',  '"SaveData {}".format($)')) ),
    'timezone':                     (HARDWARE.ESP,   'b',   0x016,       (None, '-13 <= $ <= 13 or $==99',      ('Management',  '"Timezone {}".format($)')) ),
    'ota_url':                      (HARDWARE.ESP,   '101s',0x017,       (None, None,                           ('Management',  '"OtaUrl {}".format($)')) ),
    'mqtt_prefix':                  (HARDWARE.ESP,   '11s', 0x07C,       ([3],  None,                           ('MQTT',        '"Prefix{} {}".format(#+1,$)')) ),
    'seriallog_level':              (HARDWARE.ESP,   'B',   0x09E,       (None, '0 <= $ <= 5',                  ('Management',  '"SerialLog {}".format($)')) ),
    'sta_config':                   (HARDWARE.ESP,   'B',   0x09F,       (None, '0 <= $ <= 5',                  ('Wifi',        '"WifiConfig {}".format($)')) ),
    'sta_active':                   (HARDWARE.ESP,   'B',   0x0A0,       (None, '0 <= $ <= 1',                  ('Wifi',        '"AP {}".format($)')) ),
    'sta_ssid':                     (HARDWARE.ESP,   '33s', 0x0A1,       ([2],  None,                           ('Wifi',        '"SSId{} {}".format(#+1,$)')) ),
    'sta_pwd':                      (HARDWARE.ESP,   '65s', 0x0E3,       ([2],  None,                           ('Wifi',        '"Password{} {}".format(#+1,$)')), (passwordread, passwordwrite) ),
    'hostname':                     (HARDWARE.ESP,   '33s', 0x165,       (None, None,                           ('Wifi',        '"Hostname {}".format($)')) ),
    'syslog_host':                  (HARDWARE.ESP,   '33s', 0x186,       (None, None,                           ('Management',  '"LogHost {}".format($)')) ),
    'syslog_port':                  (HARDWARE.ESP,   '<H',  0x1A8,       (None, '1 <= $ <= 32766',              ('Management',  '"LogPort {}".format($)')) ),
    'syslog_level':                 (HARDWARE.ESP,   'B',   0x1AA,       (None, '0 <= $ <= 4',                  ('Management',  '"SysLog {}".format($)')) ),
    'webserver':                    (HARDWARE.ESP,   'B',   0x1AB,       (None, '0 <= $ <= 2',                  ('Wifi',        '"WebServer {}".format($)')) ),
    'weblog_level':                 (HARDWARE.ESP,   'B',   0x1AC,       (None, '0 <= $ <= 4',                  ('Management',  '"WebLog {}".format($)')) ),
    'mqtt_fingerprint':             (HARDWARE.ESP,   'B',   0x1AD,       ([60], None,                           ('MQTT',        '"MqttFingerprint {}".format(" ".join("{:02X}".format(c) for c in @["mqtt_fingerprint"]))')), '"0x{:02x}".format($)' ),
    'mqtt_host':                    (HARDWARE.ESP,   '33s', 0x1E9,       (None, None,                           ('MQTT',        '"MqttHost {}".format($)')) ),
    'mqtt_port':                    (HARDWARE.ESP,   '<H',  0x20A,       (None, None,                           ('MQTT',        '"MqttPort {}".format($)')) ),
    'mqtt_client':                  (HARDWARE.ESP,   '33s', 0x20C,       (None, None,                           ('MQTT',        '"MqttClient {}".format($)')) ),
    'mqtt_user':                    (HARDWARE.ESP,   '33s', 0x22D,       (None, None,                           ('MQTT',        '"MqttUser {}".format($)')) ),
    'mqtt_pwd':                     (HARDWARE.ESP,   '33s', 0x24E,       (None, None,                           ('MQTT',        '"MqttPassword {}".format($)')), (passwordread, passwordwrite) ),
    'mqtt_topic':                   (HARDWARE.ESP,   '33s', 0x26F,       (None, None,                           ('MQTT',        '"Topic {}".format($)')) ),
    'button_topic':                 (HARDWARE.ESP,   '33s', 0x290,       (None, None,                           ('MQTT',        '"ButtonTopic {}".format($)')) ),
    'mqtt_grptopic':                (HARDWARE.ESP,   '33s', 0x2B1,       (None, None,                           ('MQTT',        '"GroupTopic {}".format($)')) ),
    'mqtt_fingerprinth':            (HARDWARE.ESP,   'B',   0x2D2,       ([20], None,                           ('MQTT',        None)) ),
    'pwm_frequency':                (HARDWARE.ESP,   '<H',  0x2E6,       (None, '$==1 or 100 <= $ <= 4000',     ('Management',  '"PwmFrequency {}".format($)')) ),
    'power':                        (HARDWARE.ESP, {
        'power1':                   (HARDWARE.ESP,   '<L', (0x2E8,1,0),  (None, None,                           ('Control',     '"Power1 {}".format($)')) ),
        'power2':                   (HARDWARE.ESP,   '<L', (0x2E8,1,1),  (None, None,                           ('Control',     '"Power2 {}".format($)')) ),
        'power3':                   (HARDWARE.ESP,   '<L', (0x2E8,1,2),  (None, None,                           ('Control',     '"Power3 {}".format($)')) ),
        'power4':                   (HARDWARE.ESP,   '<L', (0x2E8,1,3),  (None, None,                           ('Control',     '"Power4 {}".format($)')) ),
        'power5':                   (HARDWARE.ESP,   '<L', (0x2E8,1,4),  (None, None,                           ('Control',     '"Power5 {}".format($)')) ),
        'power6':                   (HARDWARE.ESP,   '<L', (0x2E8,1,5),  (None, None,                           ('Control',     '"Power6 {}".format($)')) ),
        'power7':                   (HARDWARE.ESP,   '<L', (0x2E8,1,6),  (None, None,                           ('Control',     '"Power7 {}".format($)')) ),
        'power8':                   (HARDWARE.ESP,   '<L', (0x2E8,1,7),  (None, None,                           ('Control',     '"Power8 {}".format($)')) ),
                                    },                      0x2E8,       (None, None,                           ('Control',     None)), (None, None) ),
    'pwm_value':                    (HARDWARE.ESP,   '<H',  0x2EC,       ([5],  '0 <= $ <= 1023',               ('Management',  '"Pwm{} {}".format(#+1,$)')) ),
    'altitude':                     (HARDWARE.ESP,   '<h',  0x2F6,       (None, '-30000 <= $ <= 30000',         ('Sensor',      '"Altitude {}".format($)')) ),
    'tele_period':                  (HARDWARE.ESP,   '<H',  0x2F8,       (None, '0 == $ or 10 <= $ <= 3600',    ('MQTT',       '"TelePeriod {}".format($)')) ),
    'ledstate':                     (HARDWARE.ESP,   'B',   0x2FB,       (None, '0 <= $ <= 8',                  ('Control',     '"LedState {}".format(($ & 0x7))')) ),
    'param':                        (HARDWARE.ESP,   'B',   0x2FC,       ([23], None,                           ('SetOption',   '"SetOption{} {}".format(#+32,$)')) ),
    'state_text':                   (HARDWARE.ESP,   '11s', 0x313,       ([4],  None,                           ('MQTT',        '"StateText{} {}".format(#+1,$)')) ),
    'domoticz_update_timer':        (HARDWARE.ESP,   '<H',  0x340,       (None, '0 <= $ <= 3600',               ('Domoticz',    '"DomoticzUpdateTimer {}".format($)')) ),
    'pwm_range':                    (HARDWARE.ESP,   '<H',  0x342,       (None, '$==1 or 255 <= $ <= 1023',     ('Management',  '"PwmRange {}".format($)')) ),
    'domoticz_relay_idx':           (HARDWARE.ESP,   '<L',  0x344,       ([4],  None,                           ('Domoticz',    '"DomoticzIdx{} {}".format(#+1,$)')) ),
    'domoticz_key_idx':             (HARDWARE.ESP,   '<L',  0x354,       ([4],  None,                           ('Domoticz',    '"DomoticzKeyIdx{} {}".format(#+1,$)')) ),
    'energy_power_calibration':     (HARDWARE.ESP,   '<L',  0x364,       (None, None,                           ('Power',       '"PowerSet {}".format($)')) ),
    'energy_voltage_calibration':   (HARDWARE.ESP,   '<L',  0x368,       (None, None,                           ('Power',       '"VoltageSet {}".format($)')) ),
    'energy_current_calibration':   (HARDWARE.ESP,   '<L',  0x36C,       (None, None,                           ('Power',       '"CurrentSet {}".format($)')) ),
    'energy_kWhtoday':              (HARDWARE.ESP,   '<L',  0x370,       (None, '0 <= $ <= 4250000',            ('Power',       '"EnergyReset1 {}".format(int(round(float($)//100)))')) ),
    'energy_kWhyesterday':          (HARDWARE.ESP,   '<L',  0x374,       (None, '0 <= $ <= 4250000',            ('Power',       '"EnergyReset2 {}".format(int(round(float($)//100)))')) ),
    'energy_kWhdoy':                (HARDWARE.ESP,   '<H',  0x378,       (None, None,                           ('Power',       None)) ),
    'energy_min_power':             (HARDWARE.ESP,   '<H',  0x37A,       (None, None,                           ('Power',       '"PowerLow {}".format($)')) ),
    'energy_max_power':             (HARDWARE.ESP,   '<H',  0x37C,       (None, None,                           ('Power',       '"PowerHigh {}".format($)')) ),
    'energy_min_voltage':           (HARDWARE.ESP,   '<H',  0x37E,       (None, None,                           ('Power',       '"VoltageLow {}".format($)')) ),
    'energy_max_voltage':           (HARDWARE.ESP,   '<H',  0x380,       (None, None,                           ('Power',       '"VoltageHigh {}".format($)')) ),
    'energy_min_current':           (HARDWARE.ESP,   '<H',  0x382,       (None, None,                           ('Power',       '"CurrentLow {}".format($)')) ),
    'energy_max_current':           (HARDWARE.ESP,   '<H',  0x384,       (None, None,                           ('Power',       '"CurrentHigh {}".format($)')) ),
    'energy_max_power_limit':       (HARDWARE.ESP,   '<H',  0x386,       (None, None,                           ('Power',       '"MaxPower {}".format($)')) ),
    'energy_max_power_limit_hold':  (HARDWARE.ESP,   '<H',  0x388,       (None, None,                           ('Power',       '"MaxPowerHold {}".format($)')) ),
    'energy_max_power_limit_window':(HARDWARE.ESP,   '<H',  0x38A,       (None, None,                           ('Power',       '"MaxPowerWindow {}".format($)')) ),
    'energy_max_power_safe_limit':  (HARDWARE.ESP,   '<H',  0x38C,       (None, None,                           ('Power',       '"SavePower {}".format($)')) ),
    'energy_max_power_safe_limit_hold':
                                    (HARDWARE.ESP,   '<H',  0x38E,       (None, None,                           ('Power',       '"SavePowerHold {}".format($)')) ),
    'energy_max_power_safe_limit_window':
                                    (HARDWARE.ESP,   '<H',  0x390,       (None, None,                           ('Power',       '"SavePowerWindow {}".format($)')) ),
    'energy_max_energy':            (HARDWARE.ESP,   '<H',  0x392,       (None, None,                           ('Power',       '"MaxEnergy {}".format($)')) ),
    'energy_max_energy_start':      (HARDWARE.ESP,   '<H',  0x394,       (None, None,                           ('Power',       '"MaxEnergyStart {}".format($)')) ),
    'mqtt_retry':                   (HARDWARE.ESP,   '<H',  0x396,       (None, '10 <= $ <= 32000',             ('MQTT',        '"MqttRetry {}".format($)')) ),
    'poweronstate':                 (HARDWARE.ESP,   'B',   0x398,       (None, '0 <= $ <= 5',                  ('Control',     '"PowerOnState {}".format($)')) ),
    'last_module':                  (HARDWARE.ESP,   'B',   0x399,       (None, None,                           (INTERNAL,      None)) ),
    'blinktime':                    (HARDWARE.ESP,   '<H',  0x39A,       (None, '2 <= $ <= 3600',               ('Control',     '"BlinkTime {}".format($)')) ),
    'blinkcount':                   (HARDWARE.ESP,   '<H',  0x39C,       (None, '0 <= $ <= 32000',              ('Control',     '"BlinkCount {}".format($)')) ),
    'friendlyname':                 (HARDWARE.ESP,   '33s', 0x3AC,       ([4],  None,                           ('Management',  '"FriendlyName{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
    'switch_topic':                 (HARDWARE.ESP,   '33s', 0x430,       (None, None,                           ('MQTT',        '"SwitchTopic {}".format($)')) ),
    'sleep':                        (HARDWARE.ESP,   'B',   0x453,       (None, '0 <= $ <= 250',                ('Management',  '"Sleep {}".format($)')) ),
    'domoticz_switch_idx':          (HARDWARE.ESP,   '<H',  0x454,       ([4],  None,                           ('Domoticz',    '"DomoticzSwitchIdx{} {}".format(#+1,$)')) ),
    'domoticz_sensor_idx':          (HARDWARE.ESP,   '<H',  0x45C,       ([12], None,                           ('Domoticz',    '"DomoticzSensorIdx{} {}".format(#+1,$)')) ),
    'module':                       (HARDWARE.ESP,   'B',   0x474,       (None, None,                           ('Management',  '"Module {}".format($)')) ),
    'ws_color':                     (HARDWARE.ESP,   'B',   0x475,       ([4,3],None,                           ('Light',       None)) ),
    'ws_width':                     (HARDWARE.ESP,   'B',   0x481,       ([3],  None,                           ('Light',       None)) ),
    'my_gp':                        (HARDWARE.ESP,   'B',   0x484,       ([18], None,                           ('Management',  '"Gpio{} {}".format(#,$)')) ),
    'light_pixels':                 (HARDWARE.ESP,   '<H',  0x496,       (None, '1 <= $ <= 512',                ('Light',       '"Pixels {}".format($)')) ),
    'light_color':                  (HARDWARE.ESP,   'B',   0x498,       ([5],  None,                           ('Light',       None)) ),
    'light_correction':             (HARDWARE.ESP,   'B',   0x49D     ,  (None, '0 <= $ <= 1',                  ('Light',       '"LedTable {}".format($)')) ),
    'light_dimmer':                 (HARDWARE.ESP,   'B',   0x49E,       (None, '0 <= $ <= 100',                ('Light',       '"Wakeup {}".format($)')) ),
    'light_fade':                   (HARDWARE.ESP,   'B',   0x4A1,       (None, '0 <= $ <= 1',                  ('Light',       '"Fade {}".format($)')) ),
    'light_speed':                  (HARDWARE.ESP,   'B',   0x4A2,       (None, '1 <= $ <= 20',                 ('Light',       '"Speed {}".format($)')) ),
    'light_scheme':                 (HARDWARE.ESP,   'B',   0x4A3,       (None, None,                           ('Light',       '"Scheme {}".format($)')) ),
    'light_width':                  (HARDWARE.ESP,   'B',   0x4A4,       (None, '0 <= $ <= 4',                  ('Light',       '"Width {}".format($)')) ),
    'light_wakeup':                 (HARDWARE.ESP,   '<H',  0x4A6,       (None, '0 <= $ <= 3100',               ('Light',       '"WakeUpDuration {}".format($)')) ),
    'web_password':                 (HARDWARE.ESP,   '33s', 0x4A9,       (None, None,                           ('Wifi',        '"WebPassword {}".format($)')), (passwordread, passwordwrite) ),
    'switchmode':                   (HARDWARE.ESP,   'B',   0x4CA,       ([4],  '0 <= $ <= 7',                  ('Control',     '"SwitchMode{} {}".format(#+1,$)')) ),
    'ntp_server':                   (HARDWARE.ESP,   '33s', 0x4CE,       ([3],  None,                           ('Wifi',        '"NtpServer{} {}".format(#+1,$)')) ),
    'ina219_mode':                  (HARDWARE.ESP,   'B',   0x531,       (None, '0 <= $ <= 7',                  ('Sensor',      '"Sensor13 {}".format($)')) ),
    'pulse_timer':                  (HARDWARE.ESP,   '<H',  0x532,       ([8],  '0 <= $ <= 64900',              ('Control',     '"PulseTime{} {}".format(#+1,$)')) ),
    'ip_address':                   (HARDWARE.ESP,   '<L',  0x544,       ([4],  None,                           ('Wifi',        '"IPAddress{} {}".format(#+1,$)')), ("socket.inet_ntoa(struct.pack('<L', $))", "struct.unpack('<L', socket.inet_aton($))[0]")),
    'energy_kWhtotal':              (HARDWARE.ESP,   '<L',  0x554,       (None, '0 <= $ <= 4250000000',         ('Power',       '"EnergyReset3 {}".format(int(round(float($)//100)))')) ),
    'mqtt_fulltopic':               (HARDWARE.ESP,   '100s',0x558,       (None, None,                           ('MQTT',        '"FullTopic {}".format($)')) ),
    'flag2':                        (HARDWARE.ESP, {
        'current_resolution':       (HARDWARE.ESP,   '<L', (0x5BC,2,15), (None, '0 <= $ <= 3',                  ('Sensor',      '"AmpRes {}".format($)')) ),
        'voltage_resolution':       (HARDWARE.ESP,   '<L', (0x5BC,2,17), (None, '0 <= $ <= 3',                  ('Sensor',      '"VoltRes {}".format($)')) ),
        'wattage_resolution':       (HARDWARE.ESP,   '<L', (0x5BC,2,19), (None, '0 <= $ <= 3',                  ('Sensor',      '"WattRes {}".format($)')) ),
        'emulation':                (HARDWARE.ESP,   '<L', (0x5BC,2,21), (None, '0 <= $ <= 2',                  ('Management',  '"Emulation {}".format($)')) ),
        'energy_resolution':        (HARDWARE.ESP,   '<L', (0x5BC,3,23), (None, '0 <= $ <= 5',                  ('Sensor',      '"EnergyRes {}".format($)')) ),
        'pressure_resolution':      (HARDWARE.ESP,   '<L', (0x5BC,2,26), (None, '0 <= $ <= 3',                  ('Sensor',      '"PressRes {}".format($)')) ),
        'humidity_resolution':      (HARDWARE.ESP,   '<L', (0x5BC,2,28), (None, '0 <= $ <= 3',                  ('Sensor',      '"HumRes {}".format($)')) ),
        'temperature_resolution':   (HARDWARE.ESP,   '<L', (0x5BC,2,30), (None, '0 <= $ <= 3',                  ('Sensor',      '"TempRes {}".format($)')) ),
                                    },                      0x5BC,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
    'pulse_counter':                (HARDWARE.ESP,   '<L',  0x5C0,       ([4],  None,                           ('Sensor',      '"Counter{} {}".format(#+1,$)')) ),
    'pulse_counter_type':           (HARDWARE.ESP, {
        'pulse_counter_type1':      (HARDWARE.ESP,   '<H', (0x5D0,1,0),  (None, None,                           ('Sensor',      '"CounterType1 {}".format($)')) ),
        'pulse_counter_type2':      (HARDWARE.ESP,   '<H', (0x5D0,1,1),  (None, None,                           ('Sensor',      '"CounterType2 {}".format($)')) ),
        'pulse_counter_type3':      (HARDWARE.ESP,   '<H', (0x5D0,1,2),  (None, None,                           ('Sensor',      '"CounterType3 {}".format($)')) ),
        'pulse_counter_type4':      (HARDWARE.ESP,   '<H', (0x5D0,1,3),  (None, None,                           ('Sensor',      '"CounterType4 {}".format($)')) ),
                                    },                      0x5D0,       (None, None,                           ('Sensor',      None)), (None, None) ),
    'pulse_counter_debounce':       (HARDWARE.ESP,   '<H',  0x5D2,       (None, '0 <= $ <= 32000',              ('Sensor',      '"CounterDebounce {}".format($)')) ),
    'rf_code':                      (HARDWARE.ESP,   'B',   0x5D4,       ([17,9],None,                          ('Rf',          None)), '"0x{:02x}".format($)'),
                                    }
# ======================================================================
SETTING_5_11_0 = copy.deepcopy(SETTING_5_10_0)
SETTING_5_11_0.update               ({
    'display_model':                (HARDWARE.ESP,   'B',   0x2D2,       (None, '0 <= $ <= 16',                 ('Display',     '"Model {}".format($)')) ),
    'display_mode':                 (HARDWARE.ESP,   'B',   0x2D3,       (None, '0 <= $ <= 5',                  ('Display',     '"Mode {}".format($)')) ),
    'display_refresh':              (HARDWARE.ESP,   'B',   0x2D4,       (None, '1 <= $ <= 7',                  ('Display',     '"Refresh {}".format($)')) ),
    'display_rows':                 (HARDWARE.ESP,   'B',   0x2D5,       (None, '1 <= $ <= 32',                 ('Display',     '"Rows {}".format($)')) ),
    'display_cols':                 (HARDWARE.ESP,   'B',   0x2D6,       ([2],  '1 <= $ <= 40',                 ('Display',     '"Cols{} {}".format(#+1,$)')) ),
    'display_address':              (HARDWARE.ESP,   'B',   0x2D8,       ([8],  None,                           ('Display',     '"Address{} {}".format(#+1,$)')) ),
    'display_dimmer':               (HARDWARE.ESP,   'B',   0x2E0,       (None, '0 <= $ <= 100',                ('Display',     '"Dimmer {}".format($)')) ),
    'display_size':                 (HARDWARE.ESP,   'B',   0x2E1,       (None, '1 <= $ <= 4',                  ('Display',     '"Size {}".format($)')) ),
                                    })
SETTING_5_11_0['flag'][1].update    ({
        'light_signal':             (HARDWARE.ESP,   '<L', (0x010,1,18), (None, None,                           ('SetOption',   '"SetOption18 {}".format($)')) ),
                                    })
SETTING_5_11_0.pop('mqtt_fingerprinth',None)
# ======================================================================
SETTING_5_12_0 = copy.deepcopy(SETTING_5_11_0)
SETTING_5_12_0['flag'][1].update    ({
        'hass_discovery':           (HARDWARE.ESP,   '<L', (0x010,1,19), (None, None,                           ('SetOption',   '"SetOption19 {}".format($)')) ),
        'not_power_linked':         (HARDWARE.ESP,   '<L', (0x010,1,20), (None, None,                           ('SetOption',   '"SetOption20 {}".format($)')) ),
        'no_power_on_check':        (HARDWARE.ESP,   '<L', (0x010,1,21), (None, None,                           ('SetOption',   '"SetOption21 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_5_13_1 = copy.deepcopy(SETTING_5_12_0)
SETTING_5_13_1.pop('mqtt_fingerprint',None)
SETTING_5_13_1['flag'][1].update    ({
        'mqtt_serial':              (HARDWARE.ESP,   '<L', (0x010,1,22), (None, None,                           ('SetOption',   '"SetOption22 {}".format($)')) ),
        'rules_enabled':            (HARDWARE.ESP,   '<L', (0x010,1,23), (None, None,                           ('SetOption',   '"SetOption23 {}".format($)')) ),
        'rules_once':               (HARDWARE.ESP,   '<L', (0x010,1,24), (None, None,                           ('SetOption',   '"SetOption24 {}".format($)')) ),
        'knx_enabled':              (HARDWARE.ESP,   '<L', (0x010,1,25), (None, None,                           ('KNX',         '"KNX_ENABLED {}".format($)')) ),
                                    })
SETTING_5_13_1.update               ({
    'baudrate':                     (HARDWARE.ESP,   'B',   0x09D,       (None, None,                           ('Serial',      '"Baudrate {}".format($)')), ('$ * 1200','$ // 1200') ),
    'mqtt_fingerprint1':            (HARDWARE.ESP,   'B',   0x1AD,       ([20], None,                           ('MQTT',        '"MqttFingerprint1 {}".format(" ".join("{:02X}".format(c) for c in @["mqtt_fingerprint1"]))')), '"0x{:02x}".format($)' ),
    'mqtt_fingerprint2':            (HARDWARE.ESP,   'B',   0x1AD+20,    ([20], None,                           ('MQTT',        '"MqttFingerprint2 {}".format(" ".join("{:02X}".format(c) for c in @["mqtt_fingerprint2"]))')), '"0x{:02x}".format($)' ),
    'energy_power_delta':           (HARDWARE.ESP,   'B',   0x33F,       (None, None,                           ('Power',       '"PowerDelta {}".format($)')) ),
    'light_rotation':               (HARDWARE.ESP,   '<H',  0x39E,       (None, None,                           ('Light',       '"Rotation {}".format($)')) ),
    'serial_delimiter':             (HARDWARE.ESP,   'B',   0x451,       (None, None,                           ('Serial',      '"SerialDelimiter {}".format($)')) ),
    'sbaudrate':                    (HARDWARE.ESP,   'B',   0x452,       (None, None,                           ('Serial',      '"SBaudrate {}".format($)')), ('$ * 1200','$ // 1200') ),
    'knx_GA_registered':            (HARDWARE.ESP,   'B',   0x4A5,       (None, None,                           ('KNX',         None)) ),
    'knx_CB_registered':            (HARDWARE.ESP,   'B',   0x4A8,       (None, None,                           ('KNX',         None)) ),
    'timer':                        (HARDWARE.ESP, {
        'time':                     (HARDWARE.ESP,   '<L', (0x670,11, 0),(None, '0 <= $ < 1440',                ('Timer',       '"Timer{} {{\\\"Arm\\\":{arm},\\\"Mode\\\":{mode},\\\"Time\\\":\\\"{tsign}{time}\\\",\\\"Window\\\":{window},\\\"Days\\\":\\\"{days}\\\",\\\"Repeat\\\":{repeat},\\\"Output\\\":{device},\\\"Action\\\":{power}}}".format(#+1, arm=@["timer"][#]["arm"],mode=@["timer"][#]["mode"],tsign="-" if @["timer"][#]["mode"]>0 and @["timer"][#]["time"]>(12*60) else "",time=time.strftime("%H:%M",time.gmtime((@["timer"][#]["time"] if @["timer"][#]["mode"]==0 else @["timer"][#]["time"] if @["timer"][#]["time"]<=(12*60) else @["timer"][#]["time"]-(12*60))*60)),window=@["timer"][#]["window"],repeat=@["timer"][#]["repeat"],days="{:07b}".format(@["timer"][#]["days"])[::-1],device=@["timer"][#]["device"]+1,power=@["timer"][#]["power"] )')), '"0x{:03x}".format($)' ),
        'window':                   (HARDWARE.ESP,   '<L', (0x670, 4,11),(None, None,                           ('Timer',       None)) ),
        'repeat':                   (HARDWARE.ESP,   '<L', (0x670, 1,15),(None, None,                           ('Timer',       None)) ),
        'days':                     (HARDWARE.ESP,   '<L', (0x670, 7,16),(None, None,                           ('Timer',       None)), '"0b{:07b}".format($)' ),
        'device':                   (HARDWARE.ESP,   '<L', (0x670, 4,23),(None, None,                           ('Timer',       None)) ),
        'power':                    (HARDWARE.ESP,   '<L', (0x670, 2,27),(None, None,                           ('Timer',       None)) ),
        'mode':                     (HARDWARE.ESP,   '<L', (0x670, 2,29),(None, '0 <= $ <= 3',                  ('Timer',       None)) ),
        'arm':                      (HARDWARE.ESP,   '<L', (0x670, 1,31),(None, None,                           ('Timer',       None)) ),
                                    },                      0x670,       ([16], None,                           ('Timer',       None)) ),
    'latitude':                     (HARDWARE.ESP,   'i',   0x6B0,       (None, None,                           ('Timer',       '"Latitude {}".format($)')),  ('float($) / 1000000', 'int($ * 1000000)')),
    'longitude':                    (HARDWARE.ESP,   'i',   0x6B4,       (None, None,                           ('Timer',       '"Longitude {}".format($)')), ('float($) / 1000000', 'int($ * 1000000)')),
    'knx_physsical_addr':           (HARDWARE.ESP,   '<H',  0x6B8,       (None, None,                           ('KNX',         None)) ),
    'knx_GA_addr':                  (HARDWARE.ESP,   '<H',  0x6BA,       ([10], None,                           ('KNX',         None)) ),
    'knx_CB_addr':                  (HARDWARE.ESP,   '<H',  0x6CE,       ([10], None,                           ('KNX',         None)) ),
    'knx_GA_param':                 (HARDWARE.ESP,   'B',   0x6E2,       ([10], None,                           ('KNX',         None)) ),
    'knx_CB_param':                 (HARDWARE.ESP,   'B',   0x6EC,       ([10], None,                           ('KNX',         None)) ),
    'rules':                        (HARDWARE.ESP,   '512s',0x800,       (None, None,                           ('Rules',       '"Rule {}".format("\\"" if len($) == 0 else $)')) ),
                                    })
# ======================================================================
SETTING_5_14_0 = copy.deepcopy(SETTING_5_13_1)
SETTING_5_14_0['flag'][1].update    ({
        'device_index_enable':      (HARDWARE.ESP,   '<L', (0x010,1,26), (None, None,                           ('SetOption',   '"SetOption26 {}".format($)')) ),
                                    })
SETTING_5_14_0['flag'][1].pop('rules_once',None)
SETTING_5_14_0.update               ({
    'tflag':                        (HARDWARE.ESP, {
        'hemis':                    (HARDWARE.ESP,   '<H', (0x2E2,1, 0), (None, None,                           ('Management',  None)) ),
        'week':                     (HARDWARE.ESP,   '<H', (0x2E2,3, 1), (None, '0 <= $ <= 4',                  ('Management',  None)) ),
        'month':                    (HARDWARE.ESP,   '<H', (0x2E2,4, 4), (None, '1 <= $ <= 12',                 ('Management',  None)) ),
        'dow':                      (HARDWARE.ESP,   '<H', (0x2E2,3, 8), (None, '1 <= $ <= 7',                  ('Management',  None)) ),
        'hour':                     (HARDWARE.ESP,   '<H', (0x2E2,5,11), (None, '0 <= $ <= 23',                 ('Management',  None)) ),
                                    },                      0x2E2,       ([2],  None,                           ('Management',  None)), (None, None) ),
    'param':                        (HARDWARE.ESP,   'B',   0x2FC,       ([18], None,                           ('SetOption',   '"SetOption{} {}".format(#+32,$)')) ),
    'toffset':                      (HARDWARE.ESP,   '<h',  0x30E,       ([2],  None,                           ('Management',  '"{cmnd} {hemis},{week},{month},{dow},{hour},{toffset}".format(cmnd="TimeSTD" if #==0 else "TimeDST", hemis=@["tflag"][#]["hemis"], week=@["tflag"][#]["week"], month=@["tflag"][#]["month"], dow=@["tflag"][#]["dow"], hour=@["tflag"][#]["hour"], toffset=value)')) ),
                                    })
# ======================================================================
SETTING_6_0_0 = copy.deepcopy(SETTING_5_14_0)
SETTING_6_0_0.update                ({
    'cfg_holder':                   (HARDWARE.ESP,   '<H',  0x000,       (None, None,                           ('System',      None)), ),
    'cfg_size':                     (HARDWARE.ESP,   '<H',  0x002,       (None, None,                           ('System',      None)), (None, False)),
    'bootcount':                    (HARDWARE.ESP,   '<H',  0x00C,       (None, None,                           ('System',      None)), (None, False)),
    'cfg_crc':                      (HARDWARE.ESP,   '<H',  0x00E,       (None, None,                           ('System',      None)), '"0x{:04x}".format($)'),
    'rule_enabled':                 (HARDWARE.ESP, {
        'rule1':                    (HARDWARE.ESP,   'B',  (0x49F,1,0),  (None, None,                           ('Rules',       '"Rule1 {}".format($)')) ),
        'rule2':                    (HARDWARE.ESP,   'B',  (0x49F,1,1),  (None, None,                           ('Rules',       '"Rule2 {}".format($)')) ),
        'rule3':                    (HARDWARE.ESP,   'B',  (0x49F,1,2),  (None, None,                           ('Rules',       '"Rule3 {}".format($)')) ),
                                    },                      0x49F,       (None, None,                           ('Rules',       None)), (None, None) ),
    'rule_once':                    (HARDWARE.ESP, {
        'rule1':                    (HARDWARE.ESP,   'B',  (0x4A0,1,0),  (None, None,                           ('Rules',       '"Rule1 {}".format($+4)')) ),
        'rule2':                    (HARDWARE.ESP,   'B',  (0x4A0,1,1),  (None, None,                           ('Rules',       '"Rule2 {}".format($+4)')) ),
        'rule3':                    (HARDWARE.ESP,   'B',  (0x4A0,1,2),  (None, None,                           ('Rules',       '"Rule3 {}".format($+4)')) ),
                                    },                      0x4A0,       (None, None,                           ('Rules',       None)), (None, None) ),
    'mems':                         (HARDWARE.ESP,   '10s', 0x7CE,       ([5],  None,                           ('Rules',       '"Mem{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
    'rules':                        (HARDWARE.ESP,   '512s',0x800,       ([3],  None,                           ('Rules',       '"Rule{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
                                    })
SETTING_6_0_0['flag'][1].update     ({
        'knx_enable_enhancement':   (HARDWARE.ESP,   '<L', (0x010,1,27), (None, None,                           ('KNX',         '"KNX_ENHANCED {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_1_1 = copy.deepcopy(SETTING_6_0_0)
SETTING_6_1_1.update                ({
    'flag3':                        (HARDWARE.ESP,   '<L',  0x3A0,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
    'switchmode':                   (HARDWARE.ESP,   'B',   0x3A4,       ([8],  '0 <= $ <= 7',                  ('Control',     '"SwitchMode{} {}".format(#+1,$)')) ),
    'mcp230xx_config':              (HARDWARE.ESP, {
        'pinmode':                  (HARDWARE.ESP,   '<H', (0x6F6,3, 0), (None, None,                           ('Sensor',      '"Sensor29 {pin},{pinmode},{pullup},{intmode}".format(pin=#, pinmode=@["mcp230xx_config"][#]["pinmode"], pullup=@["mcp230xx_config"][#]["pullup"], intmode=@["mcp230xx_config"][#]["int_report_mode"])')) ),
        'pullup':                   (HARDWARE.ESP,   '<H', (0x6F6,1, 3), (None, None,                           ('Sensor',      None)) ),
        'saved_state':              (HARDWARE.ESP,   '<H', (0x6F6,1, 4), (None, None,                           ('Sensor',      None)) ),
        'int_report_mode':          (HARDWARE.ESP,   '<H', (0x6F6,2, 5), (None, None,                           ('Sensor',      None)) ),
        'int_report_defer':         (HARDWARE.ESP,   '<H', (0x6F6,4, 7), (None, None,                           ('Sensor',      None)) ),
        'int_count_en':             (HARDWARE.ESP,   '<H', (0x6F6,1,11), (None, None,                           ('Sensor',      None)) ),
                                     },     0x6F6,       ([16], None,                                           ('Sensor',      None)), (None, None) ),
                                    })
SETTING_6_1_1['flag'][1].update     ({
        'rf_receive_decimal':       (HARDWARE.ESP,   '<L', (0x010,1,28), (None, None,                           ('SetOption' ,  '"SetOption28 {}".format($)')) ),
        'ir_receive_decimal':       (HARDWARE.ESP,   '<L', (0x010,1,29), (None, None,                           ('SetOption',   '"SetOption29 {}".format($)')) ),
        'hass_light':               (HARDWARE.ESP,   '<L', (0x010,1,30), (None, None,                           ('SetOption',   '"SetOption30 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_2_1 = copy.deepcopy(SETTING_6_1_1)
SETTING_6_2_1.update                ({
    'rule_stop':                    (HARDWARE.ESP, {
        'rule1':                    (HARDWARE.ESP,   'B',  (0x1A7,1,0),  (None, None,                           ('Rules',       '"Rule1 {}".format($+8)')) ),
        'rule2':                    (HARDWARE.ESP,   'B',  (0x1A7,1,1),  (None, None,                           ('Rules',       '"Rule2 {}".format($+8)')) ),
        'rule3':                    (HARDWARE.ESP,   'B',  (0x1A7,1,2),  (None, None,                           ('Rules',       '"Rule3 {}".format($+8)')) ),
                                     },     0x1A7,        None),
    'display_rotate':               (HARDWARE.ESP,   'B',   0x2FA,       (None, '0 <= $ <= 3',                  ('Display',     '"Rotate {}".format($)')) ),
    'display_font':                 (HARDWARE.ESP,   'B',   0x312,       (None, '1 <= $ <= 4',                  ('Display',     '"Font {}".format($)')) ),
    'flag3':                        (HARDWARE.ESP, {
        'timers_enable':            (HARDWARE.ESP,   '<L', (0x3A0,1, 0), (None, None,                           ('Timer',       '"Timers {}".format($)')) ),
        'user_esp8285_enable':      (HARDWARE.ESP,   '<L', (0x3A0,1,31), (None, None,                           (INTERNAL,      None)) ),
                                    },                      0x3A0,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
    'button_debounce':              (HARDWARE.ESP,   '<H',  0x542,       (None, '40 <= $ <= 1000',              ('Control',     '"ButtonDebounce {}".format($)')) ),
    'switch_debounce':              (HARDWARE.ESP,   '<H',  0x66E,       (None, '40 <= $ <= 1000',              ('Control',     '"SwitchDebounce {}".format($)')) ),
    'mcp230xx_int_prio':            (HARDWARE.ESP,   'B',   0x716,       (None, None,                           ('Sensor',      None)) ),
    'mcp230xx_int_timer':           (HARDWARE.ESP,   '<H',  0x718,       (None, None,                           ('Sensor',      None)) ),
                                    })
SETTING_6_2_1['flag'][1].pop('rules_enabled',None)
SETTING_6_2_1['flag'][1].update     ({
        'mqtt_serial_raw':          (HARDWARE.ESP,   '<L', (0x010,1,23), (None, None,                           ('SetOption',   '"SetOption23 {}".format($)')) ),
        'global_state':             (HARDWARE.ESP,   '<L', (0x010,1,31), (None, None,                           ('SetOption',   '"SetOption31 {}".format($)')) ),
                                    })
SETTING_6_2_1['flag2'][1].update    ({
    'axis_resolution':              (HARDWARE.ESP,   '<L', (0x5BC,2,13), (None, None,                           ('Sensor',      None)) ),   # Need to be services by command Sensor32
                                    })
# ======================================================================
SETTING_6_2_1_2 = copy.deepcopy(SETTING_6_2_1)
SETTING_6_2_1_2['flag3'][1].update  ({
        'user_esp8285_enable':      (HARDWARE.ESP,   '<L', (0x3A0,1, 1), (None, None,                           ('SetOption',   '"SetOption51 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_2_1_3 = copy.deepcopy(SETTING_6_2_1_2)
SETTING_6_2_1_3['flag2'][1].update  ({
        'frequency_resolution':     (HARDWARE.ESP,   '<L', (0x5BC,2,11), (None, '0 <= $ <= 3',                  ('Power',       '"FreqRes {}".format($)')) ),
                                    })
SETTING_6_2_1_3['flag3'][1].update  ({
        'time_append_timezone':     (HARDWARE.ESP,   '<L', (0x3A0,1, 2), (None, None,                           ('SetOption',   '"SetOption52 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_2_1_6 = copy.deepcopy(SETTING_6_2_1_3)
SETTING_6_2_1_6.update              ({
    'energy_power_calibration':     (HARDWARE.ESP,   '<L',  0x364,       (None, '1000 <= $ <= 32000',           ('Power',       '"PowerCal {}".format($)')) ),
    'energy_voltage_calibration':   (HARDWARE.ESP,   '<L',  0x368,       (None, '1000 <= $ <= 32000',           ('Power',       '"VoltageCal {}".format($)')) ),
    'energy_current_calibration':   (HARDWARE.ESP,   '<L',  0x36C,       (None, '1000 <= $ <= 32000',           ('Power',       '"CurrentCal {}".format($)')) ),
    'energy_frequency_calibration': (HARDWARE.ESP,   '<L',  0x7C8,       (None, '45000 < $ < 65000',            ('Power',       '"FrequencySet {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_2_1_10 = copy.deepcopy(SETTING_6_2_1_6)
SETTING_6_2_1_10.update             ({
    'rgbwwTable':                   (HARDWARE.ESP,   'B',   0x71A,       ([5],  None,                           ('Light',       '"RGBWWTable {}".format(",".join(str(i) for i in @["rgbwwTable"]))')) ),
                                    })
# ======================================================================
SETTING_6_2_1_14 = copy.deepcopy(SETTING_6_2_1_10)
SETTING_6_2_1_14.update             ({
    'weight_reference':             (HARDWARE.ESP,   '<L',  0x7C0,       (None, None,                           ('Management',  '"Sensor34 3 {}".format($)')) ),
    'weight_calibration':           (HARDWARE.ESP,   '<L',  0x7C4,       (None, None,                           ('Management',  '"Sensor34 4 {}".format($)')) ),
    'weight_max':                   (HARDWARE.ESP,   '<H',  0x7BE,       (None, None,                           ('Management',  '"Sensor34 5 {}".format($)')), ('float($) // 1000', 'int($ * 1000)') ),
    'weight_item':                  (HARDWARE.ESP,   '<H',  0x7BC,       (None, None,                           ('Management',  '"Sensor34 6 {}".format($)')), ('int($ * 10)', 'float($) // 10') ),
    'web_refresh':                  (HARDWARE.ESP,   '<H',  0x7CC,       (None, '1000 <= $ <= 10000',           ('Wifi',        '"WebRefresh {}".format($)')) ),
                                    })
SETTING_6_2_1_14['flag2'][1].update ({
        'weight_resolution':        (HARDWARE.ESP,   '<L', (0x5BC,2, 9), (None, '0 <= $ <= 3',                  ('Sensor',      '"WeightRes {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_2_1_19 = copy.deepcopy(SETTING_6_2_1_14)
SETTING_6_2_1_19.update             ({
    'weight_item':                  (HARDWARE.ESP,   '<L',  0x7B8,       (None, None,                           ('Sensor',      '"Sensor34 6 {}".format($)')), ('int($ * 10)', 'float($) // 10') ),
                                    })
SETTING_6_2_1_20 = SETTING_6_2_1_19
SETTING_6_2_1_20['flag3'][1].update ({
        'gui_hostname_ip':          (HARDWARE.ESP,   '<L', (0x3A0,1,3),  (None, None,                           ('SetOption',   '"SetOption53 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0 = copy.deepcopy(SETTING_6_2_1_20)
SETTING_6_3_0.update                ({
    'energy_kWhtotal_time':         (HARDWARE.ESP,   '<L',  0x7B4,       (None, None,                           ('Power',       None)) ),
    'energy_kWhtoday':              (HARDWARE.ESP,   '<L',  0x370,       (None, '0 <= $ <= 4294967295',         ('Power',       '"EnergyReset1 {}".format(int(round(float($)//100)))')) ),
    'energy_kWhyesterday':          (HARDWARE.ESP,   '<L',  0x374,       (None, '0 <= $ <= 4294967295',         ('Power',       '"EnergyReset2 {}".format(int(round(float($)//100)))')) ),
    'energy_kWhtotal':              (HARDWARE.ESP,   '<L',  0x554,       (None, '0 <= $ <= 4294967295',         ('Power',       '"EnergyReset3 {}".format(int(round(float($)//100)))')) ),
                                    })
# ======================================================================
SETTING_6_3_0_2 = copy.deepcopy(SETTING_6_3_0)
SETTING_6_3_0_2.update              ({
    'timezone_minutes':             (HARDWARE.ESP,   'B',   0x66D,       (None, None,                           (INTERNAL,      None)) ),
                                    })
SETTING_6_3_0_2['flag'][1].pop('rules_once',None)
SETTING_6_3_0_2['flag'][1].update   ({
        'pressure_conversion':      (HARDWARE.ESP,   '<L', (0x010,1,24), (None, None,                           ('SetOption',   '"SetOption24 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0_4 = copy.deepcopy(SETTING_6_3_0_2)
SETTING_6_3_0_4.update              ({
    'drivers':                      (HARDWARE.ESP,   '<L',  0x794,       ([3],  None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
    'monitors':                     (HARDWARE.ESP,   '<L',  0x7A0,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
    'sensors':                      (HARDWARE.ESP,   '<L',  0x7A4,       ([3],  None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
    'displays':                     (HARDWARE.ESP,   '<L',  0x7B0,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
                                    })
SETTING_6_3_0_4['flag3'][1].update  ({
        'tuya_apply_o20':           (HARDWARE.ESP,   '<L', (0x3A0,1, 4), (None, None,                           ('SetOption',   '"SetOption54 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0_8 = copy.deepcopy(SETTING_6_3_0_4)
SETTING_6_3_0_8['flag3'][1].update  ({
        'hass_short_discovery_msg': (HARDWARE.ESP,   '<L', (0x3A0,1, 5), (None, None,                           ('SetOption',   '"SetOption55 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0_10 = copy.deepcopy(SETTING_6_3_0_8)
SETTING_6_3_0_10['flag3'][1].update ({
        'use_wifi_scan':            (HARDWARE.ESP,   '<L', (0x3A0,1, 6), (None, None,                           ('SetOption',   '"SetOption56 {}".format($)')) ),
        'use_wifi_rescan':          (HARDWARE.ESP,   '<L', (0x3A0,1, 7), (None, None,                           ('SetOption',   '"SetOption57 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0_11 = copy.deepcopy(SETTING_6_3_0_10)
SETTING_6_3_0_11['flag3'][1].update ({
        'receive_raw':          	(HARDWARE.ESP,   '<L', (0x3A0,1, 8), (None, None,                           ('SetOption',   '"SetOption58 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0_13 = copy.deepcopy(SETTING_6_3_0_11)
SETTING_6_3_0_13['flag3'][1].update ({
        'hass_tele_on_power':       (HARDWARE.ESP,   '<L', (0x3A0,1, 9), (None, None,                           ('SetOption',   '"SetOption59 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0_14 = copy.deepcopy(SETTING_6_3_0_13)
SETTING_6_3_0_14['flag2'][1].update ({
        'calc_resolution':          (HARDWARE.ESP,   '<L', (0x5BC,3, 6), (None, '0 <= $ <= 7',                  ('Rules',       '"CalcRes {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0_15 = copy.deepcopy(SETTING_6_3_0_14)
SETTING_6_3_0_15['flag3'][1].update ({
        'sleep_normal':             (HARDWARE.ESP,   '<L', (0x3A0,1,10), (None, None,                           ('SetOption',   '"SetOption60 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_3_0_16 = copy.deepcopy(SETTING_6_3_0_15)
SETTING_6_3_0_16['mcp230xx_config'][1].update ({
        'int_retain_flag':          (HARDWARE.ESP,   '<H', (0x6F6,1,12), (None, None,                           ('Sensor',      '"Sensor29 IntRetain,{pin},{int_retain_flag}".format(pin=#, int_retain_flag=@["mcp230xx_config"][#]["int_retain_flag"])')) ),
                                    })
SETTING_6_3_0_16['flag3'][1].update ({
        'button_switch_force_local':(HARDWARE.ESP,   '<L', (0x3A0,1,11), (None, None,                           ('SetOption',   '"SetOption61 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_4_0_2 = copy.deepcopy(SETTING_6_3_0_16)
SETTING_6_4_0_2['flag3'][1].pop('hass_short_discovery_msg',None)
# ======================================================================
SETTING_6_4_1_4 = copy.deepcopy(SETTING_6_4_0_2)
SETTING_6_4_1_4['flag3'][1].update  ({
        'mdns_enabled':             (HARDWARE.ESP,   '<L', (0x3A0,1, 5), (None, None,                           ('SetOption',   '"SetOption55 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_4_1_7 = copy.deepcopy(SETTING_6_4_1_4)
SETTING_6_4_1_7['flag3'][1].update  ({
        'no_pullup':                (HARDWARE.ESP,   '<L', (0x3A0,1,12), (None, None,                           ('SetOption',   '"SetOption62 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_4_1_8 = copy.deepcopy(SETTING_6_4_1_7)
SETTING_6_4_1_8.update              ({
    'my_gp':                        (HARDWARE.ESP,   'B',   0x484,       ([17], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
                                    })
SETTING_6_4_1_8['flag3'][1].update  ({
        'split_interlock':          (HARDWARE.ESP,   '<L', (0x3A0,1,13), (None, None,                           ('SetOption',   '"SetOption63 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_4_1_11 = copy.deepcopy(SETTING_6_4_1_8)
SETTING_6_4_1_11['flag3'][1].pop('split_interlock',None)
SETTING_6_4_1_11.update             ({
    'interlock':                    (HARDWARE.ESP,   'B',   0x4CA,       ([4],  None,                           ('Control',     '"Interlock "+" ".join(",".join(str(i+1) for i in range(0,8) if j & (1<<i) ) for j in @["interlock"])')), '"0x{:02x}".format($)' ),
                                    })
SETTING_6_4_1_11['flag'][1].update  ({
        'interlock':                (HARDWARE.ESP,   '<L', (0x010,1,14), (None, None,                           ('Control',     '"Interlock {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_4_1_13 = copy.deepcopy(SETTING_6_4_1_11)
SETTING_6_4_1_13.update             ({
    'SensorBits1':                  (HARDWARE.ESP, {
        'mhz19b_abc_disable':       (HARDWARE.ESP,   'B',  (0x717,1, 7), (None, None,                           ('Sensor',      '"Sensor15 {}".format($)')) ),
                                    },                      0x717,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
# ======================================================================
SETTING_6_4_1_16 = copy.deepcopy(SETTING_6_4_1_13)
SETTING_6_4_1_16.update             ({
    'user_template':                (HARDWARE.ESP, {
        'base':                     (HARDWARE.ESP,   'B',   0x71F,       (None, None,                           ('Management',  '"Template {{\\\"BASE\\\":{}}}".format($)')), ('$+1','$-1') ),
        'name':                     (HARDWARE.ESP,   '15s', 0x720,       (None, None,                           ('Management',  '"Template {{\\\"NAME\\\":\\\"{}\\\"}}".format($)' )) ),
        'gpio':                     (HARDWARE.ESP,   'B',   0x72F,       ([13], None,                           ('Management',  '"Template {{\\\"GPIO\\\":{}}}".format(@["user_template"]["gpio"])')) ),
        'flag':                     (HARDWARE.ESP, {
            'adc0':                 (HARDWARE.ESP,   'B',  (0x73C,4,0),  (None, None,                           ('Management',  '"Template {{\\\"FLAG\\\":{}}}".format($)')) ),
                                    },                      0x73C,       (None, None,                           ('Management',  None))
                                    ),
                                    },                      0x71F,       (None, None,                           ('Management',  None))
                                    ),
                                    })
# ======================================================================
SETTING_6_4_1_17 = copy.deepcopy(SETTING_6_4_1_16)
SETTING_6_4_1_17['flag3'][1].pop('no_pullup',None)
# ======================================================================
SETTING_6_4_1_18 = copy.deepcopy(SETTING_6_4_1_17)
SETTING_6_4_1_18['flag3'][1].update ({
        'no_hold_retain':           (HARDWARE.ESP,   '<L', (0x3A0,1,12), (None, None,                           ('SetOption',   '"SetOption62 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_5_0_3 = copy.deepcopy(SETTING_6_4_1_18)
SETTING_6_5_0_3.update              ({
    'novasds_period':               (HARDWARE.ESP,   'B',   0x73D,       (None, '1 <= $ <= 255',                ('Sensor',      '"Sensor20 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_5_0_6 = copy.deepcopy(SETTING_6_5_0_3)
SETTING_6_5_0_6.update              ({
    'web_color':                    (HARDWARE.ESP,   '3B',  0x73E,       ([18], None,                           ('Wifi',        '"WebColor{} {}{:06x}".format(#+1,chr(35),int($,0))')), '"0x{:06x}".format($)' ),
                                    })
# ======================================================================
SETTING_6_5_0_7 = copy.deepcopy(SETTING_6_5_0_6)
SETTING_6_5_0_7.update              ({
    'ledmask':                      (HARDWARE.ESP,   '<H',  0x7BC,       (None, None,                           ('Control',     '"LedMask {}".format($)')), '"0x{:04x}".format($)' ),
                                    })
# ======================================================================
SETTING_6_5_0_9 = copy.deepcopy(SETTING_6_5_0_7)
SETTING_6_5_0_9['flag3'][1].update  ({
        'no_power_feedback':        (HARDWARE.ESP,   '<L', (0x3A0,1,13), (None, None,                           ('SetOption',   '"SetOption63 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_5_0_10 = copy.deepcopy(SETTING_6_5_0_9)
SETTING_6_5_0_10.update             ({
    'my_adc0':                      (HARDWARE.ESP,   'B',   0x495,       (None, None,                           ('Sensor',      '"Adc {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_5_0_11 = copy.deepcopy(SETTING_6_5_0_10)
SETTING_6_5_0_11['flag3'][1].update ({
        'use_underscore':           (HARDWARE.ESP,   '<L', (0x3A0,1,14), (None, None,                           ('SetOption',   '"SetOption64 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_5_0_12 = copy.deepcopy(SETTING_6_5_0_11)
SETTING_6_5_0_12.pop('drivers',None)
SETTING_6_5_0_12.update             ({
    'adc_param_type':               (HARDWARE.ESP,   'B',   0x1D5,       (None, '2 <= $ <= 3',                  ('Sensor',      '"AdcParam {type},{param1},{param2},{param3}".format(type=@["my_adc0"],param1=@["adc_param1"],param2=@["adc_param2"],param3=@["adc_param3"]/10000)')) ),
    'adc_param1':                   (HARDWARE.ESP,   '<L',  0x794,       (None, None,                           ('Sensor',      None)) ),
    'adc_param2':                   (HARDWARE.ESP,   '<L',  0x798,       (None, None,                           ('Sensor',      None)) ),
    'adc_param3':                   (HARDWARE.ESP,   '<l',  0x79C,       (None, None,                           ('Sensor',      None)) ),
    'sps30_inuse_hours':            (HARDWARE.ESP,   'B',   0x1E8,       (None, None,                           (INTERNAL,      None)) ),
                                    })
# ======================================================================
SETTING_6_5_0_15 = copy.deepcopy(SETTING_6_5_0_12)
SETTING_6_5_0_15['flag3'][1].update ({
        'tuya_show_dimmer':         (HARDWARE.ESP,   '<L', (0x3A0,1,15), (None, None,                           ('SetOption',   '"SetOption65 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_1 = copy.deepcopy(SETTING_6_5_0_15)
SETTING_6_6_0_1['flag3'][1].update  ({
        'tuya_dimmer_range_255':    (HARDWARE.ESP,   '<L', (0x3A0,1,16), (None, None,                           ('SetOption',   '"SetOption66 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_2 = copy.deepcopy(SETTING_6_6_0_1)
SETTING_6_6_0_2['flag3'][1].update  ({
        'buzzer_enable':            (HARDWARE.ESP,   '<L', (0x3A0,1,17), (None, None,                           ('SetOption',   '"SetOption67 {}".format($)')) ),
                                    })
SETTING_6_6_0_2.update              ({
    'display_model':                (HARDWARE.ESP,   'B',   0x2D2,       (None, '0 <= $ <= 16',                 ('Display',     '"DisplayModel {}".format($)')) ),
    'display_mode':                 (HARDWARE.ESP,   'B',   0x2D3,       (None, '0 <= $ <= 5',                  ('Display',     '"DisplayMode {}".format($)')) ),
    'display_refresh':              (HARDWARE.ESP,   'B',   0x2D4,       (None, '1 <= $ <= 7',                  ('Display',     '"DisplayRefresh {}".format($)')) ),
    'display_rows':                 (HARDWARE.ESP,   'B',   0x2D5,       (None, '1 <= $ <= 32',                 ('Display',     '"DisplayRows {}".format($)')) ),
    'display_cols':                 (HARDWARE.ESP,   'B',   0x2D6,       ([2],  '1 <= $ <= 44',                 ('Display',     '"DisplayCols{} {}".format(#+1,$)')) ),
    'display_address':              (HARDWARE.ESP,   'B',   0x2D8,       ([8],  None,                           ('Display',     '"DisplayAddress{} {}".format(#+1,$)')) ),
    'display_dimmer':               (HARDWARE.ESP,   'B',   0x2E0,       (None, '0 <= $ <= 100',                ('Display',     '"DisplayDimmer {}".format($)')) ),
    'display_size':                 (HARDWARE.ESP,   'B',   0x2E1,       (None, '1 <= $ <= 4',                  ('Display',     '"DisplaySize {}".format($)')) ),
    'display_rotate':               (HARDWARE.ESP,   'B',   0x2FA,       (None, '0 <= $ <= 3',                  ('Display',     '"DisplayRotate {}".format($)')) ),
    'display_font':                 (HARDWARE.ESP,   'B',   0x312,       (None, '$ in (1,1,2,3,7)',             ('Display',     '"DisplayFont {}".format($)')) ),
    'display_width':                (HARDWARE.ESP,   '<H',  0x774,       (None, None,                           ('Display',     '"DisplayWidth {}".format($)')) ),
    'display_height':               (HARDWARE.ESP,   '<H',  0x776,       (None, None,                           ('Display',     '"DisplayHeight {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_3 = copy.deepcopy(SETTING_6_6_0_2)
SETTING_6_6_0_3['flag3'][1].update  ({
        'pwm_multi_channels':       (HARDWARE.ESP,   '<L', (0x3A0,1,18), (None, None,                           ('SetOption',   '"SetOption68 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_5 = copy.deepcopy(SETTING_6_6_0_3)
SETTING_6_6_0_5.update              ({
    'sensors':                      (HARDWARE.ESP,   '<L',  0x7A4,       ([3],  None,                           ('Wifi',        'list("WebSensor{} {}".format((#*32)+i, 1 if (int($,0) & (1<<i)) else 0) for i in range(0, 32))')), '"0x{:08x}".format($)' ),
                                    })
SETTING_6_6_0_5['flag3'][1].update  ({
        'tuya_dimmer_min_limit':    (HARDWARE.ESP,   '<L', (0x3A0,1,19), (None, None,                           ('SetOption',   '"SetOption69 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_6 = copy.deepcopy(SETTING_6_6_0_5)
SETTING_6_6_0_6['flag3'][1].pop('tuya_show_dimmer',None)
SETTING_6_6_0_6['flag3'][1].update  ({
        'tuya_disable_dimmer':      (HARDWARE.ESP,   '<L', (0x3A0,1,15), (None, None,                           ('SetOption',   '"SetOption65 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_7 = copy.deepcopy(SETTING_6_6_0_6)
SETTING_6_6_0_7.update              ({
    'energy_usage':                 (HARDWARE.ESP, {
        'usage1_kWhtotal':          (HARDWARE.ESP,   '<L',  0x77C,       (None, None,                           ('Power',       None)) ),
        'usage1_kWhtoday':          (HARDWARE.ESP,   '<L',  0x780,       (None, None,                           ('Power',       None)) ),
        'return1_kWhtotal':         (HARDWARE.ESP,   '<L',  0x784,       (None, None,                           ('Power',       None)) ),
        'return2_kWhtotal':         (HARDWARE.ESP,   '<L',  0x788,       (None, None,                           ('Power',       None)) ),
        'last_usage_kWhtotal':      (HARDWARE.ESP,   '<L',  0x78C,       (None, None,                           ('Power',       None)) ),
        'last_return_kWhtotal':     (HARDWARE.ESP,   '<L',  0x790,       (None, None,                           ('Power',       None)) ),
                                    },                      0x77C,       (None, None,                           ('Power',       None)) ),
                                    })
# ======================================================================
SETTING_6_6_0_8 = copy.deepcopy(SETTING_6_6_0_7)
SETTING_6_6_0_8['flag3'][1].update  ({
        'energy_weekend':           (HARDWARE.ESP,   '<L', (0x3A0,1,20), (None, None,                           ('Power',       '"Tariff3 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_9 = copy.deepcopy(SETTING_6_6_0_8)
SETTING_6_6_0_9.update              ({
    'baudrate':                     (HARDWARE.ESP,   '<H',  0x778,       (None, None,                           ('Serial',      '"Baudrate {}".format($)')), ('$ * 1200','$ // 1200') ),
    'sbaudrate':                    (HARDWARE.ESP,   '<H',  0x77A,       (None, None,                           ('Serial',      '"SBaudrate {}".format($)')), ('$ * 1200','$ // 1200') ),
                                    })
# ======================================================================
SETTING_6_6_0_10 = copy.deepcopy(SETTING_6_6_0_9)
SETTING_6_6_0_10['flag3'][1].pop('tuya_disable_dimmer',None)
SETTING_6_6_0_10.update             ({
    'cfg_timestamp':                (HARDWARE.ESP,   '<L',  0xFF8,       (None, None,                           ('System',      None)) ),
    'cfg_crc32':                    (HARDWARE.ESP,   '<L',  0xFFC,       (None, None,                           ('System',      None)), '"0x{:08x}".format($)' ),
    'tuya_fnid_map':                (HARDWARE.ESP, {
        'fnid':                     (HARDWARE.ESP,   'B',   0xE00,       (None, None,                           ('Management',  '"TuyaMCU {},{}".format($,@["tuya_fnid_map"][#]["dpid"]) if ($!=0 or @["tuya_fnid_map"][#]["dpid"]!=0) else None')) ),
        'dpid':                     (HARDWARE.ESP,   'B',   0xE01,       (None, None,                           ('Management',  None)) ),
                                    },                      0xE00,       ([16], None,                           ('Management',  None)), (None, None) ),
                                    })
SETTING_6_6_0_10['flag2'][1].update ({
        'time_format':              (HARDWARE.ESP,   '<L', (0x5BC,2, 4), (None, '0 <= $ <= 2',                  ('Management', '"Time {}".format($+1)')) ),
                                    })
SETTING_6_6_0_10['flag3'][1].pop('tuya_show_dimmer',None)
# ======================================================================
SETTING_6_6_0_11 = copy.deepcopy(SETTING_6_6_0_10)
SETTING_6_6_0_11.update             ({
    'ina226_r_shunt':               (HARDWARE.ESP,   '<H',  0xE20,       ([4], None,                            ('Power',       '"Sensor54 {}1 {}".format(#+1,$)')) ),
    'ina226_i_fs':                  (HARDWARE.ESP,   '<H',  0xE28,       ([4], None,                            ('Power',       '"Sensor54 {}2 {}".format(#+1,$)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_12 = copy.deepcopy(SETTING_6_6_0_11)
SETTING_6_6_0_12.update             ({
    'register8_ENERGY_TARIFF1_ST':  (HARDWARE.ESP,   'B',   0x1D6,       (None, None,                           ('Power',       '"Tariff1 {},{}".format($,@["register8_ENERGY_TARIFF1_DS"])')) ),
    'register8_ENERGY_TARIFF2_ST':  (HARDWARE.ESP,   'B',   0x1D7,       (None, None,                           ('Power',       '"Tariff2 {},{}".format($,@["register8_ENERGY_TARIFF2_DS"])')) ),
    'register8_ENERGY_TARIFF1_DS':  (HARDWARE.ESP,   'B',   0x1D8,       (None, None,                           ('Power',       None)) ),
    'register8_ENERGY_TARIFF2_DS':  (HARDWARE.ESP,   'B',   0x1D9,       (None, None,                           ('Power',       None)) ),
                                    })
SETTING_6_6_0_12['flag3'][1].update ({
        'energy_weekend':           (HARDWARE.ESP,   '<L', (0x3A0,1,20), (None, None,                           ('Power',       '"Tariff9 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_13 = copy.deepcopy(SETTING_6_6_0_12)
SETTING_6_6_0_13['SensorBits1'][1].update ({
        'hx711_json_weight_change': (HARDWARE.ESP,   'B',  (0x717,1, 6), (None, None,                           ('Sensor',      '"Sensor34 8 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_14 = copy.deepcopy(SETTING_6_6_0_13)
SETTING_6_6_0_14.pop('register8_ENERGY_TARIFF1_ST',None)
SETTING_6_6_0_14.pop('register8_ENERGY_TARIFF2_ST',None)
SETTING_6_6_0_14.pop('register8_ENERGY_TARIFF1_DS',None)
SETTING_6_6_0_14.pop('register8_ENERGY_TARIFF2_DS',None)
SETTING_6_6_0_14.update             ({
    'register8':                    (HARDWARE.ESP,   'B',   0x1D6,       ([16], None,                           ('Power',       None)) ),
    'tariff1_0':                    (HARDWARE.ESP,   '<H',  0xE30,       (None, None,                           ('Power',       '"Tariff1 {:02d}:{:02d},{:02d}:{:02d}".format(@["tariff1_0"]//60,@["tariff1_0"]%60,@["tariff1_1"]//60,@["tariff1_1"]%60)')) ),
    'tariff1_1':                    (HARDWARE.ESP,   '<H',  0xE32,       (None, None,                           ('Power',       None)) ),
    'tariff2_0':                    (HARDWARE.ESP,   '<H',  0xE34,       (None, None,                           ('Power',       '"Tariff2 {:02d}:{:02d},{:02d}:{:02d}".format(@["tariff2_0"]//60,@["tariff2_0"]%60,@["tariff2_1"]//60,@["tariff2_1"]%60)')) ),
    'tariff2_1':                    (HARDWARE.ESP,   '<H',  0xE36,       (None, None,                           ('Power',       None)) ),
    'mqttlog_level':                (HARDWARE.ESP,   'B',   0x1E7,       (None, None,                           ('Management', '"MqttLog {}".format($)')) ),
    'pcf8574_config':               (HARDWARE.ESP,   'B',   0xE88,       ([8],  None,                           ('Sensor',      None)) ),
    'shutter_accuracy':             (HARDWARE.ESP,   'B',   0x1E6,       (None, None,                           ('Shutter',     None)) ),
    'shutter_opentime':             (HARDWARE.ESP,   '<H',  0xE40,       ([4],  None,                           ('Shutter',     '"ShutterOpenDuration{} {:.1f}".format(#+1,float($)/10.0)')) ),
    'shutter_closetime':            (HARDWARE.ESP,   '<H',  0xE48,       ([4],  None,                           ('Shutter',     '"ShutterCloseDuration{} {:.1f}".format(#+1,float($)/10.0)')) ),
    'shuttercoeff':                 (HARDWARE.ESP,   '<H',  0xE50,       ([5,4],None,                           ('Shutter',     'list("ShutterCalibration{} {}".format(k+1, list(",".join(str(@["shuttercoeff"][i][j]) for i in range(0, len(@["shuttercoeff"]))) for j in range(0, len(@["shuttercoeff"][0])))[k]) for k in range(0,len(@["shuttercoeff"][0])))')) ),
    'shutter_invert':               (HARDWARE.ESP,   'B',   0xE78,       ([4],  None,                           ('Shutter',     '"ShutterInvert{} {}".format(#+1,$)')) ),
    'shutter_set50percent':         (HARDWARE.ESP,   'B',   0xE7C,       ([4],  None,                           ('Shutter',     '"ShutterSetHalfway{} {}".format(#+1,$)')) ),
    'shutter_position':             (HARDWARE.ESP,   'B',   0xE80,       ([4],  None,                           ('Shutter',     '"ShutterPosition{} {}".format(#+1,$)')) ),
    'shutter_startrelay':           (HARDWARE.ESP,   'B',   0xE84,       ([4],  None,                           ('Shutter',     '"ShutterRelay{} {}".format(#+1,$)')) ),
                                    })
SETTING_6_6_0_14['flag3'][1].update ({
        'dds2382_model':            (HARDWARE.ESP,   '<L', (0x3A0,1,21), (None, None,                           ('SetOption',   '"SetOption71 {}".format($)')) ),
        'shutter_mode':             (HARDWARE.ESP,   '<L', (0x3A0,1,30), (None, None,                           ('SetOption',   '"SetOption80 {}".format($)')) ),
        'pcf8574_ports_inverted':   (HARDWARE.ESP,   '<L', (0x3A0,1,31), (None, None,                           ('SetOption',   '"SetOption81 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_15 = copy.deepcopy(SETTING_6_6_0_14)
SETTING_6_6_0_15['flag3'][1].update ({
        'hardware_energy_total':    (HARDWARE.ESP,   '<L', (0x3A0,1,22), (None, None,                           ('SetOption',   '"SetOption72 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_18 = copy.deepcopy(SETTING_6_6_0_15)
SETTING_6_6_0_18['flag3'][1].pop('tuya_dimmer_range_255',None)
SETTING_6_6_0_18['flag3'][1].pop('tuya_dimmer_min_limit',None)
SETTING_6_6_0_18.pop('novasds_period',None)
SETTING_6_6_0_18.update             ({
    'dimmer_hw_min':                (HARDWARE.ESP,   '<H',  0xE90,       (None, None,                           ('Light',       '"DimmerRange {},{}".format($,@["dimmer_hw_max"])')) ),
    'dimmer_hw_max':                (HARDWARE.ESP,   '<H',  0xE92,       (None, None,                           ('Light',       None)) ),
    'deepsleep':                    (HARDWARE.ESP,   '<H',  0xE94,       (None, '0 or 10 <= $ <= 86400',        ('Management',  '"DeepSleepTime {}".format($)')) ),
    'novasds_startingoffset':       (HARDWARE.ESP,   'B',   0x73D,       (None, '1 <= $ <= 255',                ('Sensor',      '"Sensor20 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_20 = copy.deepcopy(SETTING_6_6_0_18)
SETTING_6_6_0_20['flag3'][1].update ({
        'fast_power_cycle_disable': (HARDWARE.ESP,   '<L', (0x3A0,1,15), (None, None,                           ('SetOption',   '"SetOption65 {}".format($)')) ),
                                    })
SETTING_6_6_0_20.update             ({
    'energy_power_delta':           (HARDWARE.ESP,   '<H',  0xE98,       (None, '0 <= $ < 32000',               ('Power',       '"PowerDelta {}".format($)')) ),
                                    })
# ======================================================================
SETTING_6_6_0_21 = copy.deepcopy(SETTING_6_6_0_20)
SETTING_6_6_0_21['flag'][1].pop('value_units',None)
SETTING_6_6_0_21['flag3'][1].pop('tuya_dimmer_range_255',None)
SETTING_6_6_0_21['flag3'][1].update ({
        'tuya_serial_mqtt_publish': (HARDWARE.ESP,   '<L', (0x3A0,1,16), (None, None,                           ('SetOption',   '"SetOption66 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_7_0_0_1 = copy.deepcopy(SETTING_6_6_0_21)
SETTING_7_0_0_1.pop('register8',None)
SETTING_7_0_0_1.update             ({
    'shutter_motordelay':           (HARDWARE.ESP,   'B',   0xE9A,       ([4],  None,                           ('Shutter',     '"ShutterMotorDelay{} {:.1f}".format(#+1,float($)/20.0)')) ),
    'flag4':                        (HARDWARE.ESP,   '<L',  0x1E0,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
                                    })
SETTING_7_0_0_1['flag3'][1].update  ({
        'cors_enabled':             (HARDWARE.ESP,   '<L', (0x3A0,1,23), (None, None,                           ('SetOption',   '"SetOption73 {}".format($)')) ),
        'ds18x20_internal_pullup':  (HARDWARE.ESP,   '<L', (0x3A0,1,24), (None, None,                           ('SetOption',   '"SetOption74 {}".format($)')) ),
        'grouptopic_mode':          (HARDWARE.ESP,   '<L', (0x3A0,1,25), (None, None,                           ('SetOption',   '"SetOption75 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_7_0_0_2 = copy.deepcopy(SETTING_7_0_0_1)
SETTING_7_0_0_2.update              ({
    'web_color2':                   (HARDWARE.ESP,   '3B',  0xEA0,       ([1],  None,                           ('Wifi',        '"WebColor{} {}{:06x}".format(#+19,chr(35),int($,0))')), '"0x{:06x}".format($)' ),
                                    })
# ======================================================================
SETTING_7_0_0_3 = copy.deepcopy(SETTING_7_0_0_2)
SETTING_7_0_0_3.update              ({
    'i2c_drivers':                  (HARDWARE.ESP,   '<L',  0xFEC,       ([3],  None,                           ('Management',  'list("I2CDriver{} {}".format((#*32)+i, 1 if (int($,0) & (1<<i)) else 0) for i in range(0, 32))')),'"0x{:08x}".format($)' ),
                                    })
# ======================================================================
SETTING_7_0_0_4 = copy.deepcopy(SETTING_7_0_0_3)
SETTING_7_0_0_4.update              ({
    'wifi_output_power':            (HARDWARE.ESP,   'B',   0x1E5,       (None, None,                           ('Wifi',        '"WifiPower {:.1f}".format(float($)/10.0)')) ),
                                    })
SETTING_7_0_0_4['flag3'][1].update  ({
        'bootcount_update':         (HARDWARE.ESP,   '<L', (0x3A0,1,26), (None, None,                           ('SetOption',   '"SetOption76 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_7_0_0_5 = copy.deepcopy(SETTING_7_0_0_4)
SETTING_7_0_0_5.update              ({
    'temp_comp':                    (HARDWARE.ESP,   'b',   0xE9E,       (None, '-127 < $ < 127',               ('Sensor',      '"TempOffset {:.1f}".format(float($)/10.0)')) ),
                                    })
# ======================================================================
SETTING_7_0_0_6 = copy.deepcopy(SETTING_7_0_0_5)
SETTING_7_0_0_6['flag3'][1].update  ({
        'slider_dimmer_stay_on':    (HARDWARE.ESP,   '<L', (0x3A0,1,27), (None, None,                           ('SetOption',   '"SetOption77 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_7_1_2_2 = copy.deepcopy(SETTING_7_0_0_6)
SETTING_7_1_2_2.update              ({
    'serial_config':                (HARDWARE.ESP,   'B',   0x14E,       (None, '0 <= $ <= 23',                 ('Serial',      '"SerialConfig {}".format(("5N1","6N1","7N1","8N1","5N2","6N2","7N2","8N2","5E1","6E1","7E1","8E1","5E2","6E2","7E2","8E2","5O1","6O1","7O1","8O1","5O2","6O2","7O2","8O2")[$ % 24])')) ),
                                    })
# ======================================================================
SETTING_7_1_2_3 = copy.deepcopy(SETTING_7_1_2_2)
SETTING_7_1_2_3['flag3'][1].pop('cors_enabled',None)
SETTING_7_1_2_3.update              ({
    'cors_domain':                  (HARDWARE.ESP,   '33s', 0xEA6,       (None, None,                           ('Wifi',        '"CORS {}".format($ if len($) else \'"\')')) ),
    'weight_change':                (HARDWARE.ESP,   'B',   0xE9F,       (None, None,                           ('Management',  '"Sensor34 9 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_7_1_2_5 = copy.deepcopy(SETTING_7_1_2_3)
SETTING_7_1_2_5.update              ({
    'seriallog_level':              (HARDWARE.ESP,   'B',   0x452,       (None, '0 <= $ <= 4',                  ('Management',  '"SerialLog {}".format($)')) ),
    'sta_config':                   (HARDWARE.ESP,   'B',   0xEC7,       (None, '0 <= $ <= 7',                  ('Wifi',        '"WifiConfig {}".format($)')) ),
    'sta_active':                   (HARDWARE.ESP,   'B',   0xEC8,       (None, '0 <= $ <= 1',                  ('Wifi',        '"AP {}".format($)')) ),
    'rule_stop':                    (HARDWARE.ESP, {
        'rule1':                    (HARDWARE.ESP,   'B',  (0xEC9,1,0),  (None, None,                           ('Rules',       '"Rule1 {}".format($+8)')) ),
        'rule2':                    (HARDWARE.ESP,   'B',  (0xEC9,1,1),  (None, None,                           ('Rules',       '"Rule2 {}".format($+8)')) ),
        'rule3':                    (HARDWARE.ESP,   'B',  (0xEC9,1,2),  (None, None,                           ('Rules',       '"Rule3 {}".format($+8)')) ),
                                     },     0xEC9,        None),
    'syslog_port':                  (HARDWARE.ESP,   '<H',  0xECA,       (None, '1 <= $ <= 32766',              ('Management',  '"LogPort {}".format($)')) ),
    'syslog_level':                 (HARDWARE.ESP,   'B',   0xECC,       (None, '0 <= $ <= 4',                  ('Management',  '"SysLog {}".format($)')) ),
    'webserver':                    (HARDWARE.ESP,   'B',   0xECD,       (None, '0 <= $ <= 2',                  ('Wifi',        '"WebServer {}".format($)')) ),
    'weblog_level':                 (HARDWARE.ESP,   'B',   0xECE,       (None, '0 <= $ <= 4',                  ('Management',  '"WebLog {}".format($)')) ),
    'mqtt_fingerprint1':            (HARDWARE.ESP,   'B',   0xECF,       ([20], None,                           ('MQTT',        '"MqttFingerprint1 {}".format(" ".join("{:02X}".format(c) for c in @["mqtt_fingerprint1"]))')), '"0x{:02x}".format($)' ),
    'mqtt_fingerprint2':            (HARDWARE.ESP,   'B',   0xECF+20,    ([20], None,                           ('MQTT',        '"MqttFingerprint2 {}".format(" ".join("{:02X}".format(c) for c in @["mqtt_fingerprint2"]))')), '"0x{:02x}".format($)' ),
    'adc_param_type':               (HARDWARE.ESP,   'B',   0xEF7,       (None, '2 <= $ <= 3',                  ('Sensor',       '"AdcParam {type},{param1},{param2},{param3}".format(type=$,param1=@["adc_param1"],param2=@["adc_param2"],param3=@["adc_param3"]//10000)')) ),
                                    })
# ======================================================================
SETTING_7_1_2_6 = copy.deepcopy(SETTING_7_1_2_5)
SETTING_7_1_2_6.update              ({
    'flag4':                        (HARDWARE.ESP,   '<L',  0xEF8,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
    'serial_config':                (HARDWARE.ESP,   'B',   0xEFE,       (None, '0 <= $ <= 23',                 ('Serial',      '"SerialConfig {}".format(("5N1","6N1","7N1","8N1","5N2","6N2","7N2","8N2","5E1","6E1","7E1","8E1","5E2","6E2","7E2","8E2","5O1","6O1","7O1","8O1","5O2","6O2","7O2","8O2")[$ % 24])')) ),
    'wifi_output_power':            (HARDWARE.ESP,   'B',   0xEFF,       (None, None,                           ('Wifi',        '"WifiPower {:.1f}".format(float($)/10.0)')) ),
    'mqtt_port':                    (HARDWARE.ESP,   '<H',  0xEFC,       (None, None,                           ('MQTT',        '"MqttPort {}".format($)')) ),
    'shutter_accuracy':             (HARDWARE.ESP,   'B',   0xF00,       (None, None,                           ('Shutter',     None)) ),
    'mqttlog_level':                (HARDWARE.ESP,   'B',   0xF01,       (None, None,                           ('Management',  '"MqttLog {}".format($)')) ),
    'sps30_inuse_hours':            (HARDWARE.ESP,   'B',   0xF02,       (None, None,                           (INTERNAL,      None)) ),
                                    })
SETTING_7_1_2_6['flag3'][1].update  ({
        'compatibility_check':      (HARDWARE.ESP,   '<L', (0x3A0,1,28), (None, None,                           ('SetOption',   '"SetOption78 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_0_0_1 = copy.deepcopy(SETTING_7_1_2_6)
SETTING_8_0_0_1.update              ({
    # v8.x.x.x: Index numbers for indexed strings
    SETTINGVAR:
    {
        HARDWARE.hstr(HARDWARE.ESP):
                       ['SET_OTAURL',
                        'SET_MQTTPREFIX1', 'SET_MQTTPREFIX2', 'SET_MQTTPREFIX3',
                        'SET_STASSID1', 'SET_STASSID2',
                        'SET_STAPWD1', 'SET_STAPWD2',
                        'SET_HOSTNAME', 'SET_SYSLOG_HOST',
                        'SET_WEBPWD', 'SET_CORS',
                        'SET_MQTT_HOST', 'SET_MQTT_CLIENT',
                        'SET_MQTT_USER', 'SET_MQTT_PWD',
                        'SET_MQTT_FULLTOPIC', 'SET_MQTT_TOPIC',
                        'SET_MQTT_BUTTON_TOPIC', 'SET_MQTT_SWITCH_TOPIC', 'SET_MQTT_GRP_TOPIC',
                        'SET_STATE_TXT1', 'SET_STATE_TXT2', 'SET_STATE_TXT3', 'SET_STATE_TXT4',
                        'SET_NTPSERVER1', 'SET_NTPSERVER2', 'SET_NTPSERVER3',
                        'SET_MEM1', 'SET_MEM2', 'SET_MEM3', 'SET_MEM4', 'SET_MEM5', 'SET_MEM6', 'SET_MEM7', 'SET_MEM8',
                        'SET_MEM9', 'SET_MEM10', 'SET_MEM11', 'SET_MEM12', 'SET_MEM13', 'SET_MEM14', 'SET_MEM15', 'SET_MEM16',
                        'SET_FRIENDLYNAME1', 'SET_FRIENDLYNAME2', 'SET_FRIENDLYNAME3', 'SET_FRIENDLYNAME4',
                        'SET_FRIENDLYNAME5', 'SET_FRIENDLYNAME6', 'SET_FRIENDLYNAME7', 'SET_FRIENDLYNAME8',
                        'SET_BUTTON1', 'SET_BUTTON2', 'SET_BUTTON3', 'SET_BUTTON4', 'SET_BUTTON5', 'SET_BUTTON6', 'SET_BUTTON7', 'SET_BUTTON8',
                        'SET_BUTTON9', 'SET_BUTTON10', 'SET_BUTTON11', 'SET_BUTTON12', 'SET_BUTTON13', 'SET_BUTTON14', 'SET_BUTTON15', 'SET_BUTTON16',
                        'SET_MAX']
    }
                                    })
SETTING_8_0_0_1[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP82): copy.deepcopy(SETTING_8_0_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_0_0_1[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP32): copy.deepcopy(SETTING_8_0_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_0_0_1.update              ({
    'ota_url':                      (HARDWARE.ESP,   '699s',(0x017,'SET_OTAURL'),
                                                                         (None, None,                           ('Management',  '"OtaUrl {}".format($)')) ),
    'mqtt_prefix':                  (HARDWARE.ESP,   '699s',(0x017,'SET_MQTTPREFIX1'),
                                                                         ([3],  None,                           ('MQTT',        '"Prefix{} {}".format(#+1,$)')) ),
    'sta_ssid':                     (HARDWARE.ESP,   '699s',(0x017,'SET_STASSID1'),
                                                                         ([2],  None,                           ('Wifi',        '"SSId{} {}".format(#+1,$)')) ),
    'sta_pwd':                      (HARDWARE.ESP,   '699s',(0x017,'SET_STAPWD1'),
                                                                         ([2],  None,                           ('Wifi',        '"Password{} {}".format(#+1,$)')), (passwordread, passwordwrite) ),
    'hostname':                     (HARDWARE.ESP,   '699s',(0x017,'SET_HOSTNAME'),
                                                                         (None, None,                           ('Wifi',        '"Hostname {}".format($)')) ),
    'syslog_host':                  (HARDWARE.ESP,   '699s',(0x017,'SET_SYSLOG_HOST'),
                                                                         (None, None,                           ('Management',  '"LogHost {}".format($)')) ),
    'web_password':                 (HARDWARE.ESP,   '699s',(0x017,'SET_WEBPWD'),
                                                                         (None, None,                           ('Wifi',        '"WebPassword {}".format($)')), (passwordread, passwordwrite) ),
    'cors_domain':                  (HARDWARE.ESP,   '699s',(0x017,'SET_CORS'),
                                                                         (None, None,                           ('Wifi',        '"CORS {}".format($ if len($) else \'"\')')) ),
    'mqtt_host':                    (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_HOST'),
                                                                         (None, None,                           ('MQTT',        '"MqttHost {}".format($)')) ),
    'mqtt_client':                  (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_CLIENT'),
                                                                         (None, None,                           ('MQTT',        '"MqttClient {}".format($)')) ),
    'mqtt_user':                    (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_USER'),
                                                                         (None, None,                           ('MQTT',        '"MqttUser {}".format($)')) ),
    'mqtt_pwd':                     (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_PWD'),
                                                                        (None, None,                            ('MQTT',        '"MqttPassword {}".format($)')), (passwordread, passwordwrite) ),
    'mqtt_fulltopic':               (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_FULLTOPIC'),
                                                                         (None, None,                           ('MQTT',        '"FullTopic {}".format($)')) ),
    'mqtt_topic':                   (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_TOPIC'),
                                                                         (None, None,                           ('MQTT',        '"Topic {}".format($)')) ),
    'button_topic':                 (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_BUTTON_TOPIC'),
                                                                         (None, None,                           ('MQTT',        '"ButtonTopic {}".format($)')) ),
    'switch_topic':                 (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_SWITCH_TOPIC'),
                                                                         (None, None,                           ('MQTT',        '"SwitchTopic {}".format($)')) ),
    'mqtt_grptopic':                (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_GRP_TOPIC'),
                                                                         (None, None,                           ('MQTT',        '"GroupTopic {}".format($)')) ),
    'state_text':                   (HARDWARE.ESP,   '699s',(0x017,'SET_STATE_TXT1'),
                                                                         ([4],  None,                           ('MQTT',        '"StateText{} {}".format(#+1,$)')) ),
    'ntp_server':                   (HARDWARE.ESP,   '699s',(0x017,'SET_NTPSERVER1'),
                                                                         ([3],  None,                           ('Management',  '"NtpServer{} {}".format(#+1,$)')) ),
    'mems':                         (HARDWARE.ESP,   '699s',(0x017,'SET_MEM1'),
                                                                         ([16], None,                           ('Rules',       '"Mem{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
    'friendlyname':                 (HARDWARE.ESP,   '699s',(0x017,'SET_FRIENDLYNAME1'),
                                                                         ([4],  None,                           ('Management',  '"FriendlyName{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
    'script_pram':                  (HARDWARE.ESP,   'b',   0x7CE,       ([5,10],None,                          ('Rules',       None )) ),
                                    })
# ======================================================================
SETTING_8_1_0_0 = copy.deepcopy(SETTING_8_0_0_1)
SETTING_8_1_0_0.update              ({
    'friendlyname':                 (HARDWARE.ESP,   '699s',(0x017,'SET_FRIENDLYNAME1'),
                                                                         ([8],  None,                           ('Management',  '"FriendlyName{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
    'button_text':                  (HARDWARE.ESP,   '699s',(0x017,'SET_BUTTON1'),
                                                                         ([16], None,                           ('Control',     '"Webbutton{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
                                    })
# ======================================================================
SETTING_8_1_0_1 = copy.deepcopy(SETTING_8_1_0_0)
SETTING_8_1_0_1['flag3'][1].update  ({
        'counter_reset_on_tele':    (HARDWARE.ESP,   '<L', (0x3A0,1,29), (None, None,                           ('SetOption',   '"SetOption79 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_1_0_2 = copy.deepcopy(SETTING_8_1_0_1)
SETTING_8_1_0_2.update              ({
    'hotplug_scan':                 (HARDWARE.ESP,   'B',   0xF03,       (None, None,                           ('Sensor',      '"HotPlug {}".format($)')) ),
    'shutter_button':               (HARDWARE.ESP,   '<L',  0xFDC,       ([4],  None,                           ('Shutter',     '"ShutterButton{} {a} {b} {c} {d} {e} {f} {g} {h} {i} {j}".format(#+1, a=(($>> 0)&(0x03))+1, b=((($>> 2)&(0x3f))-1)<<1, c=((($>> 8)&(0x3f))-1)<<1, d=((($>>14)&(0x3f))-1)<<1, e=((($>>20)&(0x3f))-1)<<1, f=($>>26)&(0x01), g=($>>27)&(0x01),  h=($>>28)&(0x01), i=($>>29)&(0x01), j=($>>30)&(0x01) ) if $!=0 else "ShutterButton{} {}".format(#+1,0)')),'"0x{:08x}".format($)' ),
                                    })
# ======================================================================
SETTING_8_1_0_3 = copy.deepcopy(SETTING_8_1_0_2)
SETTING_8_1_0_3.pop('shutter_invert',None)
SETTING_8_1_0_3.update              ({
    'shutter_options':              (HARDWARE.ESP,   'B',   0xE78,       ([4],  None,                           ('Shutter',     ('"ShutterInvert{} {}".format(#+1,1 if $ & 1 else 0)',\
                                                                                                                                 '"ShutterLock{} {}".format(#+1,1 if $ & 2 else 0)',\
                                                                                                                                 '"ShutterEnableEndStopTime{} {}".format(#+1,1 if $ & 4 else 0)'))) ),
    'shutter_button':               (HARDWARE.ESP, {
        'shutter':                  (HARDWARE.ESP,   '<L', (0xFDC,2, 0), (None, None,                           ('Shutter',     '"ShutterButton{x} {a} {b} {c} {d} {e} {f} {g} {h} {i} {j}".format( \
                                                                                                                                    x=1+@["shutter_button"][#]["shutter"], \
                                                                                                                                    a=#+1, \
                                                                                                                                    b=@["shutter_button"][#]["press_single"], \
                                                                                                                                    c=@["shutter_button"][#]["press_double"], \
                                                                                                                                    d=@["shutter_button"][#]["press_triple"], \
                                                                                                                                    e=@["shutter_button"][#]["press_hold"], \
                                                                                                                                    f=@["shutter_button"][#]["mqtt_broadcast_single"], \
                                                                                                                                    g=@["shutter_button"][#]["mqtt_broadcast_double"], \
                                                                                                                                    h=@["shutter_button"][#]["mqtt_broadcast_triple"], \
                                                                                                                                    i=@["shutter_button"][#]["mqtt_broadcast_hold"], \
                                                                                                                                    j=@["shutter_button"][#]["mqtt_broadcast_all"] \
                                                                                                                                )')), ('$+1','$-1') ),
        'press_single':             (HARDWARE.ESP,   '<L', (0xFDC,6, 2), (None, None,                           ('Shutter',     None)), ('"-" if $==0 else ($-1)<<1','0 if $=="-" else (int(str($),0)>>1)+1') ),
        'press_double':             (HARDWARE.ESP,   '<L', (0xFDC,6, 8), (None, None,                           ('Shutter',     None)), ('"-" if $==0 else ($-1)<<1','0 if $=="-" else (int(str($),0)>>1)+1') ),
        'press_triple':             (HARDWARE.ESP,   '<L', (0xFDC,6,14), (None, None,                           ('Shutter',     None)), ('"-" if $==0 else ($-1)<<1','0 if $=="-" else (int(str($),0)>>1)+1') ),
        'press_hold':               (HARDWARE.ESP,   '<L', (0xFDC,6,20), (None, None,                           ('Shutter',     None)), ('"-" if $==0 else ($-1)<<1','0 if $=="-" else (int(str($),0)>>1)+1') ),
        'mqtt_broadcast_single':    (HARDWARE.ESP,   '<L', (0xFDC,1,26), (None, None,                           ('Shutter',     None)) ),
        'mqtt_broadcast_double':    (HARDWARE.ESP,   '<L', (0xFDC,1,27), (None, None,                           ('Shutter',     None)) ),
        'mqtt_broadcast_triple':    (HARDWARE.ESP,   '<L', (0xFDC,1,28), (None, None,                           ('Shutter',     None)) ),
        'mqtt_broadcast_hold':      (HARDWARE.ESP,   '<L', (0xFDC,1,29), (None, None,                           ('Shutter',     None)) ),
        'mqtt_broadcast_all':       (HARDWARE.ESP,   '<L', (0xFDC,1,30), (None, None,                           ('Shutter',     None)) ),
        'enabled':                  (HARDWARE.ESP,   '<L', (0xFDC,1,31), (None, None,                           ('Shutter',     None)) ),
                                    },                      0xFDC,       ([4], None,                            ('Shutter',     None)), (None, None) ),
    'flag4':                        (HARDWARE.ESP, {
        'alexa_ct_range':           (HARDWARE.ESP,   '<L', (0xEF8,1, 0), (None, None,                           ('SetOption',   '"SetOption82 {}".format($)')) ),
                                    },                      0xEF8,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
# ======================================================================
SETTING_8_1_0_4 = copy.deepcopy(SETTING_8_1_0_3)
SETTING_8_1_0_4.update              ({
    'switchmode':                   (HARDWARE.ESP,   'B',   0x3A4,       ([8],  '0 <= $ <= 10',                 ('Control',     '"SwitchMode{} {}".format(#+1,$)')) ),
    'adc_param_type':               (HARDWARE.ESP,   'B',   0xEF7,       (None, '2 <= $ <= 7',                  ('Sensor',      '"AdcParam {type},{param1},{param2},{param3},{param4}".format(type=@["my_adc0"],param1=@["adc_param1"],param2=@["adc_param2"],param3=@["adc_param3"],param4=@["adc_param4"]) \
                                                                                                                  if 6==@["my_adc0"] \
                                                                                                                  else \
                                                                                                                  "AdcParam {type},{param1},{param2},{param3}".format(type=@["my_adc0"],param1=@["adc_param1"],param2=@["adc_param2"],param3=@["adc_param3"]/10000)')) ),
    'adc_param4':                   (HARDWARE.ESP,   '<l',  0xFD8,       (None, None,                           ('Sensor',      None)) ),
                                    })
SETTING_8_1_0_4['flag4'][1].update  ({
        'zigbee_use_names':         (HARDWARE.ESP,   '<L', (0xEF8,1, 1), (None, None,                           ('SetOption',   '"SetOption83 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_1_0_5 = copy.deepcopy(SETTING_8_1_0_4)
SETTING_8_1_0_5.update              ({
    'keeloq_master_msb':            (HARDWARE.ESP,   '<L',  0xFBC,       (None, None,                           ('Shutter',     '"KeeloqSet {} {} {} {}".format(@["keeloq_master_msb"],@["keeloq_master_lsb"],@["keeloq_serial"],@["keeloq_count"])')) ),
    'keeloq_master_lsb':            (HARDWARE.ESP,   '<L',  0xFC0,       (None, None,                           ('Shutter',     None)) ),
    'keeloq_serial':                (HARDWARE.ESP,   '<L',  0xFC4,       (None, None,                           ('Shutter',     None)) ),
    'keeloq_count':                 (HARDWARE.ESP,   '<L',  0xFC8,       (None, None,                           ('Shutter',     None)) ),
                                    })
SETTING_8_1_0_5['flag4'][1].update  ({
        'awsiot_shadow':            (HARDWARE.ESP,   '<L', (0xEF8,1, 2), (None, None,                           ('SetOption',   '"SetOption84 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_1_0_6 = copy.deepcopy(SETTING_8_1_0_5)
SETTING_8_1_0_6.update              ({
    'bootcount_reset_time':         (HARDWARE.ESP,   '<L',  0xFD4,       (None, None,                           ('System',      None)) ),
                                    })
# ======================================================================
SETTING_8_1_0_9 = copy.deepcopy(SETTING_8_1_0_6)
SETTING_8_1_0_9[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].pop()  # SET_MAX
SETTING_8_1_0_9[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MQTT_GRP_TOPIC2', 'SET_MQTT_GRP_TOPIC3', 'SET_MQTT_GRP_TOPIC4'])
SETTING_8_1_0_9[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MAX'])
SETTING_8_1_0_9[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP82): copy.deepcopy(SETTING_8_1_0_9[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_1_0_9[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP32): copy.deepcopy(SETTING_8_1_0_9[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_1_0_9.update              ({
    'device_group_share_in':        (HARDWARE.ESP,   '<L',  0xFCC,       (None, None,                           ('Control',     '"DevGroupShare 0x{:08x},0x{:08x}".format(@["device_group_share_in"],@["device_group_share_out"])')) ),
    'device_group_share_out':       (HARDWARE.ESP,   '<L',  0xFD0,       (None, None,                           ('Control',     None)) ),
    'bri_power_on':                 (HARDWARE.ESP,   'B',   0xF04,       (None, None,                           ('Light',       None)) ),
    'bri_min':                      (HARDWARE.ESP,   'B',   0xF05,       (None, None,                           ('Light',       '"BriMin {}".format($)')) ),
    'bri_preset_low':               (HARDWARE.ESP,   'B',   0xF06,       (None, None,                           ('Light',       '"BriPreset {},{}".format(@["bri_preset_low"],@["bri_preset_high"])')) ),
    'bri_preset_high':              (HARDWARE.ESP,   'B',   0xF07,       (None, None,                           ('Light',       None)) ),
    'mqtt_grptopicdev':             (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_GRP_TOPIC2'),
                                                                         ([3],  None,                           ('MQTT',        '"GroupTopic{} {}".format(#+2,$)')) ),
                                    })
SETTING_8_1_0_9['flag4'][1].update  ({
        'device_groups_enabled':    (HARDWARE.ESP,   '<L', (0xEF8,1, 3), (None, None,                           ('SetOption',   '"SetOption85 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_1_0_10 = copy.deepcopy(SETTING_8_1_0_9)
SETTING_8_1_0_10['flag2'][1].update ({
        'speed_conversion':         (HARDWARE.ESP,   '<L', (0x5BC,3, 1), (None, '0 <= $ <= 5',                  ('Sensor',      '"SpeedUnit {}".format($)')) ),
                                    })
SETTING_8_1_0_10['flag4'][1].update ({
        'led_timeout':              (HARDWARE.ESP,   '<L', (0xEF8,1, 4), (None, None,                           ('SetOption',   '"SetOption86 {}".format($)')) ),
        'powered_off_led':          (HARDWARE.ESP,   '<L', (0xEF8,1, 5), (None, None,                           ('SetOption',   '"SetOption87 {}".format($)')) ),
        'remote_device_mode':       (HARDWARE.ESP,   '<L', (0xEF8,1, 6), (None, None,                           ('SetOption',   '"SetOption88 {}".format($)')) ),
        'zigbee_distinct_topics':   (HARDWARE.ESP,   '<L', (0xEF8,1, 7), (None, None,                           ('SetOption',   '"SetOption89 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_1_0_11 = copy.deepcopy(SETTING_8_1_0_10)
SETTING_8_1_0_11.update             ({
    'hum_comp':                     (HARDWARE.ESP,   'b',   0xF08,       (None, '-101 < $ < 101',               ('Sensor',      '"HumOffset {:.1f}".format(float($)/10.0)')) ),
    'shutter_options':              (HARDWARE.ESP,   'B',   0xE78,       ([4],  None,                           ('Shutter',     ('"ShutterInvert{} {}".format(#+1,1 if $ & 1 else 0)',\
                                                                                                                                 '"ShutterLock{} {}".format(#+1,1 if $ & 2 else 0)',\
                                                                                                                                 '"ShutterEnableEndStopTime{} {}".format(#+1,1 if $ & 4 else 0)',\
                                                                                                                                 '"ShutterInvertWebButtons{} {}".format(#+1,1 if $ & 8 else 0)'))) ),
                                    })
# ======================================================================
SETTING_8_2_0_0 = copy.deepcopy(SETTING_8_1_0_11)
SETTING_8_2_0_0.update              ({
    'switchmode':                   (HARDWARE.ESP,   'B',   0x3A4,       ([8],  '0 <= $ <= 14',                 ('Control',     '"SwitchMode{} {}".format(#+1,$)')) ),
                                    })
# ======================================================================
SETTING_8_2_0_3 = copy.deepcopy(SETTING_8_2_0_0)
SETTING_8_2_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].pop()  # SET_MAX
SETTING_8_2_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_TEMPLATE_NAME', 'SET_DEV_GROUP_NAME1', 'SET_DEV_GROUP_NAME2', 'SET_DEV_GROUP_NAME3', 'SET_DEV_GROUP_NAME4'])
SETTING_8_2_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MAX'])
SETTING_8_2_0_3[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP82): copy.deepcopy(SETTING_8_2_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_2_0_3[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP32): copy.deepcopy(SETTING_8_2_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_2_0_3.pop('mqtt_grptopicdev',None)
SETTING_8_2_0_3.update              ({
    'templatename':                 (HARDWARE.ESP,   '699s',(0x017,'SET_TEMPLATE_NAME'),
                                                                         (None, None,                           ('Management',  '"Template {{\\\"NAME\\\":\\\"{}\\\"}}".format($)')) ),
    'pulse_counter_debounce_low':   (HARDWARE.ESP,   '<H',  0xFB8,       (None, '0 <= $ <= 32000',              ('Sensor',      '"CounterDebounceLow {}".format($)')) ),
    'pulse_counter_debounce_high':  (HARDWARE.ESP,   '<H',  0xFBA,       (None, '0 <= $ <= 32000',              ('Sensor',      '"CounterDebounceHigh {}".format($)')) ),
    'wifi_channel':                 (HARDWARE.ESP,   'B',   0xF09,       (None, None,                           ('Wifi',        None)) ),
    'wifi_bssid':                   (HARDWARE.ESP,   'B',   0xF0A,       ([6],  None,                           ('Wifi',        None)) ),
    'as3935_sensor_cfg':            (HARDWARE.ESP,   'B',   0xF10,       ([5],  None,                           ('Sensor',      None)) ),
    'as3935_functions':             (HARDWARE.ESP, {
        'nf_autotune':              (HARDWARE.ESP,   'B',  (0xF15,1, 0), (None, None,                           ('Sensor',      '"AS3935AutoNF {}".format($)')) ),
        'dist_autotune':            (HARDWARE.ESP,   'B',  (0xF15,1, 1), (None, None,                           ('Sensor',      '"AS3935AutoDisturber {}".format($)')) ),
        'nf_autotune_both':         (HARDWARE.ESP,   'B',  (0xF15,1, 2), (None, None,                           ('Sensor',      '"AS3935AutoNFMax {}".format($)')) ),
        'mqtt_only_Light_Event':    (HARDWARE.ESP,   'B',  (0xF15,1, 3), (None, None,                           ('Sensor',      '"AS3935MQTTEvent {}".format($)')) ),
                                    },                      0xF15,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
    'as3935_parameter':             (HARDWARE.ESP, {
        'nf_autotune_time':         (HARDWARE.ESP,   '<H', (0xF16,4, 0), (None, '0 <= $ <= 15',                 ('Sensor',      '"AS3935NFTime {}".format($)')) ),
        'dist_autotune_time':       (HARDWARE.ESP,   '<H', (0xF16,1, 4), (None, '0 <= $ <= 15',                 ('Sensor',      '"AS3935DistTime {}".format($)')) ),
        'nf_autotune_min':          (HARDWARE.ESP,   '<H', (0xF16,1, 8), (None, '0 <= $ <= 15',                 ('Sensor',      '"AS3935SetMinStage {}".format($)')) ),
                                    },                      0xF16,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
    'zb_ext_panid':                 (HARDWARE.ESP,   '<Q',  0xF18,       (None, None,                           ('Zigbee',      None)), '"0x{:016x}".format($)' ),
    'zb_precfgkey_l':               (HARDWARE.ESP,   '<Q',  0xF20,       (None, None,                           ('Zigbee',      None)), '"0x{:016x}".format($)' ),
    'zb_precfgkey_h':               (HARDWARE.ESP,   '<Q',  0xF28,       (None, None,                           ('Zigbee',      None)), '"0x{:016x}".format($)' ),
    'zb_pan_id':                    (HARDWARE.ESP,   '<H',  0xF30,       (None, None,                           ('Zigbee',      None)), '"0x{:016x}".format($)' ),
    'zb_channel':                   (HARDWARE.ESP,   'B',   0xF32,       (None, '11 <= $ <= 26',                ('Zigbee',      '"ZbConfig {{\\\"Channel\\\":{},\\\"PanID\\\":\\\"0x{:04X}\\\",\\\"ExtPanID\\\":\\\"0x{:016X}\\\",\\\"KeyL\\\":\\\"0x{:016X}\\\",\\\"KeyH\\\":\\\"0x{:016X}\\\"}}".format(@["zb_channel"], @["zb_pan_id"], @["zb_ext_panid"], @["zb_precfgkey_l"], @["zb_precfgkey_h"])')) ),
    'pms_wake_interval':            (HARDWARE.ESP,   '<H',  0xF34,       (None, None,                           ('Sensor',      '"Sensor18 {}".format($)')) ),
    'device_group_share_in':        (HARDWARE.ESP,   '<L',  0xFCC,       (None, None,                           ('Control',     '"DevGroupShare 0x{:08x},0x{:08x}".format(@["device_group_share_in"],@["device_group_share_out"])')) ),
    'device_group_share_out':       (HARDWARE.ESP,   '<L',  0xFD0,       (None, None,                           ('Control',      None)) ),
    'device_group_topic':           (HARDWARE.ESP,   '699s',(0x017,'SET_DEV_GROUP_NAME1'),
                                                                         ([4],  None,                           ('Control',     '"DevGroupName{} {}".format(#+1,$ if len($) else "\\"")')) ),
    'mqtt_grptopic':                (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_GRP_TOPIC'),
                                                                         (None, None,                           ('MQTT',        '"GroupTopic1 {}".format("\\"" if len($) == 0 else $)')) ),
    'mqtt_grptopic2':               (HARDWARE.ESP,   '699s',(0x017,'SET_MQTT_GRP_TOPIC2'),
                                                                         ([3],  None,                           ('MQTT',        '"GroupTopic{} {}".format(#+2, "\\"" if len($) == 0 else $)')) ),
    'my_gp':                        (HARDWARE.ESP82, 'B',   0x484,       ([17], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
    'my_gp_esp32':                  (HARDWARE.ESP32, 'B',   0x558,       ([40], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
    'user_template_esp32':          (HARDWARE.ESP32,{
        'base':                     (HARDWARE.ESP32, 'B',   0x71F,       (None, None,                           ('Management',  '"Template {{\\\"BASE\\\":{}}}".format($)')), ('$+1','$-1') ),
        'name':                     (HARDWARE.ESP32, '15s', 0x720,       (None, None,                           ('Management',  None)) ),
        'gpio':                     (HARDWARE.ESP32, 'B',   0x580,       ([36], None,                           ('Management',  '"Template {{\\\"GPIO\\\":{}}}".format(@["user_template_esp32"]["gpio"])')) ),
        'flag':                     (HARDWARE.ESP32,{
            'adc0':                 (HARDWARE.ESP32, 'B',  (0x5A4,4,0),  (None, None,                           ('Management',  '"Template {{\\\"FLAG\\\":{}}}".format($)')) ),
                                    },                      0x5A4,       (None, None,                           ('Management',  None)) ),
                                    },                      0x71F,       (None, None,                           ('Management',  None)) ),
                                    })
SETTING_8_2_0_3['user_template'][1].update ({
        'base':                     (HARDWARE.ESP82, 'B',   0x71F,       (None, None,                           ('Management',  '"Template {{\\\"BASE\\\":{}}}".format($)')), ('$+1','$-1') ),
        'name':                     (HARDWARE.ESP82, '15s', 0x720,       (None, None,                           ('Management',  None)) ),
        'gpio':                     (HARDWARE.ESP82, 'B',   0x72F,       ([13], None,                           ('Management',  '"Template {{\\\"GPIO\\\":{}}}".format(@["user_template"]["gpio"])')) ),
        'flag':                     (HARDWARE.ESP82, {
            'adc0':                 (HARDWARE.ESP82, 'B',  (0x73C,4,0),  (None, None,                           ('Management',  '"Template {{\\\"FLAG\\\":{}}}".format($)')) ),
                                    },                      0x73C,       (None, None,                           ('Management',  None)) ),
                                    })
SETTING_8_2_0_3['flag3'][1].update  ({
        'mqtt_buttons':             (HARDWARE.ESP,   '<L', (0x3A0,1,23), (None, None,                           ('SetOption',   '"SetOption73 {}".format($)')) ),
                                    })
SETTING_8_2_0_3['flag4'][1].update  ({
        'only_json_message':        (HARDWARE.ESP,   '<L', (0xEF8,1, 8), (None, None,                           ('SetOption',   '"SetOption90 {}".format($)')) ),
        'fade_at_startup':          (HARDWARE.ESP,   '<L', (0xEF8,1, 9), (None, None,                           ('SetOption',   '"SetOption91 {}".format($)')) ),
                                    })
SETTING_8_2_0_3['SensorBits1'][1].update ({
        'bh1750_resolution':        (HARDWARE.ESP,   'B',  (0x717,2, 4), (None, '0 <= $ <= 2',                  ('Sensor',      '"Sensor10 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_2_0_4 = copy.deepcopy(SETTING_8_2_0_3)
SETTING_8_2_0_4.update              ({
    'config_version':               (HARDWARE.ESP,   'B',   0xF36,       (None, '0 <= $ < len(HARDWARE.STR)',   (INTERNAL,      None)), (None,      False) ),
                                    })
SETTING_8_2_0_4.update              ({
    'param':                        (HARDWARE.ESP,   'B',   0x2FC,       ([18], None,                           ('SetOption',   '"SO{} {}".format(#+32,$)')) ),
                                    })
SETTING_8_2_0_4['flag'][1].update   ({
        'save_state':               (HARDWARE.ESP,   '<L', (0x010,1, 0), (None, None,                           ('SetOption',   '"SO0 {}".format($)')) ),
        'button_restrict':          (HARDWARE.ESP,   '<L', (0x010,1, 1), (None, None,                           ('SetOption',   '"SO1 {}".format($)')) ),
        'value_units':              (HARDWARE.ESP,   '<L', (0x010,1, 2), (None, None,                           ('SetOption',   '"SO2 {}".format($)')) ),
        'mqtt_enabled':             (HARDWARE.ESP,   '<L', (0x010,1, 3), (None, None,                           ('SetOption',   '"SO3 {}".format($)')) ),
        'mqtt_response':            (HARDWARE.ESP,   '<L', (0x010,1, 4), (None, None,                           ('SetOption',   '"SO4 {}".format($)')) ),
        'temperature_conversion':   (HARDWARE.ESP,   '<L', (0x010,1, 8), (None, None,                           ('SetOption',   '"SO8 {}".format($)')) ),
        'mqtt_offline':             (HARDWARE.ESP,   '<L', (0x010,1,10), (None, None,                           ('SetOption',   '"SO10 {}".format($)')) ),
        'button_swap':              (HARDWARE.ESP,   '<L', (0x010,1,11), (None, None,                           ('SetOption',   '"SO11 {}".format($)')) ),
        'stop_flash_rotate':        (HARDWARE.ESP,   '<L', (0x010,1,12), (None, None,                           ('SetOption',   '"SO12 {}".format($)')) ),
        'button_single':            (HARDWARE.ESP,   '<L', (0x010,1,13), (None, None,                           ('SetOption',   '"SO13 {}".format($)')) ),
        'pwm_control':              (HARDWARE.ESP,   '<L', (0x010,1,15), (None, None,                           ('SetOption',   '"SO15 {}".format($)')) ),
        'ws_clock_reverse':         (HARDWARE.ESP,   '<L', (0x010,1,16), (None, None,                           ('SetOption',   '"SO16 {}".format($)')) ),
        'decimal_text':             (HARDWARE.ESP,   '<L', (0x010,1,17), (None, None,                           ('SetOption',   '"SO17 {}".format($)')) ),
        'light_signal':             (HARDWARE.ESP,   '<L', (0x010,1,18), (None, None,                           ('SetOption',   '"SO18 {}".format($)')) ),
        'hass_discovery':           (HARDWARE.ESP,   '<L', (0x010,1,19), (None, None,                           ('SetOption',   '"SO19 {}".format($)')) ),
        'not_power_linked':         (HARDWARE.ESP,   '<L', (0x010,1,20), (None, None,                           ('SetOption',   '"SO20 {}".format($)')) ),
        'no_power_on_check':        (HARDWARE.ESP,   '<L', (0x010,1,21), (None, None,                           ('SetOption',   '"SO21 {}".format($)')) ),
        'mqtt_serial':              (HARDWARE.ESP,   '<L', (0x010,1,22), (None, None,                           ('SetOption',   '"SO22 {}".format($)')) ),
        'mqtt_serial_raw':          (HARDWARE.ESP,   '<L', (0x010,1,23), (None, None,                           ('SetOption',   '"SO23 {}".format($)')) ),
        'pressure_conversion':      (HARDWARE.ESP,   '<L', (0x010,1,24), (None, None,                           ('SetOption',   '"SO24 {}".format($)')) ),
        'device_index_enable':      (HARDWARE.ESP,   '<L', (0x010,1,26), (None, None,                           ('SetOption',   '"SO26 {}".format($)')) ),
        'rf_receive_decimal':       (HARDWARE.ESP,   '<L', (0x010,1,28), (None, None,                           ('SetOption' ,  '"SO28 {}".format($)')) ),
        'ir_receive_decimal':       (HARDWARE.ESP,   '<L', (0x010,1,29), (None, None,                           ('SetOption',   '"SO29 {}".format($)')) ),
        'hass_light':               (HARDWARE.ESP,   '<L', (0x010,1,30), (None, None,                           ('SetOption',   '"SO30 {}".format($)')) ),
        'global_state':             (HARDWARE.ESP,   '<L', (0x010,1,31), (None, None,                           ('SetOption',   '"SO31 {}".format($)')) ),
                                    })
SETTING_8_2_0_4['flag3'][1].update  ({
        'user_esp8285_enable':      (HARDWARE.ESP,   '<L', (0x3A0,1, 1), (None, None,                           ('SetOption',   '"SO51 {}".format($)')) ),
        'time_append_timezone':     (HARDWARE.ESP,   '<L', (0x3A0,1, 2), (None, None,                           ('SetOption',   '"SO52 {}".format($)')) ),
        'gui_hostname_ip':          (HARDWARE.ESP,   '<L', (0x3A0,1, 3), (None, None,                           ('SetOption',   '"SO53 {}".format($)')) ),
        'tuya_apply_o20':           (HARDWARE.ESP,   '<L', (0x3A0,1, 4), (None, None,                           ('SetOption',   '"SO54 {}".format($)')) ),
        'mdns_enabled':             (HARDWARE.ESP,   '<L', (0x3A0,1, 5), (None, None,                           ('SetOption',   '"SO55 {}".format($)')) ),
        'use_wifi_scan':            (HARDWARE.ESP,   '<L', (0x3A0,1, 6), (None, None,                           ('SetOption',   '"SO56 {}".format($)')) ),
        'use_wifi_rescan':          (HARDWARE.ESP,   '<L', (0x3A0,1, 7), (None, None,                           ('SetOption',   '"SO57 {}".format($)')) ),
        'receive_raw':          	(HARDWARE.ESP,   '<L', (0x3A0,1, 8), (None, None,                           ('SetOption',   '"SO58 {}".format($)')) ),
        'hass_tele_on_power':       (HARDWARE.ESP,   '<L', (0x3A0,1, 9), (None, None,                           ('SetOption',   '"SO59 {}".format($)')) ),
        'sleep_normal':             (HARDWARE.ESP,   '<L', (0x3A0,1,10), (None, None,                           ('SetOption',   '"SO60 {}".format($)')) ),
        'button_switch_force_local':(HARDWARE.ESP,   '<L', (0x3A0,1,11), (None, None,                           ('SetOption',   '"SO61 {}".format($)')) ),
        'no_hold_retain':           (HARDWARE.ESP,   '<L', (0x3A0,1,12), (None, None,                           ('SetOption',   '"SO62 {}".format($)')) ),
        'no_power_feedback':        (HARDWARE.ESP,   '<L', (0x3A0,1,13), (None, None,                           ('SetOption',   '"SO63 {}".format($)')) ),
        'use_underscore':           (HARDWARE.ESP,   '<L', (0x3A0,1,14), (None, None,                           ('SetOption',   '"SO64 {}".format($)')) ),
        'fast_power_cycle_disable': (HARDWARE.ESP,   '<L', (0x3A0,1,15), (None, None,                           ('SetOption',   '"SO65 {}".format($)')) ),
        'tuya_serial_mqtt_publish': (HARDWARE.ESP,   '<L', (0x3A0,1,16), (None, None,                           ('SetOption',   '"SO66 {}".format($)')) ),
        'buzzer_enable':            (HARDWARE.ESP,   '<L', (0x3A0,1,17), (None, None,                           ('SetOption',   '"SO67 {}".format($)')) ),
        'pwm_multi_channels':       (HARDWARE.ESP,   '<L', (0x3A0,1,18), (None, None,                           ('SetOption',   '"SO68 {}".format($)')) ),
        'tuya_dimmer_min_limit':    (HARDWARE.ESP,   '<L', (0x3A0,1,19), (None, None,                           ('SetOption',   '"SO69 {}".format($)')) ),
        'dds2382_model':            (HARDWARE.ESP,   '<L', (0x3A0,1,21), (None, None,                           ('SetOption',   '"SO71 {}".format($)')) ),
        'hardware_energy_total':    (HARDWARE.ESP,   '<L', (0x3A0,1,22), (None, None,                           ('SetOption',   '"SO72 {}".format($)')) ),
        'mqtt_buttons':             (HARDWARE.ESP,   '<L', (0x3A0,1,23), (None, None,                           ('SetOption',   '"SO73 {}".format($)')) ),
        'ds18x20_internal_pullup':  (HARDWARE.ESP,   '<L', (0x3A0,1,24), (None, None,                           ('SetOption',   '"SO74 {}".format($)')) ),
        'grouptopic_mode':          (HARDWARE.ESP,   '<L', (0x3A0,1,25), (None, None,                           ('SetOption',   '"SO75 {}".format($)')) ),
        'bootcount_update':         (HARDWARE.ESP,   '<L', (0x3A0,1,26), (None, None,                           ('SetOption',   '"SO76 {}".format($)')) ),
        'slider_dimmer_stay_on':    (HARDWARE.ESP,   '<L', (0x3A0,1,27), (None, None,                           ('SetOption',   '"SO77 {}".format($)')) ),
        'compatibility_check':      (HARDWARE.ESP,   '<L', (0x3A0,1,28), (None, None,                           ('SetOption',   '"SO78 {}".format($)')) ),
        'counter_reset_on_tele':    (HARDWARE.ESP,   '<L', (0x3A0,1,29), (None, None,                           ('SetOption',   '"SO79 {}".format($)')) ),
        'shutter_mode':             (HARDWARE.ESP,   '<L', (0x3A0,1,30), (None, None,                           ('SetOption',   '"SO80 {}".format($)')) ),
        'pcf8574_ports_inverted':   (HARDWARE.ESP,   '<L', (0x3A0,1,31), (None, None,                           ('SetOption',   '"SO81 {}".format($)')) ),
                                    })
SETTING_8_2_0_4['flag4'][1].update  ({
        'alexa_ct_range':           (HARDWARE.ESP,   '<L', (0xEF8,1, 0), (None, None,                           ('SetOption',   '"SO82 {}".format($)')) ),
        'zigbee_use_names':         (HARDWARE.ESP,   '<L', (0xEF8,1, 1), (None, None,                           ('SetOption',   '"SO83 {}".format($)')) ),
        'awsiot_shadow':            (HARDWARE.ESP,   '<L', (0xEF8,1, 2), (None, None,                           ('SetOption',   '"SO84 {}".format($)')) ),
        'device_groups_enabled':    (HARDWARE.ESP,   '<L', (0xEF8,1, 3), (None, None,                           ('SetOption',   '"SO85 {}".format($)')) ),
        'led_timeout':              (HARDWARE.ESP,   '<L', (0xEF8,1, 4), (None, None,                           ('SetOption',   '"SO86 {}".format($)')) ),
        'powered_off_led':          (HARDWARE.ESP,   '<L', (0xEF8,1, 5), (None, None,                           ('SetOption',   '"SO87 {}".format($)')) ),
        'remote_device_mode':       (HARDWARE.ESP,   '<L', (0xEF8,1, 6), (None, None,                           ('SetOption',   '"SO88 {}".format($)')) ),
        'zigbee_distinct_topics':   (HARDWARE.ESP,   '<L', (0xEF8,1, 7), (None, None,                           ('SetOption',   '"SO89 {}".format($)')) ),
        'only_json_message':        (HARDWARE.ESP,   '<L', (0xEF8,1, 8), (None, None,                           ('SetOption',   '"SO90 {}".format($)')) ),
        'fade_at_startup':          (HARDWARE.ESP,   '<L', (0xEF8,1, 9), (None, None,                           ('SetOption',   '"SO91 {}".format($)')) ),
        'pwm_ct_mode':              (HARDWARE.ESP,   '<L', (0xEF8,1,10), (None, None,                           ('SetOption',   '"SO92 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_2_0_6 = copy.deepcopy(SETTING_8_2_0_4)
SETTING_8_2_0_6.pop('tariff1_0', None)
SETTING_8_2_0_6.pop('tariff1_1', None)
SETTING_8_2_0_6.pop('tariff2_0', None)
SETTING_8_2_0_6.pop('tariff2_1', None)
SETTING_8_2_0_6.update              ({
    'tariff':                       (HARDWARE.ESP,   '<H',  0xE30,       ([4,2],None,                           ('Power',       'list("Tariff{} {:02d}:{:02d},{:02d}:{:02d}".format(i+1, @["tariff"][i][0]//60, @["tariff"][i][0]%60, @["tariff"][i][1]//60, @["tariff"][i][1]%60) for i in range(0, len(@["tariff"][0])))')) ),
    'my_gp_esp32':                  (HARDWARE.ESP32, '<H',  0x3AC,       ([40], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
    'user_template_esp32':          (HARDWARE.ESP32,{
        'base':                     (HARDWARE.ESP32, '<H',  0x71F,       (None, None,                           ('Management',  '"Template {{\\\"BASE\\\":{}}}".format($)')), ('$+1','$-1') ),
        'name':                     (HARDWARE.ESP32, '15s', 0x720,       (None, None,                           ('Management',  None)) ),
        'gpio':                     (HARDWARE.ESP32, '<H',  0x3FC,       ([36], None,                           ('Management',  '"Template {{\\\"GPIO\\\":{}}}".format(@["user_template_esp32"]["gpio"])')) ),
        'flag':                     (HARDWARE.ESP32, '<H',  0x444,       (None, None,                           ('Management',  '"Template {{\\\"FLAG\\\":{}}}".format($)')) ),
                                    },                      0x71F,       (None, None,                           ('Management',  None)) ),
    'webcam_config':                (HARDWARE.ESP32, {
        'stream':                   (HARDWARE.ESP32, '<L', (0x44C,1, 0), (None, None,                           ('Control',     '"WCStream {}".format($)')) ),
        'mirror':                   (HARDWARE.ESP32, '<L', (0x44C,1, 1), (None, None,                           ('Control',     '"WCMirror {}".format($)')) ),
        'flip':                     (HARDWARE.ESP32, '<L', (0x44C,1, 2), (None, None,                           ('Control',     '"WCFlip {}".format($)')) ),
        'contrast':                 (HARDWARE.ESP32, '<l', (0x44C,3,18), (None, '0 <= $ <= 4',                  ('Control',     '"WCContrast {}".format($-2)')) ),
        'brightness':               (HARDWARE.ESP32, '<l', (0x44C,3,22), (None, '0 <= $ <= 4',                  ('Control',     '"WCBrightness {}".format($-2)')) ),
        'saturation':               (HARDWARE.ESP32, '<l', (0x44C,3,25), (None, '0 <= $ <= 4',                  ('Control',     '"WCSaturation {}".format($-2)')) ),
        'resolution':               (HARDWARE.ESP32, '<l', (0x44C,4,28), (None, '0 <= $ <= 10',                 ('Control',     '"WCResolution {}".format($)')) ),
                                    },                      0x44C,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
    'windmeter_pulses_x_rot':       (HARDWARE.ESP,   'B',   0xF37,       (None, None,                           ('Sensor',      '"Sensor68 2,{}".format($)')) ),
    'windmeter_radius':             (HARDWARE.ESP,   '<H',  0xF38,       (None, None,                           ('Sensor',      '"Sensor68 1,{}".format($)')) ),
    'windmeter_pulse_debounce':     (HARDWARE.ESP,   '<H',  0xF3A,       (None, None,                           ('Sensor',      '"Sensor68 3,{}".format($)')) ),
    'windmeter_speed_factor':       (HARDWARE.ESP,   '<h',  0xF3C,       (None, None,                           ('Sensor',      '"Sensor68 4,{}".format(float($)/1000)')) ),
    'windmeter_tele_pchange':       (HARDWARE.ESP,   'B',   0xF3E,       (None, None,                           ('Sensor',      '"Sensor68 5,{}".format($)')) ),
    'ot_hot_water_setpoint':        (HARDWARE.ESP,   'B',   0xE8C,       (None, None,                           ('Sensor',      '"Backlog OT_TWater {};OT_Save_Setpoints".format($)')) ),
    'ot_boiler_setpoint':           (HARDWARE.ESP,   'B',   0xE8D,       (None, None,                           ('Sensor',      '"Backlog OT_TBoiler {};OT_Save_Setpoints".format($)')) ),
    'ot_flags':                     (HARDWARE.ESP,   'B',   0xE8E,       (None, None,                           ('Sensor',      '"OT_Flags {}".format(",".join(["CHOD","DHW","CH","COOL","OTC","CH2"][i] for i in range(0,6) if $ & 1<<i))')) ),
    'rules':                        (HARDWARE.ESP,   '512s',0x800,       ([3],  None,                           ('Rules',       '"Rule{} \\"".format(#+1) if len($) == 0 else list("Rule{} {}{}".format(#+1, "+" if i else "", s) for i, s in enumerate(textwrap.wrap($, width=512))) if ARGS.cmnduseruleconcat else "Rule{} {}".format(#+1,$)')) ),
                                    })
SETTING_8_2_0_6['flag4'][1].update  ({
        'compress_rules_cpu':       (HARDWARE.ESP,   '<L', (0xEF8,1,11), (None, None,                           ('SetOption',   '"SO93 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_3_1_0 = copy.deepcopy(SETTING_8_2_0_6)
# ======================================================================
SETTING_8_3_1_1 = copy.deepcopy(SETTING_8_3_1_0)
SETTING_8_3_1_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].pop()  # SET_MAX
SETTING_8_3_1_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_DEVICENAME'])
SETTING_8_3_1_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MAX'])
SETTING_8_3_1_1[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP82): copy.deepcopy(SETTING_8_3_1_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_3_1_1[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP32): copy.deepcopy(SETTING_8_3_1_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_3_1_1.update              ({
    'devicename':                   (HARDWARE.ESP,   '699s',(0x017,'SET_DEVICENAME'),
                                                                         (None, None,                           ('Management',  '"DeviceName {}".format("\\"" if len($) == 0 else $)')) ),
                                    })
# ======================================================================
SETTING_8_3_1_2 = copy.deepcopy(SETTING_8_3_1_1)
SETTING_8_3_1_2.update              ({
    'ledpwm_mask':                  (HARDWARE.ESP,   'B',   0xE8F,       (None, None,                           ('Control',     'list("LedPwmMode{} {}".format(i+1, 1 if ($ & (1<<i)) else 0) for i in range(0, 4))')) ),
    'ledpwm_on':                    (HARDWARE.ESP,   'B',   0xF3F,       (None, None,                           ('Control',     '"LedPwmOn {}".format($)')) ),
    'ledpwm_off':                   (HARDWARE.ESP,   'B',   0xF40,       (None, None,                           ('Control',     '"LedPwmOff {}".format($)')) ),
                                    })
SETTING_8_3_1_2['flag2'][1].update  ({
        'time_format':              (HARDWARE.ESP,   '<L', (0x5BC,2, 4), (None, '0 <= $ <= 3',                  ('Management', '"Time {}".format($+1)')) ),
                                    })
SETTING_8_3_1_2['SensorBits1'][1].pop('bh1750_resolution',None)
SETTING_8_3_1_2['SensorBits1'][1].update ({
        'bh1750_2_resolution':      (HARDWARE.ESP,   'B',  (0x717,2, 2), (None, '0 <= $ <= 2',                  ('Sensor',      '"Bh1750Resolution2 {}".format($)')) ),
        'bh1750_1_resolution':      (HARDWARE.ESP,   'B',  (0x717,2, 4), (None, '0 <= $ <= 2',                  ('Sensor',      '"Bh1750Resolution1 {}".format($)')) ),
                                    })
SETTING_8_3_1_2['flag4'][1].update  ({
        'max6675':                  (HARDWARE.ESP,   '<L', (0xEF8,1,12), (None, None,                           ('SetOption',   '"SO94 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_3_1_3 = copy.deepcopy(SETTING_8_3_1_2)
SETTING_8_3_1_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].pop()  # SET_MAX
SETTING_8_3_1_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_TELEGRAM_TOKEN', 'SET_TELEGRAM_CHATID'])
SETTING_8_3_1_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MAX'])
SETTING_8_3_1_3[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP82): copy.deepcopy(SETTING_8_3_1_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_3_1_3[SETTINGVAR].update({HARDWARE.hstr(HARDWARE.ESP32): copy.deepcopy(SETTING_8_3_1_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)])})
SETTING_8_3_1_3.update              ({
    'telegram_token':               (HARDWARE.ESP,   '699s',(0x017,'SET_TELEGRAM_TOKEN'),
                                                                         (None, None,                           ('Telegram',    '"TmToken {}".format("\\"" if len($) == 0 else $)')) ),
    'telegram_chatid':              (HARDWARE.ESP,   '699s',(0x017,'SET_TELEGRAM_CHATID'),
                                                                         (None, None,                           ('Telegram',    '"TmChatId {}".format("\\"" if len($) == 0 else $)')) ),
                                    })

# ======================================================================
SETTING_8_3_1_4 = copy.deepcopy(SETTING_8_3_1_3)
SETTING_8_3_1_4.update              ({
    'tcp_baudrate':                 (HARDWARE.ESP,   'B',   0xF41,       (None, None,                           ('Serial',      '"TCPBaudrate {}".format($)')), ('$ * 1200','$ // 1200') ),
                                    })
SETTING_8_3_1_4['flag4'][1].update  ({
        'network_wifi':             (HARDWARE.ESP,   '<L', (0xEF8,1,13), (None, None,                           ('Wifi',        '"Wifi {}".format($)')) ),
        'network_ethernet':         (HARDWARE.ESP32, '<L', (0xEF8,1,14), (None, None,                           ('Wifi',        '"Ethernet {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_3_1_5 = copy.deepcopy(SETTING_8_3_1_4)
SETTING_8_3_1_5.update              ({
    'eth_type':                     (HARDWARE.ESP32, 'B',   0x446,       (None, '0 <= $ <= 1',                  ('Wifi',        '"EthType {}".format($)')) ),
    'eth_clk_mode':                 (HARDWARE.ESP32, 'B',   0x447,       (None, '0 <= $ <= 3',                  ('Wifi',        '"EthClockMode {}".format($)')) ),
    'eth_address':                  (HARDWARE.ESP32, 'B',   0x450,       (None, '0 <= $ <= 31',                 ('Wifi',        '"EthAddress {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_3_1_6 = copy.deepcopy(SETTING_8_3_1_5)
SETTING_8_3_1_6.update              ({
    'fallback_module':              (HARDWARE.ESP,   'B',   0xF42,       (None, None,                           ('Management',  '"Module2 {}".format($)')) ),
    'zb_channel':                   (HARDWARE.ESP,   'B',   0xF32,       (None, '11 <= $ <= 26',                ('Zigbee',      None)) ),
    'zb_txradio_dbm':               (HARDWARE.ESP,   'B',   0xF33,       (None, None,                           ('Zigbee',      '"ZbConfig {{\\\"Channel\\\":{},\\\"PanID\\\":\\\"0x{:04X}\\\",\\\"ExtPanID\\\":\\\"0x{:016X}\\\",\\\"KeyL\\\":\\\"0x{:016X}\\\",\\\"KeyH\\\":\\\"0x{:016X}\\\",\\\"TxRadio\\\":{}}}".format(@["zb_channel"], @["zb_pan_id"], @["zb_ext_panid"], @["zb_precfgkey_l"], @["zb_precfgkey_h"],@["zb_txradio_dbm"])')) ),
                                    })
SETTING_8_3_1_6['flag4'][1].update  ({
        'tuyamcu_baudrate':         (HARDWARE.ESP,   '<L', (0xEF8,1,15), (None, None,                           ('SetOption',   '"SO97 {}".format($)')) ),
        'rotary_uses_rules':        (HARDWARE.ESP,   '<L', (0xEF8,1,16), (None, None,                           ('SetOption',   '"SO98 {}".format($)')) ),
        'zerocross_dimmer':         (HARDWARE.ESP,   '<L', (0xEF8,1,17), (None, None,                           ('SetOption',   '"SO99 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_3_1_7 = copy.deepcopy(SETTING_8_3_1_6)
SETTING_8_3_1_7.update              ({
    'rules':                        (HARDWARE.ESP,   '512s',0x800,       ([3],  None,                           ('Rules',       '"Rule{} \\"".format(#+1) if len($) == 0 else list("Rule{} {}{}".format(#+1, "+" if i else "", s) for i, s in enumerate(textwrap.wrap($, width=512))) if ARGS.cmnduseruleconcat else "Rule{} {}".format(#+1,$)')), (rulesread, ruleswrite)),
    'scripting_used':               (HARDWARE.ESP,   'B',  (0x4A0,1,7),  (None, None,                           ('Rules',       None)), (False, False)),
    'scripting_compressed':         (HARDWARE.ESP,   'B',  (0x4A0,1,6),  (None, None,                           ('Rules',       None)), (False, False)),
    'script_enabled':               (HARDWARE.ESP,   'B',  (0x49F,1,0),  (None, None,                           ('Rules',       '"Script {}".format($)')), isscript),
    'script':                       (HARDWARE.ESP,  '1536s',0x800,       (None, None,                           ('Rules',       None)), (scriptread, scriptwrite)),
                                    })
SETTING_8_3_1_7['flag4'][1].update  ({
        'remove_zbreceived':        (HARDWARE.ESP,   '<L', (0xEF8,1,18), (None, None,                           ('SetOption',   '"SO100 {}".format($)')) ),
        'zb_index_ep':              (HARDWARE.ESP,   '<L', (0xEF8,1,19), (None, None,                           ('SetOption',   '"SO101 {}".format($)')) ),
                                    })
SETTING_8_3_1_7['timer'][1].update  ({
        'time':                     (HARDWARE.ESP,   '<L', (0x670,11, 0),(None, '0 <= $ < 1440',                ('Timer',       '"Timer{} {{\\\"Enable\\\":{arm},\\\"Mode\\\":{mode},\\\"Time\\\":\\\"{tsign}{time}\\\",\\\"Window\\\":{window},\\\"Days\\\":\\\"{days}\\\",\\\"Repeat\\\":{repeat},\\\"Output\\\":{device},\\\"Action\\\":{power}}}".format(#+1, arm=@["timer"][#]["arm"],mode=@["timer"][#]["mode"],tsign="-" if @["timer"][#]["mode"]>0 and @["timer"][#]["time"]>(12*60) else "",time=time.strftime("%H:%M",time.gmtime((@["timer"][#]["time"] if @["timer"][#]["mode"]==0 else @["timer"][#]["time"] if @["timer"][#]["time"]<=(12*60) else @["timer"][#]["time"]-(12*60))*60)),window=@["timer"][#]["window"],repeat=@["timer"][#]["repeat"],days="{:07b}".format(@["timer"][#]["days"])[::-1],device=@["timer"][#]["device"]+1,power=@["timer"][#]["power"] )')), '"0x{:03x}".format($)' ),
                                    })
# ======================================================================
SETTING_8_4_0_0 = copy.deepcopy(SETTING_8_3_1_7)
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].pop()  # SET_MAX
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].pop()  # SET_MAX
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].pop()  # SET_MAX
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_ADC_PARAM1'])
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_ADC_PARAM1'])
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_ADC_PARAM1', 'SET_ADC_PARAM2', 'SET_ADC_PARAM3', 'SET_ADC_PARAM4', 'SET_ADC_PARAM5', 'SET_ADC_PARAM6', 'SET_ADC_PARAM7', 'SET_ADC_PARAM8'])
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MAX'])
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_MAX'])
SETTING_8_4_0_0[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_MAX'])
SETTING_8_4_0_0.update              ({
    'adc_param':                    (HARDWARE.ESP32, '699s',(0x017,'SET_ADC_PARAM1'),
                                                                         ([8],  None,                           ('Management',  None)) ),
                                    })
# ======================================================================
SETTING_8_4_0_1 = copy.deepcopy(SETTING_8_4_0_0)
SETTING_8_4_0_1['flag4'][1].update  ({
        'multiple_device_groups':   (HARDWARE.ESP,   '<L', (0xEF8,1, 6), (None, None,                           ('SetOption',   '"SO88 {}".format($)')) ),
        'teleinfo_baudrate':        (HARDWARE.ESP,   '<L', (0xEF8,1,20), (None, None,                           ('SetOption',   '"SO102 {}".format($)')) ),
        'mqtt_tls':                 (HARDWARE.ESP,   '<L', (0xEF8,1,21), (None, None,                           ('SetOption',   '"SO103 {}".format($)')) ),
        'mqtt_no_retain':           (HARDWARE.ESP,   '<L', (0xEF8,1,22), (None, None,                           ('SetOption',   '"SO104 {}".format($)')) ),
                                    })
SETTING_8_4_0_1['flag4'][1].pop('remote_device_mode',None)
# ======================================================================
SETTING_8_4_0_2 = copy.deepcopy(SETTING_8_4_0_1)
SETTING_8_4_0_2.update              ({
    'flag5':                        (HARDWARE.ESP,   '<L',  0xEB4,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
                                    })
SETTING_8_4_0_2['flag4'][1].update  ({
        'white_blend_mode':         (HARDWARE.ESP,   '<L', (0xEF8,1,23), (None, None,                           ('SetOption',   '"SO105 {}".format($)')) ),
        'virtual_ct':               (HARDWARE.ESP,   '<L', (0xEF8,1,24), (None, None,                           ('SetOption',   '"SO106 {}".format($)')) ),
        'virtual_ct_cw':            (HARDWARE.ESP,   '<L', (0xEF8,1,25), (None, None,                           ('SetOption',   '"SO107 {}".format($)')) ),
        'teleinfo_rawdata':         (HARDWARE.ESP,   '<L', (0xEF8,1,26), (None, None,                           ('SetOption',   '"SO108 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_4_0_3 = copy.deepcopy(SETTING_8_4_0_2)
SETTING_8_4_0_3.update              ({
    'energy_power_delta':           (HARDWARE.ESP,   '<H',  0xF44,       ([3], '0 <= $ < 32000',                ('Power',       '"PowerDelta{} {}".format(#+1, $)')) ),
    'flag5':                        (HARDWARE.ESP,   '<L',  0xFB4,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
                                    })
SETTING_8_4_0_3['flag4'][1].update  ({
        'alexa_gen_1':              (HARDWARE.ESP,   '<L', (0xEF8,1,27), (None, None,                           ('SetOption',   '"SO109 {}".format($)')) ),
                                    })
SETTING_8_4_0_3['flag4'][1].update  ({
        'suppress_irq_no_Event':    (HARDWARE.ESP,   'B',  (0xF15,1, 4), (None, None,                           ('Sensor',      '"AS3935NoIrqEvent {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_5_0_1 = copy.deepcopy(SETTING_8_4_0_3)
SETTING_8_5_0_1.update              ({
    'shutter_mode':                 (HARDWARE.ESP,   'B',  0xF43,       (None, '0 <= $ <= 7',                   ('Shutter',     '"ShutterMode {}".format($)')) ),
    'shutter_pwmrange':             (HARDWARE.ESP,   '<H', 0xF4A,       ([2,4],'1 <= $ <= 1023',                ('Shutter',     'list("ShutterPWMRange{} {}".format(k+1, list(" ".join(str(@["shutter_pwmrange"][i][j]) for i in range(0, len(@["shutter_pwmrange"]))) for j in range(0, len(@["shutter_pwmrange"][0])))[k]) for k in range(0,len(@["shutter_pwmrange"][0])))')) ),
    'hass_new_discovery':           (HARDWARE.ESP,   '<H', 0xE98,       (None, None,                            (INTERNAL,      None)) ),
    'tuyamcu_topic':                (HARDWARE.ESP,   'B',  0x33F,       (None, '0 <= $ <= 1',                   ('Serial',      None)) ),
                                    })
SETTING_8_5_0_1['flag4'][1].update  ({
        'zb_disable_autobind':      (HARDWARE.ESP,   '<L', (0xEF8,1,28), (None, None,                           ('SetOption',   '"SO110 {}".format($)')) ),
        'buzzer_freq_mode':         (HARDWARE.ESP,   '<L', (0xEF8,1,29), (None, None,                           ('SetOption',   '"SO111 {}".format($)')) ),
        'zb_topic_fname':           (HARDWARE.ESP,   '<L', (0xEF8,1,30), (None, None,                           ('SetOption',   '"SO112 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_8_5_1_0 = copy.deepcopy(SETTING_8_5_0_1)
# ======================================================================
SETTING_9_0_0_1 = copy.deepcopy(SETTING_8_5_1_0)
SETTING_9_0_0_1.pop('my_adc0', None)
SETTING_9_0_0_1.pop('bri_min', None)
SETTING_9_0_0_1.update              ({
    'gpio16_converted':             (HARDWARE.ESP82, '<H',  0x3D0,       (None, None,                           ('Management',  None)) ),
    'my_gp':                        (HARDWARE.ESP82, '<H',  0x3AC,       ([18], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
    'templatename':                 (HARDWARE.ESP,   '699s',(0x017,'SET_TEMPLATE_NAME'),
                                                                         (None, None,                           ('Management',  None)) ),
    'user_template':                (HARDWARE.ESP82,{
        'base':                     (HARDWARE.ESP82, 'B',   0x71F,       (None, None,                           ('Management',  '"Template {{\\\"NAME\\\":\\\"{}\\\",\\\"GPIO\\\":{},\\\"FLAG\\\":{},\\\"BASE\\\":{}}}".format(@["templatename"],@["user_template"]["gpio"],@["user_template"]["flag"],$)')), ('$+1','$-1') ),
        'name':                     (HARDWARE.ESP82, '15s', 0x720,       (None, None,                           ('Management',  None)) ),
        'gpio':                     (HARDWARE.ESP82, '<H',  0x3FC,       ([14], None,                           ('Management',  None)) ),
        'flag':                     (HARDWARE.ESP82, '<H',  0x3FC+(2*14),(None, None,                           ('Management',  None)) ),
                                    },                      0x71F,       (None, None,                           ('Management',  None)) ),
    'my_gp_esp32':                  (HARDWARE.ESP32, '<H',  0x3AC,       ([40], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
    'user_template_esp32':          (HARDWARE.ESP32,{
        'base':                     (HARDWARE.ESP32, 'B',   0x71F,       (None, None,                           ('Management',  '"Template {{\\\"NAME\\\":\\\"{}\\\",\\\"GPIO\\\":{},\\\"FLAG\\\":{},\\\"BASE\\\":{}}}".format(@["templatename"],@["user_template_esp32"]["gpio"],@["user_template_esp32"]["flag"],$)')), ('$+1','$-1') ),
        'name':                     (HARDWARE.ESP32, '15s', 0x720,       (None, None,                           ('Management',  None)) ),
        'gpio':                     (HARDWARE.ESP32, '<H',  0x3FC,       ([36], None,                           ('Management',  None)), ('1 if $==65504 else $','65504 if $==1 else $')),
        'flag':                     (HARDWARE.ESP32, '<H',  0x3FC+(2*36),(None, None,                           ('Management',  None)) ),
                                    },                      0x71F,       (None, None,                           ('Management',  None)) ),
    'pwm_dimmer_cfg':               (HARDWARE.ESP, {
        'pwm_count':                (HARDWARE.ESP,   '<L', (0xF05,3, 0), (None, '0 <= $ <= 4',                  ('Light',       '"PWMDimmerPWMs {}".format($+1)')) ),
                                    },                      0xF05,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
# ======================================================================
SETTING_9_0_0_2 = copy.deepcopy(SETTING_9_0_0_1)
SETTING_9_0_0_2.update              ({
    'zb_txradio_dbm':               (HARDWARE.ESP,   'b',   0xF33,       (None, None,                           ('Zigbee',      '"ZbConfig {{\\\"Channel\\\":{},\\\"PanID\\\":\\\"0x{:04X}\\\",\\\"ExtPanID\\\":\\\"0x{:016X}\\\",\\\"KeyL\\\":\\\"0x{:016X}\\\",\\\"KeyH\\\":\\\"0x{:016X}\\\",\\\"TxRadio\\\":{}}}".format(@["zb_channel"], @["zb_pan_id"], @["zb_ext_panid"], @["zb_precfgkey_l"], @["zb_precfgkey_h"],@["zb_txradio_dbm"])')) ),
    'adc_param_type':               (HARDWARE.ESP,   'B',   0xEF7,       (None, '2 <= $ <= 8',                  ('Sensor',      None)) ),
    'switchmode':                   (HARDWARE.ESP,   'B',   0x3A4,       ([8],  '0 <= $ <= 15',                 ('Control',     '"SwitchMode{} {}".format(#+1,$)')) ),
                                    })
SETTING_9_0_0_2['flag4'][1].update  ({
        'rotary_poweron_dimlow':    (HARDWARE.ESP,   '<L', (0xEF8,1,31), (None, None,                           ('SetOption',   '"SO113 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_0_0_3 = copy.deepcopy(SETTING_9_0_0_2)
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].pop()    # SET_MAX
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].pop()  # SET_MAX
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].pop()  # SET_MAX
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_SWITCH_TXT1', 'SET_SWITCH_TXT2', 'SET_SWITCH_TXT3', 'SET_SWITCH_TXT4', 'SET_SWITCH_TXT5', 'SET_SWITCH_TXT6', 'SET_SWITCH_TXT7', 'SET_SWITCH_TXT8'])
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_SWITCH_TXT1', 'SET_SWITCH_TXT2', 'SET_SWITCH_TXT3', 'SET_SWITCH_TXT4', 'SET_SWITCH_TXT5', 'SET_SWITCH_TXT6', 'SET_SWITCH_TXT7', 'SET_SWITCH_TXT8'])
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_SWITCH_TXT1', 'SET_SWITCH_TXT2', 'SET_SWITCH_TXT3', 'SET_SWITCH_TXT4', 'SET_SWITCH_TXT5', 'SET_SWITCH_TXT6', 'SET_SWITCH_TXT7', 'SET_SWITCH_TXT8'])
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_SHD_PARAM'])
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_SHD_PARAM'])
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_SHD_PARAM'])
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MAX'])
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_MAX'])
SETTING_9_0_0_3[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_MAX'])
SETTING_9_0_0_3.update              ({
    'switchtext':                   (HARDWARE.ESP, '699s',(0x017,'SET_SWITCH_TXT1'),
                                                                         ([8],  None,                           ('Management',  '"SwitchText{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
    'shelly_dimmer':                (HARDWARE.ESP, '699s',(0x017,'SET_SHD_PARAM'),
                                                                         (None,  None,                          ('Light',       None)) ),
    'dimmer_step':                  (HARDWARE.ESP,   'B',   0xF5A,       (None, '1 <= $ <= 50',                 ('Light',       '"DimmerStep {}".format($)')) ),
    'flag5':                        (HARDWARE.ESP, {
        'mqtt_switches':            (HARDWARE.ESP,   '<L', (0xFB4,1, 0), (None, None,                           ('SetOption',   '"SO114 {}".format($)')) ),
                                    },                      0xFB4,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
# ======================================================================
SETTING_9_1_0_0 = copy.deepcopy(SETTING_9_0_0_3)
# ======================================================================
SETTING_9_1_0_1 = copy.deepcopy(SETTING_9_1_0_0)
SETTING_9_1_0_1.update              ({
    'shd_leading_edge':             (HARDWARE.ESP,   'B',   0xF5B,       (None, '0 <= $ <= 1',                  ('Light',       '"ShdLeadingEdge {}".format($)')) ),
    'shd_warmup_brightness':        (HARDWARE.ESP,   '<H',  0xF5C,       (None, '10 <= $ <= 100',               ('Light',       '"ShdWarmupBrightness {}".format($)')) ),
    'shd_warmup_time':              (HARDWARE.ESP,   'B',   0xF5E,       (None, '20 <= $ <= 200',               ('Light',       '"ShdWarmupTime {}".format($)')) ),
    'rf_protocol_mask':             (HARDWARE.ESP,   '<Q',  0xFA8,       (None, None,                           ('Rf',          '"RfProtocol {}".format($)')), '"0x{:016x}".format($)' ),
                                    })
SETTING_9_1_0_1['flag5'][1].update  ({
        'mi32_enable':              (HARDWARE.ESP,   '<L', (0xFB4,1, 1), (None, None,                           ('SetOption',   '"SO115 {}".format($)')) ),
        'zb_disable_autoquery':     (HARDWARE.ESP,   '<L', (0xFB4,1, 2), (None, None,                           ('SetOption',   '"SO116 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_1_0_2 = copy.deepcopy(SETTING_9_1_0_1)
SETTING_9_1_0_2['flag5'][1].update  ({
        'fade_fixed_duration':      (HARDWARE.ESP,   '<L', (0xFB4,1, 3), (None, None,                           ('SetOption',   '"SO117 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_2_0_2 = copy.deepcopy(SETTING_9_1_0_2)
SETTING_9_2_0_2['flag5'][1].update  ({
        'zb_received_as_subtopic':  (HARDWARE.ESP,   '<L', (0xFB4,1, 4), (None, None,                           ('SetOption',   '"SO118 {}".format($)')) ),
        'zb_omit_json_addr':        (HARDWARE.ESP,   '<L', (0xFB4,1, 5), (None, None,                           ('SetOption',   '"SO119 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_2_0_3 = copy.deepcopy(SETTING_9_2_0_2)
SETTING_9_2_0_3.update              ({
    'energy_kWhtoday':              (HARDWARE.ESP,   '<L',  0x370,       (None, '0 <= $ <= 4294967295',         ('Power',       '"EnergyReset1 {} {}".format(int(round(float($)//100)), @["energy_kWhtotal_time"])')) ),
    'energy_kWhyesterday':          (HARDWARE.ESP,   '<L',  0x374,       (None, '0 <= $ <= 4294967295',         ('Power',       '"EnergyReset2 {} {}".format(int(round(float($)//100)), @["energy_kWhtotal_time"])')) ),
    'energy_kWhtotal':              (HARDWARE.ESP,   '<L',  0x554,       (None, '0 <= $ <= 4294967295',         ('Power',       '"EnergyReset3 {} {}".format(int(round(float($)//100)), @["energy_kWhtotal_time"])')) ),
    'device_group_maps':            (HARDWARE.ESP,   '<L',  0xFB0,       (None, None,                           ('Control',     None)) ),
                                    })
SETTING_9_2_0_3['webcam_config'][1].update ({
        'rtsp':                     (HARDWARE.ESP32, '<L', (0x44C,1, 3), (None, None,                           ('Control',     '"WCRtsp {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_2_0_4 = copy.deepcopy(SETTING_9_2_0_3)
SETTING_9_2_0_4['flag5'][1].update  ({
        'zb_topic_endpoint':        (HARDWARE.ESP,   '<L', (0xFB4,1, 6), (None, None,                           ('SetOption',   '"SO120 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_2_0_5 = copy.deepcopy(SETTING_9_2_0_4)
SETTING_9_2_0_5.update             ({
    'power_esp32':                  (HARDWARE.ESP32, '<L',  0x2E8,       (None, '0 <= $ <= 0b1111111111111111111111111111',
                                                                                                                ('Control',     'list("Power{} {}".format(i+1, (int($,0)>>i & 1) ) for i in range(0, 28))')),'"0x{:08x}".format($)' ),
                                    })
# ======================================================================
SETTING_9_2_0_6 = copy.deepcopy(SETTING_9_2_0_5)
SETTING_9_2_0_6[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].pop()  # SET_MAX
SETTING_9_2_0_6[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].pop()  # SET_SHD_PARAM
SETTING_9_2_0_6[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_SWITCH_TXT9', 'SET_SWITCH_TXT10', 'SET_SWITCH_TXT11', 'SET_SWITCH_TXT12', 'SET_SWITCH_TXT13', 'SET_SWITCH_TXT14', 'SET_SWITCH_TXT15', 'SET_SWITCH_TXT16',
                                                       'SET_SWITCH_TXT17', 'SET_SWITCH_TXT18', 'SET_SWITCH_TXT19', 'SET_SWITCH_TXT20', 'SET_SWITCH_TXT21', 'SET_SWITCH_TXT22', 'SET_SWITCH_TXT23', 'SET_SWITCH_TXT24',
                                                       'SET_SWITCH_TXT25', 'SET_SWITCH_TXT26', 'SET_SWITCH_TXT27', 'SET_SWITCH_TXT28'])
SETTING_9_2_0_6[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_SHD_PARAM'])
SETTING_9_2_0_6[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_MAX'])

SETTING_9_2_0_6.update              ({
    'switchtext':                   (HARDWARE.ESP82, '699s',(0x017,'SET_SWITCH_TXT1'),
                                                                         ([8],  None,                           ('Management',  '"SwitchText{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
    'switchtext_esp32':             (HARDWARE.ESP32, '699s',(0x017,'SET_SWITCH_TXT1'),
                                                                         ([28],  None,                          ('Management',  '"SwitchText{} {}".format(#+1,"\\"" if len($) == 0 else $)')) ),
    'shelly_dimmer':                (HARDWARE.ESP82, '699s',(0x017,'SET_SHD_PARAM'),
                                                                         (None,  None,                          ('Light',       None)) ),
    'shelly_dimmer_esp32':          (HARDWARE.ESP32, '699s',(0x017,'SET_SHD_PARAM'),
                                                                         (None,  None,                          ('Light',       None)) ),
    'switchmode':                   (HARDWARE.ESP82, 'B',   0x4A9,       ([8],  '0 <= $ <= 15',                 ('Control',     '"SwitchMode{} {}".format(#+1,$)')) ),
    'switchmode_esp32':             (HARDWARE.ESP32, 'B',   0x4A9,       ([28], '0 <= $ <= 15',                 ('Control',     '"SwitchMode{} {}".format(#+1,$)')) ),
    'interlock':                    (HARDWARE.ESP82, '<L',  0x4D0,       ([4],  None,                           ('Control',     '"Interlock "+" ".join(",".join(str(i+1) for i in range(0,8) if j & (1<<i) ) for j in @["interlock"])')), '"0x{:08x}".format($)' ),
    'interlock_esp32':              (HARDWARE.ESP32, '<L',  0x4D0,       ([14], None,                           ('Control',     '"Interlock "+" ".join(",".join(str(i+1) for i in range(0,8) if j & (1<<i) ) for j in @["interlock_esp32"])')), '"0x{:08x}".format($)' ),
                                    })
# ======================================================================
SETTING_9_2_0_7 = copy.deepcopy(SETTING_9_2_0_6)
SETTING_9_2_0_7.pop('device_group_maps', None)
SETTING_9_2_0_7.update              ({
    'device_group_tie':             (HARDWARE.ESP,   'B',   0xFB0,       ([4],  None,                           ('Control',     '"DevGroupTie{} {}".format(#+1, $)')) ),
                                    })
# ======================================================================
SETTING_9_3_0_1 = copy.deepcopy(SETTING_9_2_0_7)
SETTING_9_3_0_1['flag5'][1].update  ({
        'mqtt_state_retain':        (HARDWARE.ESP,   '<L', (0xFB4,1, 7), (None, None,                           ('MQTT',        '"StateRetain {}".format($)')) ),
        'mqtt_info_retain':         (HARDWARE.ESP,   '<L', (0xFB4,1, 8), (None, None,                           ('MQTT',        '"InfoRetain {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_3_1_1 = copy.deepcopy(SETTING_9_3_0_1)
SETTING_9_3_1_1.update              ({
    'display_options':              (HARDWARE.ESP, {
        'ilimode':                  (HARDWARE.ESP,   'B',  (0x313,3, 0), (None, '1 <= $ <= 7',                  ('Display',     '"DisplayILIMode {}".format($)')) ),
        'invert':                   (HARDWARE.ESP,   'B',  (0x313,1, 3), (None, '0 <= $ <= 1',                  ('Display',     '"DisplayInvert {}".format($)')) ),
                                    },                      0x313,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
SETTING_9_3_1_1['flag5'][1].update  ({
        'wiegand_hex_output':       (HARDWARE.ESP,   '<L', (0xFB4,1, 9), (None, None,                           ('SetOption',   '"SO123 {}".format($)')) ),
        'wiegand_keypad_to_tag':    (HARDWARE.ESP,   '<L', (0xFB4,1,10), (None, None,                           ('SetOption',   '"SO124 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_3_1_2 = copy.deepcopy(SETTING_9_3_1_1)
SETTING_9_3_1_2['flag5'][1].pop('teleinfo_baudrate',None)
SETTING_9_3_1_2['flag5'][1].pop('teleinfo_rawdata',None)
SETTING_9_3_1_2.update              ({
    'mqtt_keepalive':               (HARDWARE.ESP,   '<H',  0x52C,       (None, '1 <= $ <= 100',                ('MQTT',        '"MqttKeepAlive {}".format($)')) ),
    'mqtt_socket_timeout':          (HARDWARE.ESP,   '<H',  0x52E,       (None, '1 <= $ <= 100',                ('MQTT',        '"MqttTimeout {}".format($)')) ),
    'teleinfo':                     (HARDWARE.ESP, {
        'raw_skip':                 (HARDWARE.ESP,   '<L', (0xFA4,8, 0), (None, None,                           ('Power',       None)) ),
        'raw_report_changed':       (HARDWARE.ESP,   '<L', (0xFA4,1, 8), (None, None,                           ('Power',       None)) ),
        'raw_send':                 (HARDWARE.ESP,   '<L', (0xFA4,1, 9), (None, None,                           ('Power',       None)) ),
        'raw_limit':                (HARDWARE.ESP,   '<L', (0xFA4,1,10), (None, None,                           ('Power',       None)) ),
        'mode_standard':            (HARDWARE.ESP,   '<L', (0xFA4,1,11), (None, None,                           ('Power',       None)) ),
                                    },                      0xFA4,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
SETTING_9_3_1_2['flag5'][1].update  ({
        'zigbee_hide_-bridge_topic': (HARDWARE.ESP,  '<L', (0xFB4,1,11), (None, None,                           ('SetOption',   '"SO125 {}".format($)')) ),
        'ds18x20_mean':             (HARDWARE.ESP,   '<L', (0xFB4,1,12), (None, None,                           ('SetOption',   '"SO126 {}".format($)')) ),
                                    })
SETTING_9_3_1_2['mcp230xx_config'][1].update ({
        'keep_output':              (HARDWARE.ESP,   '<H', (0x6F6,1,13), (None, None,                           ('Sensor',      None)) ),
                                    })
SETTING_9_3_1_2.pop('display_options',None)
SETTING_9_3_1_2.update              ({
    'display_options':              (HARDWARE.ESP, {
        'type':                     (HARDWARE.ESP,   'B',  (0x313,3, 0), (None, '1 <= $ <= 7',                  ('Display',     '"DisplayType {}".format($)')) ),
        'invert':                   (HARDWARE.ESP,   'B',  (0x313,1, 3), (None, '0 <= $ <= 1',                  ('Display',     '"DisplayInvert {}".format($)')) ),
                                    },                      0x313,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
# ======================================================================
SETTING_9_4_0_0 = copy.deepcopy(SETTING_9_3_1_2)
SETTING_9_4_0_0.update              ({
    'mbflag2':                      (HARDWARE.ESP, {
        'temperature_set_res':      (HARDWARE.ESP,   '<L', (0xFD8,2,30), (None, '0 <= $ <= 3',                  ('Management',  '"TuyaTempSetRes {}".format($)')) ),
                                    },                      0xFD8,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
# ======================================================================
SETTING_9_4_0_3 = copy.deepcopy(SETTING_9_4_0_0)
SETTING_9_4_0_3.update              ({
    'sbflag1':                      (HARDWARE.ESP, {
        'telegram_send_enable':     (HARDWARE.ESP,   '<L', (0xFA0,1,0),  (None, '0 <= $ <= 1',                  ('Telegram',     '"TmState {}".format($)')) ),
        'telegram_recv_enable':     (HARDWARE.ESP,   '<L', (0xFA0,1,1),  (None, '0 <= $ <= 1',                  ('Telegram',     '"TmState {}".format($+2)')) ),
        'telegram_echo_enable':     (HARDWARE.ESP,   '<L', (0xFA0,1,2),  (None, '0 <= $ <= 1',                  ('Telegram',     '"TmState {}".format($+4)')) ),
                                    },                      0xFA0,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
# ======================================================================
SETTING_9_4_0_5 = copy.deepcopy(SETTING_9_4_0_3)
# ======================================================================
SETTING_9_4_0_6 = copy.deepcopy(SETTING_9_4_0_5)
SETTING_9_4_0_6.update              ({
    'mqtt_wifi_timeout':            (HARDWARE.ESP,   'B',   0x530,       (None, '1 <= $ <= 200',                ('MQTT',        '"MqttWifiTimeout {}".format($)')), ('$ * 100','$ // 100') ),
                                    })
# ======================================================================
SETTING_9_5_0_2 = copy.deepcopy(SETTING_9_4_0_6)
SETTING_9_5_0_2['flag5'][1].update  ({
        'wifi_no_sleep':            (HARDWARE.ESP,   '<L', (0xFB4,1,13), (None, None,                           ('SetOption',   '"SO127 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_5_0_3 = copy.deepcopy(SETTING_9_5_0_2)
SETTING_9_5_0_3.update              ({
    'sensors':                      (HARDWARE.ESP,   '<L',  0x794,       ([2,4],  None,                         ('Wifi',        None)), '"0x{:08x}".format($)' ),
                                    })
# ======================================================================
SETTING_9_5_0_4 = copy.deepcopy(SETTING_9_5_0_3)
SETTING_9_5_0_4.update              ({
    'ip_address':                   (HARDWARE.ESP,   '<L',  0x544,       ([5],  None,                           ('Wifi',        '"IPAddress{} {}".format(#+1,$)')), ("socket.inet_ntoa(struct.pack('<L', $))", "struct.unpack('<L', socket.inet_aton($))[0]")),
    'energy_kWhtotal':              (HARDWARE.ESP,   '<L',  0xF9C,       (None, '0 <= $ <= 4294967295',         ('Power',       '"EnergyReset3 {} {}".format(int(round(float($)//100)), @["energy_kWhtotal_time"])')) ),
                                    })
# ======================================================================
SETTING_9_5_0_5 = copy.deepcopy(SETTING_9_5_0_4)
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].pop()    # SET_MAX
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].pop()  # SET_MAX
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].pop()  # SET_MAX
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_RGX_SSID', 'SET_RGX_PASSWORD', 'SET_INFLUXDB_HOST', 'SET_INFLUXDB_PORT', 'SET_INFLUXDB_ORG', 'SET_INFLUXDB_TOKEN', 'SET_INFLUXDB_BUCKET'])
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_RGX_SSID', 'SET_RGX_PASSWORD', 'SET_INFLUXDB_HOST', 'SET_INFLUXDB_PORT', 'SET_INFLUXDB_ORG', 'SET_INFLUXDB_TOKEN', 'SET_INFLUXDB_BUCKET'])
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_RGX_SSID', 'SET_RGX_PASSWORD', 'SET_INFLUXDB_HOST', 'SET_INFLUXDB_PORT', 'SET_INFLUXDB_ORG', 'SET_INFLUXDB_TOKEN', 'SET_INFLUXDB_BUCKET'])
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MAX'])
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_MAX'])
SETTING_9_5_0_5[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_MAX'])
SETTING_9_5_0_5.update              ({
    'ipv4_rgx_address':             (HARDWARE.ESP,   '<L',  0x558,       (None, None,                           ('Wifi',        '"RgxAddress {}".format($)')), ("socket.inet_ntoa(struct.pack('<L', $))", "struct.unpack('<L', socket.inet_aton($))[0]") ),
    'ipv4_rgx_subnetmask':          (HARDWARE.ESP,   '<L',  0x55C,       (None, None,                           ('Wifi',        '"RgxSubnet {}".format($)')), ("socket.inet_ntoa(struct.pack('<L', $))", "struct.unpack('<L', socket.inet_aton($))[0]") ),
    'influxdb_version':             (HARDWARE.ESP,   'B',   0xEF7,       (None, None,                           ('Management',  None)) ),
    'influxdb_port':                (HARDWARE.ESP,   '<H',  0x4CE,       (None, None,                           ('Management',  '"IfxPort {}".format($)')) ),
    'influxdb_host':                (HARDWARE.ESP82, '699s',(0x017,'SET_INFLUXDB_HOST'),
                                                                         (None,  None,                          ('Management',  '"IfxHost {}".format("\\"" if len($) == 0 else $)')) ),
    'influxdb_host32':              (HARDWARE.ESP32, '699s',(0x017,'SET_INFLUXDB_HOST'),
                                                                         (None,  None,                          ('Management',  '"IfxHost {}".format("\\"" if len($) == 0 else $)')) ),
    'influxdb_org':                 (HARDWARE.ESP82, '699s',(0x017,'SET_INFLUXDB_ORG'),
                                                                         (None,  None,                          ('Management',  '"Ifx{} {}".format("Org" if @["influxdb_version"] == 2 else "User", "\\"" if len($) == 0 else $)')) ),
    'influxdb_org32':               (HARDWARE.ESP32, '699s',(0x017,'SET_INFLUXDB_ORG'),
                                                                         (None,  None,                          ('Management',  '"Ifx{} {}".format("Org" if @["influxdb_version"] == 2 else "User", "\\"" if len($) == 0 else $)')) ),
    'influxdb_token':               (HARDWARE.ESP82, '699s',(0x017,'SET_INFLUXDB_TOKEN'),
                                                                         (None,  None,                          ('Management',  '"Ifx{} {}".format("Token" if @["influxdb_version"] == 2 else "Password", "\\"" if len($) == 0 else $)')) ),
    'influxdb_token32':             (HARDWARE.ESP32, '699s',(0x017,'SET_INFLUXDB_TOKEN'),
                                                                         (None,  None,                          ('Management',  '"Ifx{} {}".format("Token" if @["influxdb_version"] == 2 else "Password", "\\"" if len($) == 0 else $)')) ),
    'influxdb_bucket':              (HARDWARE.ESP82, '699s',(0x017,'SET_INFLUXDB_BUCKET'),
                                                                         (None,  None,                          ('Management',  '"IfxBucket {}".format("\\"" if len($) == 0 else $$)')) ),
    'influxdb_bucket32':            (HARDWARE.ESP32, '699s',(0x017,'SET_INFLUXDB_BUCKET'),
                                                                         (None,  None,                          ('Management',  '"IfxBucket {}".format("\\"" if len($) == 0 else $)')) ),
    'rgx_ssid':                     (HARDWARE.ESP82, '699s',(0x017,'SET_RGX_SSID'),
                                                                         (None,  None,                          ('Wifi',        '"RgxSSId {}".format("\\"" if len($) == 0 else $)')) ),
    'rgx_ssid_esp32':               (HARDWARE.ESP32, '699s',(0x017,'SET_RGX_SSID'),
                                                                         (None,  None,                          ('Wifi',        '"RgxSSId {}".format("\\"" if len($) == 0 else $)')) ),
    'rgx_pwassword':                (HARDWARE.ESP82, '699s',(0x017,'SET_RGX_PASSWORD'),
                                                                         (None,  None,                          ('Wifi',        '"RgxPassword {}".format("\\"" if len($) == 0 else $)')) ),
    'rgx_pwassword_esp32':          (HARDWARE.ESP32, '699s',(0x017,'SET_RGX_PASSWORD'),
                                                                         (None,  None,                          ('Wifi',        '"RgxPassword {}".format("\\"" if len($) == 0 else $)')) ),
                                    })
SETTING_9_5_0_5['flag5'][1].update  ({
        'disable_referer_chk':      (HARDWARE.ESP,   '<L', (0xFB4,1,14), (None, None,                           ('SetOption',   '"SO128 {}".format($)')) ),
                                    })
SETTING_9_5_0_5['sbflag1'][1].update  ({
        'range_extender':           (HARDWARE.ESP,   '<L', (0xFA0,1,3), (None, '0 <= $ <= 1',                   ('Wifi',        '"RgxState {}".format($)')) ),
        'range_extender_napt':      (HARDWARE.ESP,   '<L', (0xFA0,1,4), (None, '0 <= $ <= 1',                   ('Wifi',        '"RgxNAPT {}".format($)')) ),
        'sonoff_l1_music_sync':     (HARDWARE.ESP,   '<L', (0xFA0,1,5), (None, '0 <= $ <= 1',                   ('Management',  '"L1MusicSync {}".format($)')) ),
        'influxdb_default':         (HARDWARE.ESP,   '<L', (0xFA0,1,6), (None, '0 <= $ <= 1',                   ('Management',  None)) ),
        'influxdb_state':           (HARDWARE.ESP,   '<L', (0xFA0,1,7), (None, '0 <= $ <= 1',                   ('Management',  '"Ifx {}".format($)')) ),
                                    })
# ======================================================================
SETTING_9_5_0_7 = copy.deepcopy(SETTING_9_5_0_5)
# ======================================================================
SETTING_9_5_0_8 = copy.deepcopy(SETTING_9_5_0_7)
SETTING_9_5_0_8.pop('display_dimmer', None)
SETTING_9_5_0_8.update              ({
    'display_dimmer_protected':     (HARDWARE.ESP,   'b',   0x2E0,       (None, '-100 <= $ <= 15',              ('Display',     '"DisplayDimmer {}".format(abs($))')) ),
                                    })
SETTING_9_5_0_8['flag'][1].update   ({
        'mqtt_add_global_info':     (HARDWARE.ESP,   '<L', (0x010,1, 2), (None, None,                           ('SetOption',   '"SO2 {}".format($)')) ),
                                    })
SETTING_9_5_0_8['flag'][1].pop('value_units',None)
# ======================================================================
SETTING_9_5_0_9 = copy.deepcopy(SETTING_9_5_0_8)
SETTING_9_5_0_9.update              ({
    'energy_kWhtoday_ph':           (HARDWARE.ESP,   '<l',  0x314,       ([3], '0 <= $ <= 4294967295',          ('Power',       '"EnergyToday{} {}".format(#+1,int(round(float($)//100)))')) ),
    'energy_kWhyesterday_ph':       (HARDWARE.ESP,   '<l',  0x320,       ([3], '0 <= $ <= 4294967295',          ('Power',       '"EnergyYesterday{} {}".format(#+1,int(round(float($)//100)))')) ),
    'energy_kWhtotal_ph':           (HARDWARE.ESP,   '<l',  0x32C,       ([3], '0 <= $ <= 4294967295',          ('Power',       '"EnergyTotal{} {}".format(#+1,int(round(float($)//100)))')) ),
                                    })
SETTING_9_5_0_9['flag5'][1].update  ({
        'energy_phase':             (HARDWARE.ESP,   '<L', (0xFB4,1,15), (None, None,                           ('SetOption',   '"SO129 {}".format($)')) ),
        'show_heap_with_timestamp': (HARDWARE.ESP,   '<L', (0xFB4,1,16), (None, None,                           ('SetOption',   '"SO130 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_10_0_0_1 = copy.deepcopy(SETTING_9_5_0_9)
SETTING_10_0_0_1.update             ({
    'tcp_config':                   (HARDWARE.ESP,   'B',   0xF5F,       (None, '0 <= $ <= 23',                 ('Serial',      '"TCPConfig {}".format(("5N1","6N1","7N1","8N1","5N2","6N2","7N2","8N2","5E1","6E1","7E1","8E1","5E2","6E2","7E2","8E2","5O1","6O1","7O1","8O1","5O2","6O2","7O2","8O2")[$ % 24])')) ),
    'shutter_tilt_config':          (HARDWARE.ESP,   'b',   0x508,       ([5,4],None,                           ('Shutter',     'list("ShutterTiltConfig{} {}".format(k+1, list(",".join(str(@["shutter_tilt_config"][i][j]) for i in range(0, len(@["shutter_tilt_config"]))) for j in range(0, len(@["shutter_tilt_config"][0])))[k]) for k in range(0,len(@["shutter_tilt_config"][0])))')) ),
    'shutter_tilt_pos':             (HARDWARE.ESP,   'b',   0x51C,       ([4],  None,                           ('Shutter',     None)) ),
                                    })
# ======================================================================
SETTING_10_0_0_3 = copy.deepcopy(SETTING_10_0_0_1)
SETTING_10_0_0_3.update             ({
    'light_step_pixels':            (HARDWARE.ESP,   'B',   0xF60,       (None, None,                           ('Light',      '"StepPixels {}".format($)')) ),
    'influxdb_period':              (HARDWARE.ESP,   '<H',  0x520,       (None, '0 <= $ <= 3600',               ('Management', '"IfxPeriod {}".format($)')) ),
                                    })
SETTING_10_0_0_3['flag5'][1].update ({
        'tuya_allow_dimmer_0':      (HARDWARE.ESP,   '<L', (0xFB4,1,17), (None, None,                           ('SetOption',   '"SO131 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_10_0_0_4 = copy.deepcopy(SETTING_10_0_0_3)
SETTING_10_0_0_4.update             ({
    'shift595_device_count':        (HARDWARE.ESP,   'B',   0xEC6,       (None, None,                           ('Sensor',     '"Shift595DeviceCount {}".format($)')) ),
                                    })
SETTING_10_0_0_4['sbflag1'][1].update({
        'sspm_display':             (HARDWARE.ESP32, '<L', (0xFA0,1,8),  (None, '0 <= $ <= 1',                  ('Management',  '"SSPMDisplay {}".format($)')) ),
                                    })
SETTING_10_0_0_4['flag5'][1].update ({
        'tls_use_fingerprint':      (HARDWARE.ESP,   '<L', (0xFB4,1,18), (None, None,                           ('SetOption',   '"SO132 {}".format($)')) ),
        'shift595_invert_outputs':  (HARDWARE.ESP,   '<L', (0xFB4,1,19), (None, None,                           ('SetOption',   '"SO133 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_10_1_0_3 = copy.deepcopy(SETTING_10_0_0_4)
SETTING_10_1_0_3.update             ({
    'sserial_config':               (HARDWARE.ESP,   'B',   0x33E,       (None, None,                           ('Serial',      '"SSerialConfig {}".format(("5N1","6N1","7N1","8N1","5N2","6N2","7N2","8N2","5E1","6E1","7E1","8E1","5E2","6E2","7E2","8E2","5O1","6O1","7O1","8O1","5O2","6O2","7O2","8O2")[$ % 24])')) ),
                                    })
# ======================================================================
SETTING_10_1_0_5 = copy.deepcopy(SETTING_10_1_0_3)
SETTING_10_1_0_5.update            ({
    'eth_ipv4_address':             (HARDWARE.ESP32, '<L',  0xF88,       ([5], None,                            ('Wifi',        'list("{} {}".format(["EthIPAddress","EthGateway","EthSubnetmask","EthDNSServer","EthDNSServer2"][i], socket.inet_ntoa(struct.pack("<L", @["eth_ipv4_address"][i]))) for i in range(0, len(@["eth_ipv4_address"])))')), ("socket.inet_ntoa(struct.pack('<L', $))", "struct.unpack('<L', socket.inet_aton($))[0]") ),
                                    })
# ======================================================================
SETTING_10_1_0_6 = copy.deepcopy(SETTING_10_1_0_5)
SETTING_10_1_0_6.update            ({
    'web_time_start':               (HARDWARE.ESP,   'B',   0x33C,       (None, None,                           ('Management',  '"WebTime {},{}".format($,@["web_time_end"])')) ),
    'web_time_end':                 (HARDWARE.ESP,   'B',   0x33D,       (None, None,                           ('Management',  None)) ),
    'pwm_value_ext':                (HARDWARE.ESP32, '<H',  0x560,       ([11], '0 <= $ <= 1023',               ('Management',  '"Pwm{} {}".format(#+1+5,$)')) ),
    'eth_type':                     (HARDWARE.ESP32ex,
                                                     'B',   0x446,       (None, '0 <= $ <= 1',                  ('Wifi',        '"EthType {}".format($)')) ),
    'eth_type_esp32s3':             (HARDWARE.ESP32S3,
                                                     'B',   0x40E,       (None, '0 <= $ <= 1',                  ('Wifi',        '"EthType {}".format($)')) ),
    'eth_clk_mode':                 (HARDWARE.ESP32ex,
                                                     'B',   0x447,       (None, '0 <= $ <= 3',                  ('Wifi',        '"EthClockMode {}".format($)')) ),
    'eth_clk_mode_esp32s3':         (HARDWARE.ESP32S3,
                                                     'B',   0x40F,       (None, '0 <= $ <= 3',                  ('Wifi',        '"EthClockMode {}".format($)')) ),
    'eth_address':                  (HARDWARE.ESP32ex,
                                                     'B',   0x450,       (None, '0 <= $ <= 31',                 ('Wifi',        '"EthAddress {}".format($)')) ),
    'eth_address_esp32s3':          (HARDWARE.ESP32S3,
                                                     'B',   0x45E,       (None, '0 <= $ <= 31',                 ('Wifi',        '"EthAddress {}".format($)')) ),
    'module':                       (HARDWARE.ESP82_32ex,
                                                     'B',   0x474,       (None, None,                           ('Management',  '"Module {}".format($)')) ),
    'module_esp32s3':               (HARDWARE.ESP32S3,
                                                     'B',   0x45F,       (None, None,                           ('Management',  '"Module {}".format($)')) ),
    'webcam_config':                (HARDWARE.ESP32ex, {
        'stream':                   (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 0), (None, None,                           ('Control',     '"WCStream {}".format($)')) ),
        'mirror':                   (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 1), (None, None,                           ('Control',     '"WCMirror {}".format($)')) ),
        'flip':                     (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 2), (None, None,                           ('Control',     '"WCFlip {}".format($)')) ),
        'rtsp':                     (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 3), (None, None,                           ('Control',     '"WCRtsp {}".format($)')) ),
        'contrast':                 (HARDWARE.ESP32ex,
                                                     '<l', (0x44C,3,18), (None, '0 <= $ <= 4',                  ('Control',     '"WCContrast {}".format($-2)')) ),
        'brightness':               (HARDWARE.ESP32ex,
                                                     '<l', (0x44C,3,22), (None, '0 <= $ <= 4',                  ('Control',     '"WCBrightness {}".format($-2)')) ),
        'saturation':               (HARDWARE.ESP32ex,
                                                     '<l', (0x44C,3,25), (None, '0 <= $ <= 4',                  ('Control',     '"WCSaturation {}".format($-2)')) ),
        'resolution':               (HARDWARE.ESP32ex,
                                                     '<l', (0x44C,4,28), (None, '0 <= $ <= 10',                 ('Control',     '"WCResolution {}".format($)')) ),
                                    },                      0x44C,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
    'webcam_config_esp32s3':        (HARDWARE.ESP32S3, {
        'stream':                   (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 0), (None, None,                           ('Control',     '"WCStream {}".format($)')) ),
        'mirror':                   (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 1), (None, None,                           ('Control',     '"WCMirror {}".format($)')) ),
        'flip':                     (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 2), (None, None,                           ('Control',     '"WCFlip {}".format($)')) ),
        'rtsp':                     (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 3), (None, None,                           ('Control',     '"WCRtsp {}".format($)')) ),
        'contrast':                 (HARDWARE.ESP32S3,
                                                     '<L', (0x460,3,18), (None, '0 <= $ <= 4',                  ('Control',     '"WCContrast {}".format($-2)')) ),
        'brightness':               (HARDWARE.ESP32S3,
                                                     '<L', (0x460,3,22), (None, '0 <= $ <= 4',                  ('Control',     '"WCBrightness {}".format($-2)')) ),
        'saturation':               (HARDWARE.ESP32S3,
                                                     '<L', (0x460,3,25), (None, '0 <= $ <= 4',                  ('Control',     '"WCSaturation {}".format($-2)')) ),
        'resolution':               (HARDWARE.ESP32S3,
                                                     '<L', (0x460,4,28), (None, '0 <= $ <= 10',                 ('Control',     '"WCResolution {}".format($)')) ),
                                    },                      0x460,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
    'ws_width':                     (HARDWARE.ESP82_32ex,
                                                     'B',   0x481,       ([3],  None,                           ('Light',       None)) ),
    'ws_width_esp32s3':             (HARDWARE.ESP32S3,
                                                     'B',   0x464,       ([3],  None,                           ('Light',       None)) ),
    'serial_delimiter':             (HARDWARE.ESP82_32ex,
                                                     'B',   0x451,       (None, None,                           ('Serial',      '"SerialDelimiter {}".format($)')) ),
    'serial_delimiter_esp32s3':     (HARDWARE.ESP32S3,
                                                     'B',   0x467,       (None, None,                           ('Serial',      '"SerialDelimiter {}".format($)')) ),
    'seriallog_level':              (HARDWARE.ESP82_32ex,
                                                     'B',   0x452,       (None, '0 <= $ <= 4',                  ('Management',  '"SerialLog {}".format($)')) ),
    'seriallog_level_esp32s3':      (HARDWARE.ESP32S3,
                                                     'B',   0x468,       (None, '0 <= $ <= 4',                  ('Management',  '"SerialLog {}".format($)')) ),
    'sleep':                        (HARDWARE.ESP82_32ex,
                                                     'B',   0x453,       (None, '0 <= $ <= 250',                ('Management',  '"Sleep {}".format($)')) ),
    'sleep_esp32s3':                (HARDWARE.ESP32S3,
                                                     'B',   0x469,       (None, '0 <= $ <= 250',                ('Management',  '"Sleep {}".format($)')) ),
    'domoticz_switch_idx':          (HARDWARE.ESP82_32ex,
                                                     '<H',  0x454,       ([4],  None,                           ('Domoticz',    '"DomoticzSwitchIdx{} {}".format(#+1,$)')) ),
    'domoticz_switch_idx_esp32s3':  (HARDWARE.ESP32S3,
                                                     '<H',  0x46A,       ([4],  None,                           ('Domoticz',    '"DomoticzSwitchIdx{} {}".format(#+1,$)')) ),
    'domoticz_sensor_idx':          (HARDWARE.ESP82_32ex,
                                                     '<H',  0x45C,       ([12], None,                           ('Domoticz',    '"DomoticzSensorIdx{} {}".format(#+1,$)')) ),
    'domoticz_sensor_idx_esp32s3':  (HARDWARE.ESP32S3,
                                                     '<H',  0x472,       ([12], None,                           ('Domoticz',    '"DomoticzSensorIdx{} {}".format(#+1,$)')) ),
    'ws_color':                     (HARDWARE.ESP82_32ex,
                                                     'B',   0x475,       ([4,3],None,                           ('Light',       None)) ),
    'ws_color_esp32s3':             (HARDWARE.ESP32S3,
                                                     'B',   0x48A,       ([4,3],None,                           ('Light',       None)) ),
    'my_gp_esp32':                  (HARDWARE.ESP32ex,
                                                     '<H',  0x3AC,       ([40], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
    'my_gp_esp32c3':                (HARDWARE.ESP32C3,
                                                     '<H',  0x3AC,       ([22], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
    'my_gp_esp32s2':                (HARDWARE.ESP32S2,
                                                     '<H',  0x3AC,       ([47], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
    'my_gp_esp32s3':                (HARDWARE.ESP32S3,
                                                     '<H',  0x3AC,       ([49], None,                           ('Management',  '"Gpio{} {}".format(#, $)')) ),
                                    })
SETTING_10_1_0_6['user_template_esp32'][1].update({
        'gpio':                     (HARDWARE.ESP32ex,
                                                     '<H',  0x3FC,       ([36], None,                           ('Management',  None)), ('1 if $==65504 else $','65504 if $==1 else $')),
        'flag':                     (HARDWARE.ESP32ex,
                                                     '<H',  0x3FC+(2*36),(None, None,                           ('Management',  None)) ),
        'gpio_esp32c3':             (HARDWARE.ESP32C3,
                                                     '<H',  0x3FC,       ([22], None,                           ('Management',  None)), ('1 if $==65504 else $','65504 if $==1 else $')),
        'flag_esp32c3':             (HARDWARE.ESP32C3,
                                                     '<H',  0x3FC+(2*22),(None, None,                           ('Management',  None)) ),
        'gpio_esp32s2':             (HARDWARE.ESP32S2,
                                                     '<H',  0x3FC,       ([36], None,                           ('Management',  None)), ('1 if $==65504 else $','65504 if $==1 else $')),
        'flag_esp32s2':             (HARDWARE.ESP32S2,
                                                     '<H',  0x3FC+(2*36),(None, None,                           ('Management',  None)) ),
        'gpio_esp32s3':             (HARDWARE.ESP32S3,
                                                     '<H',  0x410,       ([33], None,                           ('Management',  None)), ('1 if $==65504 else $','65504 if $==1 else $')),
        'flag_esp32s3':             (HARDWARE.ESP32S3,
                                                     '<H',  0x410+(2*33),(None, None,                           ('Management',  None)) ),
                                    })
SETTING_10_1_0_6['flag5'][1].update({
        'pwm_force_same_phase':     (HARDWARE.ESP,   '<L', (0xFB4,1,20), (None, None,                           ('SetOption',   '"SO134 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_0_0_3 = copy.deepcopy(SETTING_10_1_0_6)
SETTING_11_0_0_3.update            ({
    'pulse_timer':                  (HARDWARE.ESP,   '<H',  0x57C,       ([32], '0 <= $ <= 65535',              ('Control',     '"PulseTime{} {}".format(#+1,$)')) ),
    'rf_duplicate_time':            (HARDWARE.ESP,   '<H',  0x522,       (None, '10 <= $ <= 65535',             ('Rf',          '"RfTimeOut {}".format($)')) ),
                                    })
SETTING_11_0_0_3['flag5'][1].update({
        'display_no_splash':        (HARDWARE.ESP,   '<L', (0xFB4,1,21), (None, None,                           ('SetOption',   '"SO135 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_0_0_4 = copy.deepcopy(SETTING_11_0_0_3)
SETTING_11_0_0_4['sbflag1'][1].update({
        'local_ntp_server':         (HARDWARE.ESP32, '<L', (0xFA0,1,9),  (None, '0 <= $ <= 1',                  ('Management',  '"RtcNtpserver {}".format($)')) ),
                                    })
SETTING_11_0_0_4.update            ({
    'ds3502_state':                 (HARDWARE.ESP,   'B',  0x4CA,       ([4], '0 <= $ <= 127',                  ('Sensor',      '"Wiper{} {}".format(#+1,$)')) ),
                                    })
SETTING_11_0_0_4['flag5'][1].update({
        'tuyasns_no_immediate':     (HARDWARE.ESP,   '<L', (0xFB4,1,22), (None, None,                           ('SetOption',   '"SO136 {}".format($)')) ),
        'tuya_exclude_heartbeat':   (HARDWARE.ESP,   '<L', (0xFB4,1,23), (None, None,                           ('SetOption',   '"SO137 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_0_0_5 = copy.deepcopy(SETTING_11_0_0_4)
SETTING_11_0_0_5.update            ({
    'weight_absconv_a':             (HARDWARE.ESP,   '<l',  0x524,       (None, None,                           ('Sensor',          None)) ),
    'weight_absconv_b':             (HARDWARE.ESP,   '<l',  0x528,       (None, None,                           ('Sensor',          None)) ),
                                    })
SETTING_11_0_0_5['sbflag1'][1].update({
        'influxdb_sensor':          (HARDWARE.ESP,   '<L', (0xFA0,1,10),  (None, '0 <= $ <= 1',                 ('Management',  '"IfxSensor {}".format($)')) ),
                                    })
SETTING_11_0_0_5['flag5'][1].pop('tuya_exclude_heartbeat',None)
SETTING_11_0_0_5['flag5'][1].update({
        'tuya_exclude_from_mqtt':   (HARDWARE.ESP,   '<L', (0xFB4,1,23), (None, None,                           ('SetOption',   '"SO137 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_0_0_6 = copy.deepcopy(SETTING_11_0_0_5)
SETTING_11_0_0_6.update            ({
    'weight_absconv_a':             (HARDWARE.ESP,   '<l',  0x524,       (None, None,                           ('Sensor',          '"Sensor34 10 {}".format($)')) ),
    'weight_absconv_b':             (HARDWARE.ESP,   '<l',  0x528,       (None, None,                           ('Sensor',          '"Sensor34 11 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_0_0_7 = copy.deepcopy(SETTING_11_0_0_6)
SETTING_11_0_0_7.update            ({
    'weight_offset':                (HARDWARE.ESP,   '<l',  0x578,       (None, None,                           ('Sensor',          None)) ),
    'weight_user_tare':             (HARDWARE.ESP,   '<l',  0x338,       (None, None,                           ('Sensor',          '"Sensor34 10 {}".format($)')) ),
    'weight_absconv_a':             (HARDWARE.ESP,   '<l',  0x524,       (None, None,                           ('Sensor',          '"Sensor34 11 {}".format($)')) ),
    'weight_absconv_b':             (HARDWARE.ESP,   '<l',  0x528,       (None, None,                           ('Sensor',          '"Sensor34 12 {}".format($)')) ),
                                    })
SETTING_11_0_0_7['flag5'][1].update({
        'gui_table_align':          (HARDWARE.ESP,   '<L', (0xFB4,1,24), (None, None,                           ('SetOption',   '"SO138 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_1_0_1 = copy.deepcopy(SETTING_11_0_0_7)
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].pop()    # SET_MAX
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].pop()  # SET_MAX
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].pop()  # SET_MAX
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_INFLUXDB_RP'])
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_INFLUXDB_RP'])
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_INFLUXDB_RP'])
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].extend(['SET_MAX'])
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP82)].extend(['SET_MAX'])
SETTING_11_1_0_1[SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP32)].extend(['SET_MAX'])
SETTING_11_1_0_1.update            ({
    'influxdb_rp':                  (HARDWARE.ESP82, '699s',(0x017,'SET_INFLUXDB_RP'),
                                                                         (None,  None,                          ('Management',  '"IfxRP {}".format("\\"" if len($) == 0 else $$)')) ),
    'influxdb_rp':                  (HARDWARE.ESP32, '699s',(0x017,'SET_INFLUXDB_RP'),
                                                                         (None,  None,                          ('Management',  '"IfxRP {}".format("\\"" if len($) == 0 else $)')) ),
                                    })

SETTING_11_1_0_1.update            ({
    'energy_kWhexport_ph':          (HARDWARE.ESP,   '<l',  0xF7C,       ([3], '0 <= $ <= 4294967295',          ('Power',       '"EnergyExportActive{} {}".format(#+1,int(round(float($)//100)))')) ),
    'flowratemeter_calibration':    (HARDWARE.ESP,   '<H',  0xF78,       ([2], None,                            ('Sensor',      '"Sensor96 {} {}".format(#+1,$)'))),
                                    })
SETTING_11_1_0_1['flag5'][1].update({
        'mm_vs_inch':               (HARDWARE.ESP,   '<L', (0xFB4,1,25), (None, None,                           ('SetOption',   '"SO139 {}".format($)')) ),
                                    })
SETTING_11_1_0_1['SensorBits1'][1].update ({
        'flowratemeter_unit':       (HARDWARE.ESP,   'B',  (0x717,1, 1), (None, '0 <= $ <= 1',                  ('Sensor',      '"Sensor96 0 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_1_0_2 = copy.deepcopy(SETTING_11_1_0_1)
SETTING_11_1_0_2.update            ({
    'webcam_config2':               (HARDWARE.ESP32, {
        'wb_mode':                  (HARDWARE.ESP32, '<L', (0x730,3, 0), (None, '0 <= $ <= 6',                  ('Control',     '"WCWBMode {}".format($)')) ),
        'ae_level':                 (HARDWARE.ESP32, '<L', (0x730,3, 3), (None, '-2 <= $ <= 2',                 ('Control',     '"WCAELevel {}".format($)')), ('$ - 2','$ + 2') ),
        'aec_value':                (HARDWARE.ESP32, '<L', (0x730,11,6), (None, '0 <= $ <= 1200',               ('Control',     '"WCAECValue {}".format($)')) ),
        'gainceiling':              (HARDWARE.ESP32, '<L', (0x730,3,17), (None, '0 <= $ <= 6',                  ('Control',     '"WCGainCeiling {}".format($)')) ),
        'agc_gain':                 (HARDWARE.ESP32, '<L', (0x730,5,20), (None, '0 <= $ <= 30',                 ('Control',     '"WCAGCGain {}".format($)')) ),
        'special_effect':           (HARDWARE.ESP32, '<L', (0x730,3,25), (None, '0 <= $ <= 6',                  ('Control',     '"WCSpecialEffect {}".format($)')) ),
        'upgraded':                 (HARDWARE.ESP32, '<L', (0x730,1,31), (None, None,                           ('Control',     None)) ),
                                    },                      0x730,       (None, None,                           (VIRTUAL,       None)), (None, None) ),
                                    })
SETTING_11_1_0_2['webcam_config'][1].update({
        'awb':                      (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 4), (None, None,                           ('Control',     '"WCAWB {}".format($)')) ),
        'awb_gain':                 (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 5), (None, None,                           ('Control',     '"WCAWBGain {}".format($)')) ),
        'aec':                      (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 6), (None, None,                           ('Control',     '"WCAEC {}".format($)')) ),
        'aec2':                     (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 7), (None, None,                           ('Control',     '"WCAECDSP {}".format($)')) ),
        'raw_gma':                  (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 8), (None, None,                           ('Control',     '"WCGammaCorrect {}".format($)')) ),
        'lenc':                     (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1, 9), (None, None,                           ('Control',     '"WCLensCorrect {}".format($)')) ),
        'colorbar':                 (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1,10), (None, None,                           ('Control',     '"WCColorbar {}".format($)')) ),
        'wpc':                      (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1,11), (None, None,                           ('Control',     '"WCWPC {}".format($)')) ),
        'dcw':                      (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1,12), (None, None,                           ('Control',     '"WCDCW {}".format($)')) ),
        'bpc':                      (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,1,13), (None, None,                           ('Control',     '"WCBPC {}".format($)')) ),
        'feature':                  (HARDWARE.ESP32ex,
                                                     '<L', (0x44C,2,16), (None, '0 <= $ <= 2',                  ('Control',     '"WCFeature {}".format($)')) ),
                                    })
SETTING_11_1_0_2['webcam_config_esp32s3'][1].update({
        'awb':                      (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 4), (None, None,                           ('Control',     '"WCAWB {}".format($)')) ),
        'awb_gain':                 (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 5), (None, None,                           ('Control',     '"WCAWBGain {}".format($)')) ),
        'aec':                      (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 6), (None, None,                           ('Control',     '"WCAEC {}".format($)')) ),
        'aec2':                     (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 7), (None, None,                           ('Control',     '"WCAECDSP {}".format($)')) ),
        'raw_gma':                  (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 8), (None, None,                           ('Control',     '"WCGammaCorrect {}".format($)')) ),
        'lenc':                     (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1, 9), (None, None,                           ('Control',     '"WCLensCorrect {}".format($)')) ),
        'colorbar':                 (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1,10), (None, None,                           ('Control',     '"WCColorbar {}".format($)')) ),
        'wpc':                      (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1,11), (None, None,                           ('Control',     '"WCWPC {}".format($)')) ),
        'dcw':                      (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1,12), (None, None,                           ('Control',     '"WCDCW {}".format($)')) ),
        'bpc':                      (HARDWARE.ESP32S3,
                                                     '<L', (0x460,1,13), (None, None,                           ('Control',     '"WCBPC {}".format($)')) ),
        'feature':                  (HARDWARE.ESP32S3,
                                                     '<L', (0x460,2,16), (None, '0 <= $ <= 2',                  ('Control',     '"WCFeature {}".format($)')) ),
                                    })
SETTING_11_1_0_2['flag5'][1].update({
        'mqtt_persistent':          (HARDWARE.ESP,   '<L', (0xFB4,1,26), (None, None,                           ('SetOption',   '"SO140 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_1_0_3 = copy.deepcopy(SETTING_11_1_0_2)
SETTING_11_1_0_3.update              ({
    'flag6':                        (HARDWARE.ESP,   '<L',  0xF74,       (None, None,                           (INTERNAL,      None)), '"0x{:08x}".format($)' ),
                                    })
SETTING_11_1_0_3['flag5'][1].update({
        'gui_module_name':          (HARDWARE.ESP,   '<L', (0xFB4,1,27), (None, None,                           ('SetOption',   '"SO141 {}".format($)')) ),
                                    })
SETTING_11_1_0_3['webcam_config2'][1].update({
        'auth':                     (HARDWARE.ESP32, '<L', (0x730,1,28), (None, '0 <= $ <= 1',                  ('Control',     '"WCSAuth {}".format($)')) ),
                                    })
# ======================================================================
SETTING_11_1_0_4 = copy.deepcopy(SETTING_11_1_0_3)
SETTING_11_1_0_4['sbflag1'][1].update({
        'serbridge_console':        (HARDWARE.ESP,   '<L', (0xFA0,1,11), (None, '0 <= $ <= 1',                  ('Serial',      '"SSerialSend9 {}".format($)')) ),
                                    })
SETTING_11_1_0_4['flag5'][1].update({
        'wait_for_wifi_result':     (HARDWARE.ESP,   '<L', (0xFB4,1,28), (None, None,                           ('SetOption',   '"SO142 {}".format($)')) ),
                                    })
# ======================================================================
SETTING_12_0_1_2 = copy.deepcopy(SETTING_11_1_0_4)
SETTING_12_0_1_2.update             ({
    'dns_timeout':                  (HARDWARE.ESP,   '<H',  0x4C8,       (None, '100 <= $ <= 20000',            ('Wifi',        '"DnsTimeout {}".format($)')) ),
                                    })
# ======================================================================
SETTING_12_0_2_2 = copy.deepcopy(SETTING_12_0_1_2)
SETTING_12_0_2_2.update             ({
    'global_sensor_index':          (HARDWARE.ESP,   'B',   0x4C5,       ([3], '0 <= $ <= 251',                 ('Sensor',        None)) ),
                                    })
# ======================================================================
SETTING_12_0_2_4 = copy.deepcopy(SETTING_12_0_2_2)
SETTING_12_0_2_4.update             ({
    'modbus_sbaudrate':             (HARDWARE.ESP,   'B',   0xF61,       (None, '1 <= $ <= 384',                ('Serial',        '"ModbusBaudrate {}".format($)')), ('$ * 300','$ // 300') ),
    'modbus_sconfig':               (HARDWARE.ESP,   'B',   0xF62,       (None, None,                           ('Serial',        '"ModbusSerialConfig {}".format(("5N1","6N1","7N1","8N1","5N2","6N2","7N2","8N2","5E1","6E1","7E1","8E1","5E2","6E2","7E2","8E2","5O1","6O1","7O1","8O1","5O2","6O2","7O2","8O2")[$ % 24])')) ),
                                    })
SETTING_12_0_2_4['flag5'][1].update({
        'zigbee_no_batt_autoprobe': (HARDWARE.ESP,   '<L', (0xFB4,1,29), (None, None,                           ('SetOption',   '"SO143 {}".format($)')) ),
        'zigbee_include_time':      (HARDWARE.ESP,   '<L', (0xFB4,1,30), (None, None,                           ('SetOption',   '"SO144 {}".format($)')) ),
                                    })
SETTING_12_0_2_4.pop('energy_kWhtoday',None)
SETTING_12_0_2_4.pop('energy_kWhyesterday',None)
SETTING_12_0_2_4.pop('energy_kWhtotal',None)
# ======================================================================
SETTING_12_1_0_0 = copy.deepcopy(SETTING_12_0_2_4)
# ======================================================================
SETTINGS = [
            (0x0C010000,0x1000, SETTING_12_1_0_0),
            (0x0C000204,0x1000, SETTING_12_0_2_4),
            (0x0C000202,0x1000, SETTING_12_0_2_2),
            (0x0C000002,0x1000, SETTING_12_0_1_2),
            (0x0B010004,0x1000, SETTING_11_1_0_4),
            (0x0B010003,0x1000, SETTING_11_1_0_3),
            (0x0B010002,0x1000, SETTING_11_1_0_2),
            (0x0B010001,0x1000, SETTING_11_1_0_1),
            (0x0B000007,0x1000, SETTING_11_0_0_7),
            (0x0B000006,0x1000, SETTING_11_0_0_6),
            (0x0B000005,0x1000, SETTING_11_0_0_5),
            (0x0B000004,0x1000, SETTING_11_0_0_4),
            (0x0B000003,0x1000, SETTING_11_0_0_3),
            (0x0A010006,0x1000, SETTING_10_1_0_6),
            (0x0A010005,0x1000, SETTING_10_1_0_5),
            (0x0A010003,0x1000, SETTING_10_1_0_3),
            (0x0A000004,0x1000, SETTING_10_0_0_4),
            (0x0A000003,0x1000, SETTING_10_0_0_3),
            (0x0A000001,0x1000, SETTING_10_0_0_1),
            (0x09050009,0x1000, SETTING_9_5_0_9),
            (0x09050008,0x1000, SETTING_9_5_0_8),
            (0x09050007,0x1000, SETTING_9_5_0_7),
            (0x09050005,0x1000, SETTING_9_5_0_5),
            (0x09050004,0x1000, SETTING_9_5_0_4),
            (0x09050003,0x1000, SETTING_9_5_0_3),
            (0x09050002,0x1000, SETTING_9_5_0_2),
            (0x09040006,0x1000, SETTING_9_4_0_6),
            (0x09040005,0x1000, SETTING_9_4_0_5),
            (0x09040003,0x1000, SETTING_9_4_0_3),
            (0x09040000,0x1000, SETTING_9_4_0_0),
            (0x09030102,0x1000, SETTING_9_3_1_2),
            (0x09030101,0x1000, SETTING_9_3_1_1),
            (0x09030001,0x1000, SETTING_9_3_0_1),
            (0x09020007,0x1000, SETTING_9_2_0_7),
            (0x09020006,0x1000, SETTING_9_2_0_6),
            (0x09020005,0x1000, SETTING_9_2_0_5),
            (0x09020004,0x1000, SETTING_9_2_0_4),
            (0x09020003,0x1000, SETTING_9_2_0_3),
            (0x09020002,0x1000, SETTING_9_2_0_2),
            (0x09010002,0x1000, SETTING_9_1_0_2),
            (0x09010001,0x1000, SETTING_9_1_0_1),
            (0x09010000,0x1000, SETTING_9_1_0_0),
            (0x09000003,0x1000, SETTING_9_0_0_3),
            (0x09000002,0x1000, SETTING_9_0_0_2),
            (0x09000001,0x1000, SETTING_9_0_0_1),
            (0x08050100,0x1000, SETTING_8_5_1_0),
            (0x08050001,0x1000, SETTING_8_5_0_1),
            (0x08040003,0x1000, SETTING_8_4_0_3),
            (0x08040002,0x1000, SETTING_8_4_0_2),
            (0x08040001,0x1000, SETTING_8_4_0_1),
            (0x08040000,0x1000, SETTING_8_4_0_0),
            (0x08030107,0x1000, SETTING_8_3_1_7),
            (0x08030106,0x1000, SETTING_8_3_1_6),
            (0x08030105,0x1000, SETTING_8_3_1_5),
            (0x08030104,0x1000, SETTING_8_3_1_4),
            (0x08030103,0x1000, SETTING_8_3_1_3),
            (0x08030102,0x1000, SETTING_8_3_1_2),
            (0x08030101,0x1000, SETTING_8_3_1_1),
            (0x08030100,0x1000, SETTING_8_3_1_0),
            (0x08020006,0x1000, SETTING_8_2_0_6),
            (0x08020004,0x1000, SETTING_8_2_0_4),
            (0x08020003,0x1000, SETTING_8_2_0_3),
            (0x08020000,0x1000, SETTING_8_2_0_0),
            (0x0801000B,0x1000, SETTING_8_1_0_11),
            (0x0801000A,0x1000, SETTING_8_1_0_10),
            (0x08010009,0x1000, SETTING_8_1_0_9),
            (0x08010006,0x1000, SETTING_8_1_0_6),
            (0x08010005,0x1000, SETTING_8_1_0_5),
            (0x08010004,0x1000, SETTING_8_1_0_4),
            (0x08010003,0x1000, SETTING_8_1_0_3),
            (0x08010002,0x1000, SETTING_8_1_0_2),
            (0x08010001,0x1000, SETTING_8_1_0_1),
            (0x08010000,0x1000, SETTING_8_1_0_0),
            (0x08000001,0x1000, SETTING_8_0_0_1),
            (0x07010206,0x1000, SETTING_7_1_2_6),
            (0x07010205,0x1000, SETTING_7_1_2_5),
            (0x07010203,0x1000, SETTING_7_1_2_3),
            (0x07010202,0x1000, SETTING_7_1_2_2),
            (0x07000006,0x1000, SETTING_7_0_0_6),
            (0x07000005,0x1000, SETTING_7_0_0_5),
            (0x07000004,0x1000, SETTING_7_0_0_4),
            (0x07000003,0x1000, SETTING_7_0_0_3),
            (0x07000002,0x1000, SETTING_7_0_0_2),
            (0x07000001,0x1000, SETTING_7_0_0_1),
            (0x06060015,0x1000, SETTING_6_6_0_21),
            (0x06060014,0x1000, SETTING_6_6_0_20),
            (0x06060012,0x1000, SETTING_6_6_0_18),
            (0x0606000F,0x1000, SETTING_6_6_0_15),
            (0x0606000E,0x1000, SETTING_6_6_0_14),
            (0x0606000D,0x1000, SETTING_6_6_0_13),
            (0x0606000C,0x1000, SETTING_6_6_0_12),
            (0x0606000B,0x1000, SETTING_6_6_0_11),
            (0x0606000A,0x1000, SETTING_6_6_0_10),
            (0x06060009,0x1000, SETTING_6_6_0_9),
            (0x06060008,0x1000, SETTING_6_6_0_8),
            (0x06060007,0x1000, SETTING_6_6_0_7),
            (0x06060006, 0xe00, SETTING_6_6_0_6),
            (0x06060005, 0xe00, SETTING_6_6_0_5),
            (0x06060003, 0xe00, SETTING_6_6_0_3),
            (0x06060002, 0xe00, SETTING_6_6_0_2),
            (0x06060001, 0xe00, SETTING_6_6_0_1),
            (0x0605000F, 0xe00, SETTING_6_5_0_15),
            (0x0605000C, 0xe00, SETTING_6_5_0_12),
            (0x0605000B, 0xe00, SETTING_6_5_0_11),
            (0x0605000A, 0xe00, SETTING_6_5_0_10),
            (0x06050009, 0xe00, SETTING_6_5_0_9),
            (0x06050007, 0xe00, SETTING_6_5_0_7),
            (0x06050006, 0xe00, SETTING_6_5_0_6),
            (0x06050003, 0xe00, SETTING_6_5_0_3),
            (0x06040112, 0xe00, SETTING_6_4_1_18),
            (0x06040111, 0xe00, SETTING_6_4_1_17),
            (0x06040110, 0xe00, SETTING_6_4_1_16),
            (0x0604010D, 0xe00, SETTING_6_4_1_13),
            (0x0604010B, 0xe00, SETTING_6_4_1_11),
            (0x06040108, 0xe00, SETTING_6_4_1_8),
            (0x06040107, 0xe00, SETTING_6_4_1_7),
            (0x06040104, 0xe00, SETTING_6_4_1_4),
            (0x06040002, 0xe00, SETTING_6_4_0_2),
            (0x06030010, 0xe00, SETTING_6_3_0_16),
            (0x0603000F, 0xe00, SETTING_6_3_0_15),
            (0x0603000E, 0xe00, SETTING_6_3_0_14),
            (0x0603000D, 0xe00, SETTING_6_3_0_13),
            (0x0603000B, 0xe00, SETTING_6_3_0_11),
            (0x0603000A, 0xe00, SETTING_6_3_0_10),
            (0x06030008, 0xe00, SETTING_6_3_0_8),
            (0x06030004, 0xe00, SETTING_6_3_0_4),
            (0x06030002, 0xe00, SETTING_6_3_0_2),
            (0x06030000, 0xe00, SETTING_6_3_0),
            (0x06020114, 0xe00, SETTING_6_2_1_20),
            (0x06020113, 0xe00, SETTING_6_2_1_19),
            (0x0602010E, 0xe00, SETTING_6_2_1_14),
            (0x0602010A, 0xe00, SETTING_6_2_1_10),
            (0x06020106, 0xe00, SETTING_6_2_1_6),
            (0x06020103, 0xe00, SETTING_6_2_1_3),
            (0x06020102, 0xe00, SETTING_6_2_1_2),
            (0x06020100, 0xe00, SETTING_6_2_1),
            (0x06010100, 0xe00, SETTING_6_1_1),
            (0x06000000, 0xe00, SETTING_6_0_0),
            (0x050e0000, 0xa00, SETTING_5_14_0),
            (0x050d0100, 0xa00, SETTING_5_13_1),
            (0x050c0000, 0x670, SETTING_5_12_0),
            (0x050b0000, 0x670, SETTING_5_11_0),
            (0x050a0000, 0x670, SETTING_5_10_0),
           ]
# pylint: enable=bad-continuation,bad-whitespace,invalid-name

def check_setting_definition():
    """
    Check complete setting definition history

    @return: True if ok
    """
    for cfg in SETTINGS:
        setting = cfg[2]
        for key in setting:
            if key != SETTINGVAR:
                fielddef = setting[key]
                get_fielddef(fielddef)

    return True

# ======================================================================
# Common helper
# ======================================================================
class LogType:
    """
    Logging types
    """
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'

def message(msg, type_=None, status=None, line=None):
    """
    Writes a message to stdout

    @param msg:
        message to output
    @param type_:
        INFO, WARNING or ERROR
    @param status:
        status number
    """
    sdelimiter = ' ' if status is not None and type_ is not None and status > 0 else ''
    print('{styp}{sdelimiter1}{sstatus}{sdelimiter2}{slineno}{scolon}{smgs}'\
          .format(styp=type_ if type_ is not None else '',
                  sdelimiter1=sdelimiter,
                  sdelimiter2=sdelimiter if line is not None else '',
                  sstatus=status if status is not None and status > 0 else '',
                  scolon=': ' if type_ is not None or line is not None else '',
                  smgs=msg,
                  slineno='(@{:04d})'.format(line) if line is not None else ''),
          file=sys.stderr)

def exit_(status=0, msg="end", type_=LogType.ERROR, src=None, doexit=True, line=None):
    """
    Called when the program should be exit

    @param status:
        the exit status program returns to callert
    @param msg:
        the msg logged before exit
    @param type_:
        msg type: 'INFO', 'WARNING' or 'ERROR'
    @param doexit:
        True to exit program, otherwise return
    """
    global EXIT_CODE    # pylint: disable=global-statement

    if src is not None:
        msg = '{} ({})'.format(src, msg)
    message(msg, type_=type_ if status != ExitCode.OK else LogType.INFO, status=status, line=line)
    EXIT_CODE = status
    if doexit:
        message("Premature exit - #{} {}".format(status, ExitCode.str(status)), type_=None, status=None, line=None)
        sys.exit(EXIT_CODE)

def shorthelp(doexit=True):
    """
    Show short help (usage) only - ued by own -h handling

    @param doexit:
        sys.exit with OK if True
    """
    print(PARSER.description)
    print()
    PARSER.print_usage()
    print()
    print("For advanced help use '{prog} -H' or '{prog} --full-help'".format(prog=os.path.basename(sys.argv[0])))
    print()
    if doexit:
        sys.exit(ExitCode.OK)

# ======================================================================
# Tasmota config data handling
# ======================================================================
class Unishox:
    """
    This is a highly modified and optimized version of Unishox
    for Tasmota, aimed at compressing `Rules` which are typically
    short strings from 50 to 500 bytes.

    @author Stephan Hadinger
    @revised Norbert Richter
    """

    # pylint: disable=bad-continuation,bad-whitespace,line-too-long
    #cl_95 = [0x4000 +  3, 0x3F80 + 11, 0x3D80 + 11, 0x3C80 + 10, 0x3BE0 + 12, 0x3E80 + 10, 0x3F40 + 11, 0x3EC0 + 10, 0x3BA0 + 11, 0x3BC0 + 11, 0x3D60 + 11, 0x3B60 + 11, 0x3A80 + 10, 0x3AC0 + 10, 0x3A00 +  9, 0x3B00 + 10, 0x38C0 + 10, 0x3900 + 10, 0x3940 + 11, 0x3960 + 11, 0x3980 + 11, 0x39A0 + 11, 0x39C0 + 11, 0x39E0 + 12, 0x39F0 + 12, 0x3880 + 10, 0x3CC0 + 10, 0x3C00 +  9, 0x3D00 + 10, 0x3E00 +  9, 0x3F00 + 10, 0x3B40 + 11, 0x3BF0 + 12, 0x2B00 +  8, 0x21C0 + 11, 0x20C0 + 10, 0x2100 + 10, 0x2600 +  7, 0x2300 + 11, 0x21E0 + 12, 0x2140 + 11, 0x2D00 +  8, 0x2358 + 13, 0x2340 + 12, 0x2080 + 10, 0x21A0 + 11, 0x2E00 +  8, 0x2C00 +  8, 0x2180 + 11, 0x2350 + 13, 0x2F80 +  9, 0x2F00 +  9, 0x2A00 +  8, 0x2160 + 11, 0x2330 + 12, 0x21F0 + 12, 0x2360 + 13, 0x2320 + 12, 0x2368 + 13, 0x3DE0 + 12, 0x3FA0 + 11, 0x3DF0 + 12, 0x3D40 + 11, 0x3F60 + 11, 0x3FF0 + 12, 0xB000 +  4, 0x1C00 +  7, 0x0C00 +  6, 0x1000 +  6, 0x6000 +  3, 0x3000 +  7, 0x1E00 +  8, 0x1400 +  7, 0xD000 +  4, 0x3580 +  9, 0x3400 +  8, 0x0800 +  6, 0x1A00 +  7, 0xE000 +  4, 0xC000 +  4, 0x1800 +  7, 0x3500 +  9, 0xF800 +  5, 0xF000 +  5, 0xA000 +  4, 0x1600 +  7, 0x3300 +  8, 0x1F00 +  8, 0x3600 +  9, 0x3200 +  8, 0x3680 +  9, 0x3DA0 + 11, 0x3FC0 + 11, 0x3DC0 + 11, 0x3FE0 + 12]
    cl_95 = [0x4000 +  3, 0x3F80 + 11, 0x3D80 + 11, 0x3C80 + 10, 0x3BE0 + 12, 0x3E80 + 10, 0x3F40 + 11, 0x3EC0 + 10, 0x3BA0 + 11, 0x3BC0 + 11, 0x3D60 + 11, 0x3B60 + 11, 0x3A80 + 10, 0x3AC0 + 10, 0x3A00 +  9, 0x3B00 + 10, 0x38C0 + 10, 0x3900 + 10, 0x3940 + 11, 0x3960 + 11, 0x3980 + 11, 0x39A0 + 11, 0x39C0 + 11, 0x39E0 + 12, 0x39F0 + 12, 0x3880 + 10, 0x3CC0 + 10, 0x3C00 +  9, 0x3D00 + 10, 0x3E00 +  9, 0x3F00 + 10, 0x3B40 + 11, 0x3BF0 + 12, 0x2B00 +  8, 0x21C0 + 11, 0x20C0 + 10, 0x2100 + 10, 0x2600 +  7, 0x2300 + 11, 0x21E0 + 12, 0x2140 + 11, 0x2D00 +  8, 0x46B0 + 13, 0x2340 + 12, 0x2080 + 10, 0x21A0 + 11, 0x2E00 +  8, 0x2C00 +  8, 0x2180 + 11, 0x46A0 + 13, 0x2F80 +  9, 0x2F00 +  9, 0x2A00 +  8, 0x2160 + 11, 0x2330 + 12, 0x21F0 + 12, 0x46C0 + 13, 0x2320 + 12, 0x46D0 + 13, 0x3DE0 + 12, 0x3FA0 + 11, 0x3DF0 + 12, 0x3D40 + 11, 0x3F60 + 11, 0x3FF0 + 12, 0xB000 +  4, 0x1C00 +  7, 0x0C00 +  6, 0x1000 +  6, 0x6000 +  3, 0x3000 +  7, 0x1E00 +  8, 0x1400 +  7, 0xD000 +  4, 0x3580 +  9, 0x3400 +  8, 0x0800 +  6, 0x1A00 +  7, 0xE000 +  4, 0xC000 +  4, 0x1800 +  7, 0x3500 +  9, 0xF800 +  5, 0xF000 +  5, 0xA000 +  4, 0x1600 +  7, 0x3300 +  8, 0x1F00 +  8, 0x3600 +  9, 0x3200 +  8, 0x3680 +  9, 0x3DA0 + 11, 0x3FC0 + 11, 0x3DC0 + 11, 0x3FE0 + 12]

    # enum {SHX_STATE_1 = 1, SHX_STATE_2};    // removed Unicode state
    SHX_STATE_1 = 1
    SHX_STATE_2 = 2

    SHX_SET1 = 0
    SHX_SET1A = 1
    SHX_SET1B = 2
    SHX_SET2 = 3

    sets = [['\0', ' ', 'e', '\0', 't', 'a', 'o', 'i', 'n', 's', 'r'],
            ['\0', 'l', 'c', 'd', 'h', 'u', 'p', 'm', 'b', 'g', 'w'],
            ['f', 'y', 'v', 'k', 'q', 'j', 'x', 'z', '\0', '\0', '\0'],
            ['\0', '9', '0', '1', '2', '3', '4', '5', '6', '7', '8'],
            ['.', ',', '-', '/', '?', '+', ' ', '(', ')', '$', '@'],
            [';', '#', ':', '<', '^', '*', '"', '{', '}', '[', ']'],
            ['=', '%', '\'', '>', '&', '_', '!', '\\', '|', '~', '`']]

    us_vcode = [2 + (0 << 3), 3 + (3 << 3), 3 + (1 << 3), 4 + (6 << 3), 0,
    #           5,            6,            7,            8, 9, 10
                4 + (4 << 3), 3 + (2 << 3), 4 + (8 << 3), 0, 0,  0,
    #           11,          12, 13,            14, 15
                4 + (7 << 3), 0,  4 + (5 << 3),  0,  5 + (9 << 3),
    #           16, 17, 18, 19, 20, 21, 22, 23
                0, 0, 0, 0, 0, 0, 0, 0,
    #           24, 25, 26, 27, 28, 29, 30, 31
                0, 0, 0, 0, 0, 0, 0, 5 + (10 << 3) ]
    #           0,            1,            2, 3,            4, 5, 6, 7,
    us_hcode  = [1 + (1 << 3), 2 + (0 << 3), 0, 3 + (2 << 3), 0, 0, 0, 5 + (3 << 3),
    #            8, 9, 10, 11, 12, 13, 14, 15,
                0, 0, 0, 0, 0, 0, 0, 5 + (5 << 3),
    #            16, 17, 18, 19, 20, 21, 22, 23
                0, 0, 0, 0, 0, 0, 0, 5 + (4 << 3),
    #            24, 25, 26, 27, 28, 29, 30, 31
                0, 0, 0, 0, 0, 0, 0, 5 + (6 << 3) ]
    # pylint: enable=bad-continuation,bad-whitespace

    ESCAPE_MARKER = 0x2A

    TERM_CODE = 0x37C0
    # TERM_CODE_LEN = 10
    DICT_CODE = 0x0000
    DICT_CODE_LEN = 5
    #DICT_OTHER_CODE = 0x0000
    #DICT_OTHER_CODE_LEN = 6
    RPT_CODE_TASMOTA = 0x3780
    RPT_CODE_TASMOTA_LEN = 10
    BACK2_STATE1_CODE = 0x2000
    BACK2_STATE1_CODE_LEN = 4
    #BACK_FROM_UNI_CODE = 0xFE00
    #BACK_FROM_UNI_CODE_LEN = 8
    LF_CODE = 0x3700
    LF_CODE_LEN = 9
    TAB_CODE = 0x2400
    TAB_CODE_LEN = 7
    ALL_UPPER_CODE = 0x2200
    ALL_UPPER_CODE_LEN = 8
    SW2_STATE2_CODE = 0x3800
    SW2_STATE2_CODE_LEN = 7
    ST2_SPC_CODE = 0x3B80
    ST2_SPC_CODE_LEN = 11
    BIN_CODE_TASMOTA = 0x8000
    BIN_CODE_TASMOTA_LEN = 3

    NICE_LEN = 5

    mask = [0x80, 0xC0, 0xE0, 0xF0, 0xF8, 0xFC, 0xFE, 0xFF]

    # pylint: disable=missing-function-docstring,invalid-name

    # Input
    # out = bytearray
    def append_bits(self, out, ol, code, clen, state):
        #print("Append bits {ol} {code} {clen} {state}".format(ol=ol, code=code, clen=clen, state=state))
        if state == self.SHX_STATE_2:
            # remove change state prefix
            if (code >> 9) == 0x1C:
                code <<= 7
                clen -= 7
        while clen > 0:
            cur_bit = ol % 8
            blen = 8 if (clen > 8) else clen
            a_byte = (code >> 8) & self.mask[blen - 1]
            #print("append_bits a_byte {ab} blen {blen}".format(ab=a_byte,blen=blen))
            a_byte >>= cur_bit
            if blen + cur_bit > 8:
                blen = (8 - cur_bit)
            if cur_bit == 0:
                out[ol // 8] = a_byte
            else:
                out[ol // 8] |= a_byte
            code <<= blen
            ol += blen
            if 0 == ol % 8:     # pylint: disable=misplaced-comparison-constant
                # we completed a full byte
                last_c = out[(ol // 8) - 1]
                if last_c in (0, self.ESCAPE_MARKER):
                    out[ol // 8] = 1 + last_c           # increment to 0x01 or 0x2B
                    out[(ol // 8) -1] = self.ESCAPE_MARKER   # replace old value with marker
                    ol += 8   # add one full byte
            clen -= blen
        return ol

    codes   = [0x82, 0xC3, 0xE5, 0xED, 0xF5]    # pylint: disable=bad-whitespace
    bit_len = [   5,    7,    9,   12,   16]    # pylint: disable=bad-whitespace

    def encodeCount(self, out, ol, count):
        #print("encodeCount ol = {ol}, count = {count}".format(ol=ol, count=count))
        till = 0
        base = 0
        for i in range(len(self.bit_len)):
            bit_len_i = self.bit_len[i]
            till += (1 << bit_len_i)
            if count < till:
                codes_i = self.codes[i]
                ol = self.append_bits(out, ol, (codes_i & 0xF8) << 8, codes_i & 0x07, 1)
                #print("encodeCount append_bits ol = {ol}, code = {code}, len = {len}".format(ol=ol,code=(codes_i & 0xF8) << 8,len=codes_i & 0x07))
                ol = self.append_bits(out, ol, (count - base) << (16 - bit_len_i), bit_len_i, 1)
                #print("encodeCount append_bits ol = {ol}, code = {code}, len = {len}".format(ol=ol,code=(count - base) << (16 - bit_len_i),len=bit_len_i))
                return ol
            base = till
        return ol

    # Returns (int, ol, state, is_all_upper)
    def matchOccurance(self, inn, len_, l_, out, ol, state, is_all_upper):
        # int j, k;
        longest_dist = 0
        longest_len = 0
        #for (j = l_ - self.NICE_LEN; j >= 0; j--) {
        j = l_ - self.NICE_LEN
        while j >= 0:
            k = l_
            #for (k = l_; k < len && j + k - l_ < l_; k++) {
            while k < len_ and j + k - l_ < l_:
                if inn[k] != inn[j + k - l_]:
                    break
                k += 1
            if k - l_ > self.NICE_LEN - 1:
                match_len = k - l_ - self.NICE_LEN
                match_dist = l_ - j - self.NICE_LEN + 1
                if match_len > longest_len:
                    longest_len = match_len
                    longest_dist = match_dist
            j -= 1

        if longest_len:
            #print("longest_len {ll}".format(ll=longest_len))
            #ol_save = ol
            if state == self.SHX_STATE_2 or is_all_upper:
                is_all_upper = 0
                state = self.SHX_STATE_1
                ol = self.append_bits(out, ol, self.BACK2_STATE1_CODE, self.BACK2_STATE1_CODE_LEN, state)

            ol = self.append_bits(out, ol, self.DICT_CODE, self.DICT_CODE_LEN, 1)
            ol = self.encodeCount(out, ol, longest_len)
            ol = self.encodeCount(out, ol, longest_dist)
            #print("longest_len {ll} longest_dist {ld} ol {ols}-{ol}".format(ll=longest_len, ld=longest_dist, ol=ol, ols=ol_save))
            l_ += longest_len + self.NICE_LEN
            l_ -= 1

            return l_, ol, state, is_all_upper
        return -l_, ol, state, is_all_upper


    def compress(self, inn, len_, out, len_out):
        ol = 0
        state = self.SHX_STATE_1
        is_all_upper = 0
        l = 0
        while l < len_:
        # for (l=0; l<len_; l++) {

            c_in = inn[l]

            if l and l < len_ - 4:
                if c_in == inn[l - 1] and c_in == inn[l + 1] and c_in == inn[l + 2] and c_in == inn[l + 3]:
                    rpt_count = l + 4
                    while rpt_count < len_ and inn[rpt_count] == c_in:
                        rpt_count += 1
                    rpt_count -= l

                    if state == self.SHX_STATE_2 or is_all_upper:
                        is_all_upper = 0
                        state = self.SHX_STATE_1
                        ol = self.append_bits(out, ol, self.BACK2_STATE1_CODE, self.BACK2_STATE1_CODE_LEN, state) # back to lower case and Set1

                    ol = self.append_bits(out, ol, self.RPT_CODE_TASMOTA, self.RPT_CODE_TASMOTA_LEN, 1)     # reusing CRLF for RPT
                    ol = self.encodeCount(out, ol, rpt_count - 4)
                    l += rpt_count
                    #l -= 1
                    continue

            if l < (len_ - self.NICE_LEN + 1):
                #l_old = l
                (l, ol, state, is_all_upper) = self.matchOccurance(inn, len_, l, out, ol, state, is_all_upper)
                if l > 0:
                    #print("matchOccurance l = {l} l_old = {lo}".format(l=l,lo=l_old))
                    l += 1    # for loop
                    continue

                l = -l

            if state == self.SHX_STATE_2:      # if Set2
                if ord(' ') <= c_in <= ord('@') or ord('[') <= c_in <= ord('`') or ord('{') <= c_in <= ord('~'):
                    pass
                else:
                    state = self.SHX_STATE_1        # back to Set1 and lower case
                    ol = self.append_bits(out, ol, self.BACK2_STATE1_CODE, self.BACK2_STATE1_CODE_LEN, state)

            is_upper = 0
            if ord('A') <= c_in <= ord('Z'):
                is_upper = 1
            else:
                if is_all_upper:
                    is_all_upper = 0
                    ol = self.append_bits(out, ol, self.BACK2_STATE1_CODE, self.BACK2_STATE1_CODE_LEN, state)

            if 32 <= c_in <= 126:
                if is_upper and not is_all_upper:
                    ll = l+5
                    # for (ll=l+5; ll>=l && ll<len_; ll--) {
                    while l <= ll < len_:
                        if inn[ll] < ord('A') or inn[ll] > ord('Z'):
                            break

                        ll -= 1

                    if ll == l-1:
                        ol = self.append_bits(out, ol, self.ALL_UPPER_CODE, self.ALL_UPPER_CODE_LEN, state)   # CapsLock
                        is_all_upper = 1

                if state == self.SHX_STATE_1 and ord('0') <= c_in <= ord('9'):
                    ol = self.append_bits(out, ol, self.SW2_STATE2_CODE, self.SW2_STATE2_CODE_LEN, state)   # Switch to sticky Set2
                    state = self.SHX_STATE_2

                c_in -= 32
                if is_all_upper and is_upper:
                    c_in += 32
                if c_in == 0 and state == self.SHX_STATE_2:
                    ol = self.append_bits(out, ol, self.ST2_SPC_CODE, self.ST2_SPC_CODE_LEN, state)       # space from Set2 ionstead of Set1
                else:
                    # ol = self.append_bits(out, ol, pgm_read_word(&c_95[c_in]), pgm_read_byte(&l_95[c_in]), state);  // original version with c/l in split arrays
                    cl = self.cl_95[c_in]
                    cl_code = cl & 0xFFF0
                    cl_len = cl & 0x000F
                    if cl_len == 13:
                        cl_code = cl_code >> 1
                    ol = self.append_bits(out, ol, cl_code, cl_len, state)

            elif c_in == 10:
                ol = self.append_bits(out, ol, self.LF_CODE, self.LF_CODE_LEN, state)         # LF
            elif c_in == '\t':
                ol = self.append_bits(out, ol, self.TAB_CODE, self.TAB_CODE_LEN, state)       # TAB
            else:
                ol = self.append_bits(out, ol, self.BIN_CODE_TASMOTA, self.BIN_CODE_TASMOTA_LEN, state)       # Binary, we reuse the Unicode marker which 3 bits instead of 9
                ol = self.encodeCount(out, ol, (255 - c_in) & 0xFF)


            # check that we have some headroom in the output buffer
            if ol // 8 >= len_out - 4:
                return -1      # we risk overflow and crash

            l += 1

        bits = ol % 8
        if bits:
            ol = self.append_bits(out, ol, self.TERM_CODE, 8 - bits, 1)   # 0011 0111 1100 0000 TERM = 0011 0111 11
        return (ol + 7) // 8
        # return ol // 8 + 1 if (ol%8) else 0


    def getBitVal(self, inn, bit_no, count):
        c_in = inn[bit_no >> 3]
        if bit_no >> 3 and self.ESCAPE_MARKER == inn[(bit_no >> 3) - 1]:
            c_in -= 1
        r = 1 << count if (c_in & (0x80 >> (bit_no % 8))) else 0
        #print("getBitVal r={r}".format(r=r))
        return r

    # Returns:
    # 0..11
    # or -1 if end of stream
    def getCodeIdx(self, code_type, inn, len_, bit_no_p):
        code = 0
        count = 0
        while count < 5:
            if bit_no_p >= len_:
                return -1, bit_no_p
            # detect marker
            if self.ESCAPE_MARKER == inn[bit_no_p >> 3]:
                bit_no_p += 8      # skip marker

            if bit_no_p >= len_:
                return -1, bit_no_p

            code += self.getBitVal(inn, bit_no_p, count)
            bit_no_p += 1
            count += 1
            code_type_code = code_type[code]
            if code_type_code and (code_type_code & 0x07) == count:
                #print("getCodeIdx = {r}".format(r=code_type_code >> 3))
                return code_type_code >> 3, bit_no_p

        #print("getCodeIdx  not found = {r}".format(r=1))
        return 1, bit_no_p

    def getNumFromBits(self, inn, bit_no_p, count):
        ret = 0
        while count:
            count -= 1
            if self.ESCAPE_MARKER == inn[bit_no_p >> 3]:
                bit_no_p += 8      # skip marker
            ret += self.getBitVal(inn, bit_no_p, count)
            bit_no_p += 1
        # print("getNumFromBits = {r}".format(r=ret))
        return ret, bit_no_p

    def readCount(self, inn, bit_no_p, len_):
        (idx, bit_no_p) = self.getCodeIdx(self.us_hcode, inn, len_, bit_no_p)
        if idx >= 1:
            idx -= 1    # we skip v = 1 (code '0') since we no more accept 2 bits encoding
        if idx >= 5 or idx < 0:
            return 0, bit_no_p  # unsupported or end of stream
        till = 0
        bit_len_idx = 0
        base = 0
        #for (uint32_t i = 0; i <= idx; i++) {
        i = 0
        while i <= idx:
        # for i in range(idx):
            base = till
            bit_len_idx = self.bit_len[i]
            till += (1 << bit_len_idx)
            i += 1

        (count, bit_no_p) = self.getNumFromBits(inn, bit_no_p, bit_len_idx)
        count = count + base
        #print("readCount getNumFromBits = {count} ({bl})".format(count=count,bl=bit_len_idx))

        return count, bit_no_p

    def decodeRepeat(self, inn, len_, out, ol, bit_no):
        #print("decodeRepeat Enter")
        (dict_len, bit_no) = self.readCount(inn, bit_no, len_)
        dict_len += self.NICE_LEN
        (dist, bit_no) = self.readCount(inn, bit_no, len_)
        dist += self.NICE_LEN - 1
        #memcpy(out + ol, out + ol - dist, dict_len);
        i = 0
        while i < dict_len:
        #for i in range(dict_len):
            out[ol + i] = out[ol - dist + i]
            i += 1
        ol += dict_len

        return ol, bit_no

    def decompress(self, inn, len_, out, len_out):
        ol = 0
        bit_no = 0
        dstate = self.SHX_SET1
        is_all_upper = 0

        len_ <<= 3    # *8, len_ in bits
        out[ol] = 0
        while bit_no < len_:
            c = 0
            is_upper = is_all_upper
            (v, bit_no) = self.getCodeIdx(self.us_vcode, inn, len_, bit_no)    # read vCode
            #print("bit_no {b}. v = {v}".format(b=bit_no,v=v))
            if v < 0:
                break     # end of stream
            h = dstate     # Set1 or Set2
            if v == 0:    # Switch which is common to Set1 and Set2, first entry
                (h, bit_no) = self.getCodeIdx(self.us_hcode, inn, len_, bit_no)    # read hCode
                #print("bit_no {b}. h = {h}".format(b=bit_no,h=h))
                if h < 0:
                    break     # end of stream
                if h == self.SHX_SET1:          # target is Set1
                    if dstate == self.SHX_SET1:   # Switch from Set1 to Set1 us UpperCase
                        if is_all_upper:      # if CapsLock, then back to LowerCase
                            is_upper = 0
                            is_all_upper = 0
                            continue

                        (v, bit_no) = self.getCodeIdx(self.us_vcode, inn, len_, bit_no)   # read again vCode
                        if v < 0:
                            break     # end of stream
                        if v == 0:
                            (h, bit_no) = self.getCodeIdx(self.us_hcode, inn, len_, bit_no)  # read second hCode
                            if h < 0:
                                break      # end of stream
                            if h == self.SHX_SET1:  # If double Switch Set1, the CapsLock
                                is_all_upper = 1
                                continue

                        is_upper = 1      # anyways, still uppercase
                    else:
                        dstate = self.SHX_SET1  # if Set was not Set1, switch to Set1
                        continue

                elif h == self.SHX_SET2:    # If Set2, switch dstate to Set2
                    if dstate == self.SHX_SET1:
                        dstate = self.SHX_SET2
                    continue

                if h != self.SHX_SET1:    # all other Sets (why not else)
                    (v, bit_no) = self.getCodeIdx(self.us_vcode, inn, len_, bit_no)    # we changed set, now read vCode for char
                    if v < 0:
                        break      # end of stream

            if v == 0 and h == self.SHX_SET1A:
                #print("v = 0, h = self.SHX_SET1A")
                if is_upper:
                    (temp, bit_no) = self.readCount(inn, bit_no, len_)
                    out[ol] = 255 - temp    # binary
                    ol += 1
                else:
                    (ol, bit_no) = self.decodeRepeat(inn, len_, out, ol, bit_no)   # dist
                continue

            if h == self.SHX_SET1 and v == 3:
                # was Unicode, will do Binary instead
                (temp, bit_no) = self.readCount(inn, bit_no, len_)
                out[ol] = 255 - temp    # binary
                ol += 1
                continue

            if h < 7 and v < 11:
                #print("h {h} v {v}".format(h=h,v=v))
                c = ord(self.sets[h][v])
            if ord('a') <= c <= ord('z'):
                if is_upper:
                    c -= 32       # go to UpperCase for letters
            else:          # handle all other cases
                if is_upper and dstate == self.SHX_SET1 and v == 1:
                    c = ord('\t')     # If UpperCase Space, change to TAB
                if h == self.SHX_SET1B:
                    if 8 == v:   # was LF or RPT, now only LF   # pylint: disable=misplaced-comparison-constant
                        out[ol] = ord('\n')
                        ol += 1
                        continue

                    if 9 == v:           # was CRLF, now RPT    # pylint: disable=misplaced-comparison-constant
                        (count, bit_no) = self.readCount(inn, bit_no, len_)
                        count += 4
                        if ol + count >= len_out:
                            return -1        # overflow

                        rpt_c = out[ol - 1]
                        while count:
                            count -= 1
                            out[ol] = rpt_c
                            ol += 1
                        continue

                    if 10 == v:         # pylint: disable=misplaced-comparison-constant
                        break           # TERM, stop decoding

            out[ol] = c
            ol += 1

            if ol >= len_out:
                return -1         # overflow

        return ol

    # pylint: enable=missing-function-docstring

def get_jsonstr(configmapping, jsonsort, jsonindent, jsoncompact):
    """
    Get JSON string output from config mapping

    @param configmapping:
        binary config data (decrypted)
    @param jsonsort:
        True: output of dictionaries will be sorted by key
        Uppercase and lowercase main keys remain unaffected
    @param jsonindent:
        pretty-printed JSON output indent level (<0 disables indent)
    @param jsoncompact:
        True: output of dictionaries will be compacted (no space after , and :)

    @return:
        template sizes as list []
    """
    conv_keys = {}
    for key in list(configmapping):
        if key[0].isupper():
            conv_keys[key] = key.lower()
            configmapping[conv_keys[key]] = configmapping.pop(key)
    json_output = json.dumps(
        configmapping,
        ensure_ascii=False,
        sort_keys=jsonsort,
        indent=None if (jsonindent is None or ARGS.jsonindent < 0) else jsonindent,
        separators=(',', ':') if jsoncompact else (', ', ': ')
        )
    for str_ in conv_keys:
        json_output = json_output.replace('"'+conv_keys[str_]+'"', '"'+str_+'"')

    return json_output

def get_templatesizes():
    """
    Get all possible template sizes as list

    @return:
        template sizes as list []
    """
    sizes = []
    for cfg in SETTINGS:
        sizes.append(cfg[1])
    # return unique sizes only (remove duplicates)
    return list(set(sizes))

def get_config_info(decode_cfg):
    """
    Extract info about loaded config

    @param decode_cfg:
        binary config data (decrypted)

    @return: dict
        hardware         int  config data hardware
        version          int  config data version
        template_version int  template version number
        template_size    int  config data size
        template         dict template dict (from SETTINGS)
    """
    version = 0x0
    size = setting = None
    version = get_field(decode_cfg, HARDWARE.ESP, 'version', SETTING_6_2_1['version'], raw=True, ignoregroup=True)
    template_version = version

    # identify hardware (config_version)
    config_version = HARDWARE.config_versions.index(HARDWARE.ESP82)  # default legacy
    for cfg in sorted(SETTINGS, key=lambda s: s[0], reverse=True):
        if version >= cfg[0]:
            fielddef = cfg[2].get('config_version', None)
            if fielddef is not None:
                config_version = get_field(decode_cfg, HARDWARE.ESP, 'config_version', fielddef, raw=True, ignoregroup=True)
                if config_version >= len(HARDWARE.config_versions):
                    exit_(ExitCode.INVALID_DATA, "Invalid data in config (config_version is {}, valid range [0,{}])".format(config_version, len(HARDWARE.STR)-1), type_=LogType.WARNING, line=inspect.getlineno(inspect.currentframe()))
                    config_version = HARDWARE.config_versions.index(HARDWARE.ESP82)
            break
    # search setting definition for hardware top-down
    for cfg in sorted(SETTINGS, key=lambda s: s[0], reverse=True):
        if version >= cfg[0]:
            template_version = cfg[0]
            size = cfg[1]
            setting = cfg[2]
            break

    if setting is None:
        exit_(ExitCode.UNSUPPORTED_VERSION, "Tasmota configuration version v{} not supported".format(get_versionstr(version)), line=inspect.getlineno(inspect.currentframe()))

    return {
        'hardware': config_version,
        'version': version,
        'template_version': template_version,
        'template_size': size,
        'template': setting
        }

def get_grouplist(setting):
    """
    Get all avilable group definition from setting

    @return:
        configargparse.parse_args() result
    """
    groups = set()

    for name in setting:
        if name != SETTINGVAR:
            dev = setting[name]
            format_, group = get_fielddef(dev, fields="format_, group")
            if group is not None and len(group) > 0:
                groups.add(group.title())
            if isinstance(format_, dict):
                subgroups = get_grouplist(format_)
                if subgroups is not None and len(subgroups) > 0:
                    for group in subgroups:
                        groups.add(group.title())

    groups = list(groups)
    groups.sort()
    return groups

class FileType:
    """
    File type returns
    """
    FILE_NOT_FOUND = None
    DMP = 'dmp'
    JSON = 'json'
    BIN = 'bin'
    UNKNOWN = 'unknown'
    INCOMPLETE_JSON = 'incomplete json'
    INVALID_JSON = 'invalid json'
    INVALID_BIN = 'invalid bin'

def get_filetype(filename):
    """
    Get the FileType class member of a given filename

    @param filename:
        filename of the file to analyse

    @return:
        FileType class member
    """
    filetype = FileType.UNKNOWN

    # try filename
    try:
        with open(filename, "r") as file:
            try:
                # try reading as json
                json.load(file)
                filetype = FileType.JSON
            except ValueError:
                filetype = FileType.INVALID_JSON
                # not a valid json, get filesize and compare it with all possible sizes
                try:
                    size = os.path.getsize(filename)
                except:     # pylint: disable=bare-except
                    filetype = FileType.UNKNOWN

                header_format = '<L'
                sizes = get_templatesizes()
                # size is one of a dmp file size
                if size in sizes:
                    filetype = FileType.DMP
                elif size - struct.calcsize(header_format) in sizes:
                    # check if the binary file has the magic header
                    with open(filename, "rb") as inputfile:
                        inputbin = inputfile.read()
                    if BINARYFILE_MAGIC in (struct.unpack_from(header_format, inputbin, 0)[0],
                                            struct.unpack_from(header_format, inputbin, len(inputbin)-struct.calcsize(header_format))[0]):
                        filetype = FileType.BIN
                    else:
                        filetype = FileType.INVALID_BIN

    except:     # pylint: disable=bare-except
        filetype = FileType.FILE_NOT_FOUND

    return filetype

def get_versionstr(version):
    """
    Create human readable version string

    @param version:
        version integer

    @return:
        version string
    """
    if isinstance(version, str):
        version = int(version, 0)
    major = ((version>>24) & 0xff)
    minor = ((version>>16) & 0xff)
    release = ((version>> 8) & 0xff)
    subrelease = (version & 0xff)
    if major >= 6:
        if subrelease > 0:
            subreleasestr = str(subrelease)
        else:
            subreleasestr = ''
    else:
        if subrelease > 0:
            subreleasestr = str(chr(subrelease+ord('a')-1))
        else:
            subreleasestr = ''
    return "{:d}.{:d}.{:d}{}{}".format(major, minor, release, '.' if (major >= 6 and subreleasestr != '') else '', subreleasestr)

def make_filename(filename, filetype, configmapping):
    """
    Replace variables within a filename

    @param filename:
        original filename possible containing replacements:
        @v:
            Tasmota version from config data
        @f:
            friendlyname from config data
        @d:
            devicename from config data
        @h:
            hostname from config data
        @H:
            hostname from device (http source only)
        @F:
            configuration filename from MQTT request (mqtt source only)
    @param filetype:
        FileType.x object - creates extension if not None
    @param configmapping:
        binary config data (decrypted)

    @return:
        New filename with replacements
    """
    config_version = config_friendlyname = config_hostname = device_hostname = filesource = ''

    try:
        config_version = configmapping['header']['data']['version']['id']
    except:     # pylint: disable=bare-except
        config_version = configmapping.get('version', '')
    if config_version != '':
        config_version = get_versionstr(int(str(config_version), 0))
    config_friendlyname = configmapping.get('friendlyname', '')
    if config_friendlyname != '':
        config_friendlyname = re.sub('_{2,}', '_', "".join(itertools.islice((c for c in str(config_friendlyname[0]) if c.isprintable()), 256))).replace(' ', '_')
    config_devicename = configmapping.get('devicename', '')
    if config_devicename != '':
        config_devicename = re.sub('_{2,}', '_', "".join(itertools.islice((c for c in str(config_devicename) if c.isprintable()), 256))).replace(' ', '_')
    config_hostname = configmapping.get('hostname', '')
    if config_hostname != '':
        if str(config_hostname).find('%') < 0:
            config_hostname = re.sub('_{2,}', '_', re.sub('[^0-9a-zA-Z]', '_', str(config_hostname)).strip('_'))
    if filename.find('@H') >= 0 and ARGS.httpsource is not None:
        _, http_host, http_port, http_username, http_password = get_http_parts()
        device_hostname = get_tasmotahostname(http_host, http_port, username=http_username, password=http_password)
        if device_hostname is None:
            device_hostname = ''
    if filename.find('@F') >= 0 and ARGS.mqttsource is not None and ARGS.filesource is not None:
        filesource = ARGS.filesource.strip().rstrip('.dmp')

    dirname = basename = ext = ''

    # split file parts
    dirname = os.path.normpath(os.path.dirname(filename))
    basename = os.path.basename(filename)
    name, ext = os.path.splitext(basename)

    # make a valid filename
    try:
        name = name.translate(dict((ord(char), None) for char in r'\/*?:"<>|'))
    except:     # pylint: disable=bare-except
        pass
    name = name.replace(' ', '_')

    # append extension based on filetype if not given
    if len(ext) != 0 and ext[0] == '.':
        ext = ext[1:]
    if filetype is not None and ARGS.extension and (len(ext) < 2 or all(c.isdigit() for c in ext)):
        ext = filetype.lower()

    # join filename + extension
    if len(ext) != 0:
        name_ext = name+'.'+ext
    else:
        name_ext = name

    # join path and filename
    try:
        filename = os.path.join(dirname, name_ext)
    except:     # pylint: disable=bare-except
        pass

    filename = filename.replace('@v', config_version)
    filename = filename.replace('@d', config_devicename)
    filename = filename.replace('@f', config_friendlyname)
    filename = filename.replace('@h', config_hostname)
    filename = filename.replace('@H', device_hostname)
    filename = filename.replace('@F', filesource)

    return filename

def make_url(host, port=80, location=''):
    """
    Create a Tasmota host url

    @param host:
        hostname or IP of Tasmota host
    @param port:
        port number to use for http connection
    @param location:
        http url location

    @return:
        Tasmota http url
    """
    return "http://{shost}{sdelimiter}{sport}/{slocation}".format(\
            shost=host,
            sdelimiter=':' if port != 80 else '',
            sport=port if port != 80 else '',
            slocation=location)

def get_http_parts():
    """
    Get http connection parameter parts from url/hostnme/ip and optional arguments

    @return
        http_host, http_port, http_username, http_password
    """
    http_scheme = 'http'
    http_host = ARGS.httpsource
    http_port = ARGS.port
    http_username = ARGS.username
    http_password = ARGS.password
    try:
        URLPARSE = urllib.parse.urlparse(urllib.parse.quote(ARGS.httpsource, safe='/:@'))
        if URLPARSE.netloc:
            if URLPARSE.scheme is not None:
                http_scheme = URLPARSE.scheme
            if URLPARSE.hostname is not None:
                http_host = urllib.parse.unquote(URLPARSE.hostname)
            if URLPARSE.port is not None:
                http_port = URLPARSE.port
            if URLPARSE.username is not None:
                http_username = urllib.parse.unquote(URLPARSE.username)
            if URLPARSE.password is not None:
                http_password = urllib.parse.unquote(URLPARSE.password)
    except:     # pylint: disable=bare-except
        pass
    if not SSL_MODULE:
        exit_(ExitCode.MODULE_NOT_FOUND,
            "Missing python SSL module - HTTP scheme '{}' not possible, use http instead".format(http_scheme),
            type_=LogType.WARNING,
            doexit=not ARGS.ignorewarning,
            line=inspect.getlineno(inspect.currentframe()))
        ARGS.httpsource = ARGS.httpsource.replace('https', 'http')
        http_scheme = 'http'
    if http_port is None:
        try:
            http_port = DEFAULT_PORT_HTTPS if http_scheme[-1] == 's' else DEFAULT_PORT_HTTP
        except:     # pylint: disable=bare-except
            http_port = DEFAULT_PORT_HTTP

    return http_scheme, http_host, http_port, http_username, http_password

def get_mqtt_parts():
    """
    Get mqtt connection parameter parts from url/hostnme/ip and optional arguments

    @return
        mqtt_host, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, http_password
    """
    mqtt_scheme = 'mqtt'
    mqtt_host = ARGS.mqttsource
    mqtt_port = ARGS.port
    mqtt_topic =  ARGS.fulltopic
    mqtt_username = ARGS.username
    mqtt_password = ARGS.password
    http_password = ARGS.password
    try:
        URLPARSE = urllib.parse.urlparse(urllib.parse.quote(ARGS.mqttsource, safe='/:@'))
        if URLPARSE.netloc:
            if URLPARSE.scheme is not None:
                mqtt_scheme = URLPARSE.scheme
            if URLPARSE.hostname is not None:
                mqtt_host = urllib.parse.unquote(URLPARSE.hostname)
            if URLPARSE.port is not None:
                mqtt_port = URLPARSE.port
            if URLPARSE.path is not None:
                mqtt_topic = urllib.parse.unquote(URLPARSE.path)[1:]
            if URLPARSE.username is not None:
                mqtt_username = urllib.parse.unquote(URLPARSE.username)
            if URLPARSE.password is not None:
                mqtt_password = urllib.parse.unquote(URLPARSE.password)
                if ARGS.password is None:
                    http_password = mqtt_password
    except:     # pylint: disable=bare-except
        pass
    if not SSL_MODULE and len(mqtt_scheme) and mqtt_scheme[-1] == 's':
        exit_(ExitCode.MODULE_NOT_FOUND,
            "Missing python SSL module - MQTT scheme '{}' not possible, use mqtt instead".format(mqtt_scheme),
            type_=LogType.WARNING,
            doexit=not ARGS.ignorewarning,
            line=inspect.getlineno(inspect.currentframe()))
        ARGS.mqttsource = ARGS.mqttsource.replace('mqtts', 'mqtt')
        mqtt_scheme = 'mqtt'
    if mqtt_port is None:
        try:
            mqtt_port = DEFAULT_PORT_MQTTS if mqtt_scheme[-1] == 's' else DEFAULT_PORT_MQTT
        except:     # pylint: disable=bare-except
            mqtt_port = DEFAULT_PORT_MQTT
    return mqtt_scheme, mqtt_host, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, http_password

def load_tasmotaconfig(filename):
    """
    Load config from Tasmota file

    @param filename:
        filename to load

    @return:
        binary config data (encrypted) or None on error
    """
    encode_cfg = None

    # read config from a file
    if not os.path.isfile(filename):    # check file exists
        exit_(ExitCode.FILE_NOT_FOUND, "File '{}' not found".format(filename), line=inspect.getlineno(inspect.currentframe()))

    if ARGS.verbose or ((ARGS.backupfile is not None or ARGS.restorefile is not None) and not ARGS.output):
        message("Load data from file '{}'".format(ARGS.filesource), type_=LogType.INFO if ARGS.verbose else None)
    try:
        with open(filename, "rb") as tasmotafile:
            encode_cfg = tasmotafile.read()
    except Exception as err:    # pylint: disable=broad-except
        exit_(ExitCode.INTERNAL_ERROR, "'{}' {}".format(filename, err), line=inspect.getlineno(inspect.currentframe()))

    return encode_cfg

def get_tasmotaconfig(cmnd, host, port, username=DEFAULTS['source']['username'], password=None, contenttype=None):
    """
    Tasmota http request

    @param host:
        hostname or IP of Tasmota device
    @param port:
        http port of Tasmota device
    @param username:
        optional username for Tasmota web login
    @param password
        optional password for Tasmota web login

    @return:
        binary config data (encrypted) or None on error
    """
    # read config direct from device via http
    url = make_url(host, port, cmnd)
    referer = make_url(host, port)
    auth = None
    if username is not None and password is not None:
        auth = (username, password)
    try:
        res = requests.get(url, auth=auth, headers={'referer': referer})
    except (requests.exceptions.ConnectionError, requests.exceptions.InvalidURL) as _:
        exit_(ExitCode.HTTP_CONNECTION_ERROR, "Failed to establish HTTP connection to '{}:{}'".format(host, port))

    if not res.ok:
        exit_(res.status_code, "Error on http GET request for {} - {}".format(url, res.reason), line=inspect.getlineno(inspect.currentframe()))

    if contenttype is not None and res.headers['Content-Type'] != contenttype:
        exit_(ExitCode.DOWNLOAD_CONFIG_ERROR, "Device did not respond properly, maybe Tasmota webserver admin mode is disabled (WebServer 2)", line=inspect.getlineno(inspect.currentframe()))

    return res.status_code, res.content

def get_tasmotahostname(host, port, username=DEFAULTS['source']['username'], password=None):
    """
    Get Tasmota hostname from device

    @param host:
        hostname or IP of Tasmota device
    @param port:
        http port of Tasmota device
    @param username:
        optional username for Tasmota web login
    @param password
        optional password for Tasmota web login

    @return:
        Tasmota real hostname or None on error
    """
    hostname = None

    loginstr = ""
    if password is not None:
        loginstr = "user={}&password={}&".format(urllib.parse.quote(username), urllib.parse.quote(password))
    # get hostname
    _, body = get_tasmotaconfig("cm?{}cmnd=status%205".format(loginstr), host, port, username=username, password=password)
    if body is not None:
        jsonbody = json.loads(str(body, STR_CODING))
        statusnet = jsonbody.get('StatusNET', None)
        if statusnet is not None:
            hostname = statusnet.get('Hostname', None)
            if hostname is not None:
                if ARGS.verbose:
                    message("Hostname for '{}' retrieved: '{}'".format(host, hostname), type_=LogType.INFO)

    return hostname

def pull_http():
    """
    Download binary data to a Tasmota host using http

    @return:
        binary config data (encrypted) or None on error
    """
    _, http_host, http_port, http_username, http_password = get_http_parts()

    if ARGS.verbose or ((ARGS.backupfile is not None or ARGS.restorefile is not None) and not ARGS.output):
        message("Load data by http from device '{}'".format(http_host), type_=LogType.INFO if ARGS.verbose else None)

    _, body = get_tasmotaconfig('dl', http_host, http_port, http_username, http_password, contenttype='application/octet-stream')

    return body

def push_http(encode_cfg):
    """
    Upload binary data to a Tasmota host using http

    @param encode_cfg:
        encrypted binary data or filename containing Tasmota encrypted binary config

    @return
        errorcode, errorstring
        errorcode=0 if success, otherwise http response or exception code
    """
    if isinstance(encode_cfg, str):
        encode_cfg = bytearray(encode_cfg)

    _, http_host, http_port, http_username, http_password = get_http_parts()

    # get restore config page first to set internal Tasmota vars
    responsecode, body = get_tasmotaconfig('rs?', http_host, http_port, http_username, http_password, contenttype='text/html')
    if body is None:
        return responsecode, "ERROR"

    # ~ # post data
    url = make_url(http_host, http_port, "u2")
    auth = None
    if http_username is not None and http_password is not None:
        auth = (http_username, http_password)
    files = {'u2':('{sprog}_v{sver}.dmp'.format(sprog=os.path.basename(sys.argv[0]), sver=METADATA['VERSION_BUILD']), encode_cfg)}
    try:
        res = requests.post(url, auth=auth, files=files)
    except ConnectionError as err:
        exit_(ExitCode.UPLOAD_CONFIG_ERROR, "Error on http POST request for {} - {}".format(url, err), line=inspect.getlineno(inspect.currentframe()))

    if not res.ok:
        exit_(res.status_code, "Error on http POST request for {} - {}".format(url, res.reason), line=inspect.getlineno(inspect.currentframe()))

    if res.headers['Content-Type'] != 'text/html':
        exit_(ExitCode.UPLOAD_CONFIG_ERROR, "Device did not response properly, may be Tasmota webserver admin mode is disabled (WebServer 2)", line=inspect.getlineno(inspect.currentframe()))

    body = res.text

    find_upload = -1
    for key in ("Carga", "Caricamento", "Enviar", "Feltöltés", "Ladda upp", "Nahrání...", "Nahrávanie...", "Upload", "Verzenden", "Wgraj", "Yükleme", "Încărcăre", "Ανέβασμα", "Завантажити", "Загрузить", "Зареждане", "העלאה", "上传", "上傳", "업로드"):
        find_upload = body.find(key)
        if find_upload >= 0:
            break
    if find_upload < 0:
        return ExitCode.UPLOAD_CONFIG_ERROR, "Device did not response properly with upload result page"

    body = body[find_upload:]
    if sum(map(lambda s: body.find(s) >= 0, ("Başarıyla Tamamlandı", "Completato", "Exitosa", "Gelukt", "Lyckat", "Powodzenie", "Réussi", "Sikeres", "Successful", "Successo", "Succes", "erfolgreich", "úspešné.", "úspěšné.", "Επιτυχές", "Успешно", "Успішно", "הצליח", "已成功", "成功", "성공"))) < 1:
        errmatch = re.search(r"<font\s*color='[#0-9a-fA-F]+'>(\S*)</font></b><br><br>(.*)<br>", body)
        reason = "Unknown error"
        if errmatch and len(errmatch.groups()) > 1:
            reason = errmatch.group(2)
        return ExitCode.UPLOAD_CONFIG_ERROR, reason

    return 0, 'OK'

def mqtt_maketopic(mqtt_topic, prefix, cmnd):
    """
    Make command or stat topic from given topic

    @param topic
        topic given by user via mqtt(s):// or --fulltopic param
    @param iscmnd
        True if generate Tasmota command topic, otherwise stat topic
    @param isdownload
        True generate Tasmota command for download topic otherwise for upload

    @return:
        topic to use for MQTT transport
    """
    if prefix == 'stat':
        cmnd = cmnd.upper()
    else:
        cmnd = cmnd.lower()
    return re.sub(r'\bstat\b|\btele\b|\bcmnd\b|\%prefix\%', prefix, mqtt_topic).rstrip('/')+"/"+cmnd

def pull_mqtt(use_base64=True):
    """
    Download binary data from a Tasmota host using mqtt

    @param use_base64
        optional True if using base64 data transfer, otherwise binary data transfer

    @return:
        binary config data (encrypted) or None on error
    """
    mqtt_scheme, mqtt_host, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, tasmota_mqtt_password = get_mqtt_parts()

    if ARGS.verbose or ((ARGS.backupfile is not None or ARGS.restorefile is not None) and not ARGS.output):
        message("Load data by mqtt using '{}'".format(ARGS.mqttsource), type_=LogType.INFO if ARGS.verbose else None)

    cmnd = 'FILEDOWNLOAD'
    topic_publish = mqtt_maketopic(mqtt_topic, 'cmnd', cmnd)

    dobj = None

    ack_flag = False
    err_flag = False
    err_str = ""

    file_name = ""
    file_id = 0
    file_type = 0
    file_size = 0
    file_md5 = ""

    # The callback for when subscribe message is received
    def on_message(client, userdata, msg):
        nonlocal ack_flag
        nonlocal err_flag
        nonlocal err_str
        nonlocal file_name
        nonlocal file_id
        nonlocal file_type
        nonlocal file_size
        nonlocal file_md5
        nonlocal in_hash_md5
        nonlocal dobj

        base64_data = ""
        rcv_id = 0

        try:
            root = json.loads(msg.payload.decode("utf-8"))
            if root:
                if "FileDownload" in root:
                    rcv_code = root["FileDownload"]
                    if "Aborted" in rcv_code:
                        err_str ="Aborted"
                        err_flag = True
                        return
                    if "Started" in rcv_code:
                        return
                    if "Error" in rcv_code:
                        if "1" in rcv_code:
                            err_str ="Wrong password"
                        else:
                            if "2" in rcv_code:
                                err_str ="Bad chunk size"
                            else:
                                if "3" in rcv_code:
                                    err_str ="Invalid file type"
                                else:
                                    err_str ="Receive code "+rcv_code
                        err_flag = True
                        return
                if "Command" in root:
                    rcv_code = root["Command"]
                    if rcv_code == "Error":
                        err_str ="Command error"
                        err_flag = True
                        return
                if "File" in root:
                    file_name = root["File"]
                if "Id" in root:
                    rcv_id = root["Id"]
                if "Type" in root:
                    file_type = root["Type"]
                if "Size" in root:
                    file_size = root["Size"]
                if "Data" in root:
                    base64_data = root["Data"]
                if "Md5" in root:
                    file_md5 = root["Md5"]
        except:
            pass

        if dobj is None and rcv_id > 0 and file_size > 0 and file_type > 0 and file_name:
            file_id = rcv_id
            dobj = bytearray()
        else:
            if use_base64 and file_id > 0 and file_id != rcv_id:
                err_flag = True
                return

        if file_md5 == "" and file_name:
            if use_base64 and base64_data:
                base64_decoded_data = base64_data.encode('utf-8')
                chunk = base64.decodebytes(base64_decoded_data)
                in_hash_md5.update(chunk)    # Update hash
                dobj += chunk
            if not use_base64 and 0 == rcv_id:
                chunk = msg.payload
                in_hash_md5.update(chunk)    # Update hash
                dobj += chunk

        if file_md5 != "":
            md5_hash = in_hash_md5.hexdigest()
            if md5_hash != file_md5:
                err_str ="MD5 mismatch"
                err_flag = True

        ack_flag = False

    def wait_for_ack():
        nonlocal err_flag

        timeout = MQTT_TIMEOUT/10
        while ack_flag and not err_flag and timeout > 0:
            time.sleep(0.01)
            timeout = timeout -1

        if 0 == timeout:
            err_str ="Timeout"
            err_flag = True

        return ack_flag

    conn_rc = 0
    conn_flag = False
    def on_connect(client, userdata, flags, rc):
        nonlocal conn_rc
        nonlocal conn_flag

        conn_rc = rc
        conn_flag = True

    def wait_for_connect():
        nonlocal conn_flag

        timeout = 200
        while not conn_flag and timeout > 0:
            time.sleep(0.01)
            timeout = timeout -1

        return 0 != timeout


    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    if SSL_MODULE:
        # cafile and url scheme controls TLS usage
        try:
            tls = mqtt_scheme[-1] == 's'
        except:
            tls = False
        if tls or ARGS.cafile is not None:
            if ARGS.certfile is not None and ARGS.keyfile is not None:
                client.tls_set(ARGS.cafile,
                            certfile=ARGS.certfile,
                            keyfile=ARGS.keyfile,
                            cert_reqs=ssl.CERT_REQUIRED)
            else:
                client.tls_set(ARGS.cafile, cert_reqs=ssl.CERT_REQUIRED)
            client.tls_insecure_set(ARGS.insecure)
    if mqtt_username is not None and mqtt_password is not None:
        client.username_pw_set(mqtt_username, mqtt_password)
    try:
        client.connect(mqtt_host, mqtt_port, ARGS.keepalive)
    except Exception as err:    # pylint: disable=broad-except,unused-variable
        exit_(ExitCode.MQTT_CONNECTION_ERROR, "Failed to establish MQTT connection to '{}:{}: {}'".format(mqtt_host, mqtt_port, err.strerror))
    client.loop_start()                    # Start loop to process received messages
    if not wait_for_connect():
        exit_(ExitCode.MQTT_CONNECTION_ERROR, "Failed to establish MQTT connection to '{}:{}: Connection timeout'".format(mqtt_host, mqtt_port))
    elif conn_rc != mqtt.MQTT_ERR_SUCCESS:
        exit_(ExitCode.MQTT_CONNECTION_ERROR, "Failed to establish MQTT connection to '{}:{}: Code {} - {}'".format(mqtt_host, mqtt_port, conn_rc, mqtt.connack_string(conn_rc)))
    client.subscribe(mqtt_maketopic(mqtt_topic, 'stat', cmnd))

    in_hash_md5 = hashlib.md5()

    data = {"Password":tasmota_mqtt_password, "Type":MQTT_FILETYPE}
    if not use_base64:
        data["Binary"] = 1
    client.publish(topic_publish, json.dumps(data))

    ack_flag = True
    run_flag = True
    while run_flag:
        if wait_for_ack():                  # We use Ack here
            client.publish(topic_publish, "0")   # Abort any failed download
            run_flag = False
        else:
            if file_md5 == "":               # Request chunk
                client.publish(topic_publish, "?")
                ack_flag = True
            else:
                run_flag = False

    if not err_flag:
        file_type_name = "Data"
        if file_type == MQTT_FILETYPE:
            file_type_name = "Settings"
        ARGS.filesource = file_name
        if ARGS.verbose:
            message("{} downloaded by MQTT as {}".format(file_type_name, file_name), type_=LogType.INFO)
    else:
        exit_(ExitCode.DOWNLOAD_CONFIG_ERROR, "Error during MQTT data processing: {}".format(err_str), line=inspect.getlineno(inspect.currentframe()))

    client.disconnect()                    # Disconnect
    client.loop_stop()                     # Stop loop

    return dobj

def push_mqtt(encode_cfg, use_base64=True):
    """
    Upload binary data to a Tasmota host using mqtt

    @param encode_cfg:
        encrypted binary data or filename containing Tasmota encrypted binary config
    @param use_base64
        optional True if using base64 data transfer, otherwise binary data transfer

    @return
        errorcode, errorstring
        errorcode=0 if success, otherwise mqtt response or exception code
    """
    mqtt_scheme, mqtt_host, mqtt_port, mqtt_topic, mqtt_username, mqtt_password, tasmota_mqtt_password = get_mqtt_parts()

    cmnd = 'FILEUPLOAD'
    topic_publish = mqtt_maketopic(mqtt_topic, 'cmnd', cmnd)

    dobj = encode_cfg

    ack_flag = False
    err_flag = False
    err_str = ""

    file_id = int(time.time()*10000000 % 253) + 2   # id must be between 2 and 254
    file_chunk_size = MQTT_MESSAGE_MAX_SIZE         # Tasmota MQTT max message size

    # The callback for when subscribe message is received
    def on_message(client, userdata, msg):
        nonlocal ack_flag
        nonlocal err_flag
        nonlocal err_str
        nonlocal file_chunk_size
        nonlocal encode_cfg

        rcv_code = ""
        rcv_id = 0

        try:
            root = json.loads(msg.payload.decode("utf-8"))
            if root:
                if "FileUpload" in root:
                    rcv_code = root["FileUpload"]
                    if "Aborted" in rcv_code:
                        err_str ="Aborted"
                        err_flag = True
                        return
                    if "MD5 mismatch" in rcv_code:
                        err_str ="MD5 mismatch"
                        Err_flag = True
                        return
                    if "Started" in rcv_code:
                        return
                    if "Error" in rcv_code:
                        if "1" in rcv_code:
                            err_str ="Wrong password"
                        else:
                            if "2" in rcv_code:
                                err_str ="Bad chunk size"
                            else:
                                if "3" in rcv_code:
                                    err_str ="Invalid file type"
                                else:
                                    err_str ="Receive code "+rcv_code
                        err_flag = True
                        return
                if "Command" in root:
                    rcv_code = root["Command"]
                    if rcv_code == "Error":
                        err_str ="Command error"
                        err_flag = True
                        return
                if "Id" in root:
                    rcv_id = root["Id"]
                    if rcv_id == file_id:
                        if "MaxSize" in root:
                            file_chunk_size = root["MaxSize"]
        except:
            pass

        ack_flag = False

    def wait_for_ack():
        nonlocal err_flag

        timeout = MQTT_TIMEOUT/10
        while ack_flag and not err_flag and timeout > 0:
            time.sleep(0.01)
            timeout = timeout -1

        if 0 == timeout:
            err_str ="Timeout"
            err_flag = True

        return ack_flag

    conn_rc = 0
    conn_flag = False
    def on_connect(client, userdata, flags, rc):
        nonlocal conn_rc
        nonlocal conn_flag

        conn_rc = rc
        conn_flag = True

    def wait_for_connect():
        nonlocal conn_flag

        timeout = 200
        while not conn_flag and timeout > 0:
            time.sleep(0.01)
            timeout = timeout -1

        return 0 != timeout

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    if SSL_MODULE:
        # cafile and url scheme controls TLS usage
        try:
            tls = mqtt_scheme[-1] == 's'
        except:
            tls = False
        if tls or ARGS.cafile is not None:
            if ARGS.certfile is not None and ARGS.keyfile is not None:
                client.tls_set(ARGS.cafile,
                            certfile=ARGS.certfile,
                            keyfile=ARGS.keyfile,
                            cert_reqs=ssl.CERT_REQUIRED)
            else:
                client.tls_set(ARGS.cafile, cert_reqs=ssl.CERT_REQUIRED)
            client.tls_insecure_set(ARGS.insecure)
    if mqtt_username is not None and mqtt_password is not None:
        client.username_pw_set(mqtt_username, mqtt_password)
    try:
        client.connect(mqtt_host, mqtt_port, ARGS.keepalive)
    except Exception as err:    # pylint: disable=broad-except,unused-variable
        return ExitCode.MQTT_CONNECTION_ERROR, "MQTT connection: {}".format(err.strerror)
    client.loop_start()                    # Start loop to process received messages
    if not wait_for_connect():
        return ExitCode.MQTT_CONNECTION_ERROR, "MQTT connection: Connection timeout"
    elif conn_rc != mqtt.MQTT_ERR_SUCCESS:
        return ExitCode.MQTT_CONNECTION_ERROR, "MQTT connection: Code {} - {}'".format(conn_rc, mqtt.connack_string(conn_rc))
    client.subscribe(mqtt_maketopic(mqtt_topic, 'stat', cmnd))

    client.publish(topic_publish, json.dumps({"Password":tasmota_mqtt_password,
                                              "File":"decode-config.dmp",
                                              "Id":file_id,
                                              "Type":MQTT_FILETYPE,
                                              "Size":len(encode_cfg)
                                            }))

    out_hash_md5 = hashlib.md5()

    ack_flag = True
    run_flag = True
    while run_flag:
        if wait_for_ack():                  # We use Ack here
            client.publish(topic_publish, "0")   # Abort any failed upload
            run_flag = False
        chunk = dobj[:file_chunk_size]
        dobj = dobj[file_chunk_size:]
        if len(chunk):
            out_hash_md5.update(chunk)       # Update hash
            if use_base64:
                base64_encoded_data = base64.b64encode(chunk)
                base64_data = base64_encoded_data.decode('utf-8')
                client.publish(topic_publish, json.dumps({"Id":file_id,"Data":base64_data}))
            else:
                client.publish(topic_publish+"201", chunk)
            ack_flag = True

        else:
            md5_hash = out_hash_md5.hexdigest()
            client.publish(topic_publish, json.dumps({"Id":file_id,"Md5":md5_hash}))
            run_flag = False

    if not err_flag:
        if ARGS.verbose:
            message("Settings uploaded by MQTT", type_=LogType.INFO)
    else:
       return ExitCode.DOWNLOAD_CONFIG_ERROR, "MQTT data processing error: {}".format(err_str)

    client.disconnect()                    # Disconnect
    client.loop_stop()                     # Stop loop

    return ExitCode.OK, ""

def decrypt_encrypt(obj):
    """
    Decrpt/Encrypt binary config data

    @param obj:
        binary config data

    @return:
        decrypted configuration (if obj contains encrypted data)
    """
    if isinstance(obj, str):
        obj = bytearray(obj)
    dobj = bytearray(obj[0:2])
    for i in range(2, len(obj)):
        dobj.append((obj[i] ^ (CONFIG_FILE_XOR +i)) & 0xff)
    return dobj

def get_settingcrc(dobj):
    """
    Return binary config data calclulated crc

    @param dobj:
        decrypted binary config data

    @return:
        2 byte unsigned integer crc value
    """
    if isinstance(dobj, str):
        dobj = bytearray(dobj)

    crc = 0
    config_info = get_config_info(dobj)
    for i in range(0, config_info['template_size']):
        if not i in [14, 15]: # Skip crc
            byte_ = dobj[i]
            crc += byte_ * (i+1)

    return crc & 0xffff

def get_settingcrc32(dobj):
    """
    Return binary config data calclulated crc32

    @param dobj:
        decrypted binary config data

    @return:
        4 byte unsigned integer crc value
    """
    if isinstance(dobj, str):
        dobj = bytearray(dobj)
    crc = 0
    for i in range(0, len(dobj)-4):
        crc ^= dobj[i]
        for _ in range(0, 8):
            crc = (crc >> 1) ^ (-int(crc & 1) & 0xEDB88320)

    return ~crc & 0xffffffff

def bitsread(value, pos=0, bits=1):
    """
    Reads bit(s) of a number

    @param value:
        the number from which to read

    @param pos:
        which bit position to read

    @param bits:
        how many bits to read (1 if omitted)

    @return:
        the bit value(s)
    """
    if isinstance(value, str):
        value = int(value, 0)
    if isinstance(pos, str):
        pos = int(pos, 0)

    if pos >= 0:
        value >>= pos
    else:
        value <<= abs(pos)
    if bits > 0:
        value &= (1<<bits)-1
    return value

def get_strindex(hardware, strindex_name):
    """
    Get the hardware corresponding string index for variable strings

    @param hardware:
        platfrom id
    @param strindex_name:
        name of the index to find within string definition

    @return:
        index of the string or -1 on error
    """
    # hardware = get_fielddef(fielddef, fields='hardware')
    try:
        return CONFIG['info']['template'][SETTINGVAR][HARDWARE.hstr(hardware)].index(strindex_name)
    except:     # pylint: disable=bare-except
        return -1

def get_fielddef(fielddef, fields="hardware, format_, addrdef, baseaddr, bits, bitshift, strindex, datadef, arraydef, validate, cmd, group, tasmotacmnd, converter, readconverter, writeconverter"):
    """
    Get field definition items

    @param fielddef:
        field format - see "Settings dictionary" above
    @param fields:
        comma separated string list of values to be returned
        possible values see fields default

    @return:
        set of values defined in <fields>
    """
    hardware = format_ = addrdef = baseaddr = datadef = arraydef = validate = cmd = group = tasmotacmnd = converter = readconverter = writeconverter = strindex = None
    bits = bitshift = 0
    raise_error = '<fielddef> error'

    # calling with None is wrong
    if fielddef is None:
        print('<fielddef> is None', file=sys.stderr)
        raise SyntaxError(raise_error)

    # check global format
    if not isinstance(fielddef, (dict, tuple)):
        print('wrong <fielddef> in setting {}'.format(fielddef), file=sys.stderr)
        raise SyntaxError(raise_error)

    # get top level items
    if len(fielddef) == 4:
        # converter not present
        hardware, format_, addrdef, datadef = fielddef
    elif len(fielddef) == 5:
        # converter present
        hardware, format_, addrdef, datadef, converter = fielddef
    else:
        print('wrong <fielddef> {} length ({}) in setting'.format(fielddef, len(fielddef)), file=sys.stderr)
        raise SyntaxError(raise_error)

    # ignore calls with 'root' setting
    if isinstance(format_, dict) and baseaddr is None and datadef is None:
        return eval(fields)     # pylint: disable=eval-used

    if not isinstance(hardware, int):
        print("baseaddr: {} datadef: {}".format(baseaddr, datadef))
        print('<hardware> ({}) must be defined as integer in <fielddef> {}'.format(type(hardware), fielddef), file=sys.stderr)
        raise SyntaxError(raise_error)

    if not isinstance(format_, (str, dict)):
        print('wrong <format> {} type {} in <fielddef> {}'.format(format_, type(format_), fielddef), file=sys.stderr)
        raise SyntaxError(raise_error)

    # extract addrdef items
    baseaddr = addrdef
    if isinstance(baseaddr, (list, tuple)):
        if len(baseaddr) == 3:
            # baseaddr bit definition
            baseaddr, bits, bitshift = baseaddr
            if not isinstance(bits, int):
                print('<bits> must be defined as integer in <fielddef> {}'.format(fielddef), file=sys.stderr)
                raise SyntaxError(raise_error)
            if not isinstance(bitshift, int):
                print('<bitshift> must be defined as integer in <fielddef> {}'.format(fielddef), file=sys.stderr)
                raise SyntaxError(raise_error)
        elif len(baseaddr) == 2:
            # baseaddr string definition
            baseaddr, strindex_name = baseaddr
            if 'strindex' in fields:
                if not isinstance(strindex_name, str):
                    print('<strindex> must be defined as named index string in <fielddef> {}'.format(fielddef), file=sys.stderr)
                    raise SyntaxError(raise_error)
                try:
                    strindex = get_strindex(hardware, strindex_name)
                    if strindex < 0 or strindex >= CONFIG['info']['template'][SETTINGVAR][HARDWARE.hstr(hardware)].index('SET_MAX'):
                        print('<strindex> out of range [0, {}] in <fielddef> {}'.format(CONFIG['info']['template'][SETTINGVAR][HARDWARE.hstr(hardware)].index('SET_MAX'), fielddef), file=sys.stderr)
                        raise SyntaxError(raise_error)
                except:     # pylint: disable=bare-except
                    pass
        else:
            print('wrong <addrdef> {} length ({}) in <fielddef> {}'.format(addrdef, len(addrdef), fielddef), file=sys.stderr)
            raise SyntaxError(raise_error)
    if not isinstance(baseaddr, int):
        print('<baseaddr> {} must be defined as integer in <fielddef> {}'.format(baseaddr, fielddef), file=sys.stderr)
        raise SyntaxError(raise_error)

    # extract datadef items
    arraydef = datadef
    if isinstance(datadef, (tuple)):
        if len(datadef) == 2:
            # datadef has a validator
            arraydef, validate = datadef
        elif len(datadef) == 3:
            # datadef has a validator and cmd set
            arraydef, validate, cmd = datadef
            # cmd must be a tuple with 2 objects
            if isinstance(cmd, tuple) and len(cmd) == 2:
                group, tasmotacmnd = cmd
                if group is not None and not isinstance(group, str):
                    print('wrong <group> {} in <fielddef> {}'.format(group, fielddef), file=sys.stderr)
                    raise SyntaxError(raise_error)
                if isinstance(tasmotacmnd, tuple):
                    for tcmnd in tasmotacmnd:
                        if tcmnd is not None and not callable(tcmnd) and not isinstance(tcmnd, str):
                            print('wrong <tasmotacmnd> {} in <fielddef> {}'.format(tcmnd, fielddef), file=sys.stderr)
                            raise SyntaxError(raise_error)
                else:
                    if tasmotacmnd is not None and not callable(tasmotacmnd) and not isinstance(tasmotacmnd, str):
                        print('wrong <tasmotacmnd> {} in <fielddef> {}'.format(tasmotacmnd, fielddef), file=sys.stderr)
                        raise SyntaxError(raise_error)
            else:
                print('wrong <cmd> {} length ({}) in <fielddef> {}'.format(cmd, len(cmd), fielddef), file=sys.stderr)
                raise SyntaxError(raise_error)
        else:
            print('wrong <datadef> {} length ({}) in <fielddef> {}'.format(datadef, len(datadef), fielddef), file=sys.stderr)
            raise SyntaxError(raise_error)

        if validate is not None and (not isinstance(validate, str) and not callable(validate)):
            print('wrong <validate> {} type {} in <fielddef> {}'.format(validate, type(validate), fielddef), file=sys.stderr)
            raise SyntaxError(raise_error)

    # convert single int into one-dimensional list
    if isinstance(arraydef, int):
        arraydef = [arraydef]

    if arraydef is not None and not isinstance(arraydef, (list)):
        print('wrong <arraydef> {} type {} in <fielddef> {}'.format(arraydef, type(arraydef), fielddef), file=sys.stderr)
        raise SyntaxError(raise_error)

    # get read/write converter items
    readconverter = converter
    if isinstance(converter, (tuple)):
        if len(converter) == 2:
            # converter has read/write converter
            readconverter, writeconverter = converter
            if not (readconverter is None or readconverter is False or isinstance(readconverter, str) or callable(readconverter)):
                print('wrong <readconverter> {} type {} in <fielddef> {}'.format(readconverter, type(readconverter), fielddef), file=sys.stderr)
                raise SyntaxError(raise_error)
            if not (writeconverter is None or writeconverter is False or isinstance(writeconverter, str) or callable(writeconverter)):
                print('wrong <writeconverter> {} type {} in <fielddef> {}'.format(writeconverter, type(writeconverter), fielddef), file=sys.stderr)
                raise SyntaxError(raise_error)
        else:
            print('wrong <converter> {} length ({}) in <fielddef> {}'.format(converter, len(converter), fielddef), file=sys.stderr)
            raise SyntaxError(raise_error)

    return eval(fields)     # pylint: disable=eval-used

def exec_function(func_, value, idx=None):
    """
    Execute an evaluable string or callable function using macros

    @param func_:
        a callable function or evaluable string
    @param value:
        original value
    @param idx:
        possible array index

    @return:
        (un)converted value
    """
    try:
        if isinstance(func_, str):
            # evaluate strings
            if idx is None:
                idx = ''
            elif len(idx) == 1:
                idx = idx[0]
            valuemapping = copy.deepcopy(CONFIG['valuemapping'])    # pylint: disable=possibly-unused-variable
            func_ = func_.replace('@', 'valuemapping')
            func_ = func_.replace('$', 'value')
            func_ = func_.replace('#', 'idx')
            scope = locals()
            scope.update(SETTING_OBJECTS)
            scope.update({"ARGS": ARGS})
            value = eval(func_, scope)      # pylint: disable=eval-used

        elif callable(func_):
            # use as format function
            if isinstance(idx, int):
                value = func_(value, idx)
            else:
                value = func_(value)

    except Exception as err:    # pylint: disable=broad-except
        exit_(ExitCode.INTERNAL_ERROR, '{}'.format(err), type_=LogType.WARNING, line=inspect.getlineno(inspect.currentframe()))

    return value

def read_converter(value, fielddef, raw=False):
    """
    Convert field value using read converter based on field desc

    @param value:
        original value
    @param fielddef
        field definition - see "Settings dictionary" above
    @param raw
        return raw values (True) or converted values (False)

    @return:
        (un)converted value
    """
    readconverter = get_fielddef(fielddef, fields='readconverter')

    # call password functions even if raw value should be processed
    if callable(readconverter) and passwordread == readconverter:   # pylint: disable=comparison-with-callable
        raw = False

    if not raw and readconverter is not None and readconverter is not False:
        value = exec_function(readconverter, value)
    if not raw and readconverter is False:
        value = False

    return value

def write_converter(value, fielddef, raw=False):
    """
    Convert field value using write converter based on field desc

    @param value:
        original value
    @param fielddef
        field definition - see "Settings dictionary" above
    @param raw
        return raw values (True) or converted values (False)

    @return:
        (un)converted value
    """
    writeconverter = get_fielddef(fielddef, fields='writeconverter')

    # call password functions even if raw value should be processed
    if callable(writeconverter) and passwordwrite == writeconverter:   # pylint: disable=comparison-with-callable
        raw = False

    if not raw and writeconverter is not None:
        value = exec_function(writeconverter, value)

    return value

def cmnd_converter(value, idx, readconverter, writeconverter, tasmotacmnd):    # pylint: disable=unused-argument
    """
    Convert field value into Tasmota command if available

    @param value:
        original value
    @param idx
        array index
    @param readconverter
        <function> to convert value from binary object to JSON
    @param writeconverter
        <function> to convert value from JSON back to binary object
    @param tasmotacmnd
        <function> convert data into Tasmota command function

    @return:
        converted value, list of values or None if unable to convert
    """
    result = None

    if (callable(readconverter) and readconverter == passwordread) or (callable(writeconverter) and writeconverter == passwordwrite):   # pylint: disable=comparison-with-callable
        if value == HIDDEN_PASSWORD:
            return None
        result = value

    if tasmotacmnd is not None and (callable(tasmotacmnd) or len(tasmotacmnd) > 0):
        result = exec_function(tasmotacmnd, value, idx)

    return result

def validate_value(value, fielddef):
    """
    Validate a value if validator is defined in fielddef

    @param value:
        original value
    @param fielddef
        field definition - see "Settings dictionary" above

    @return:
        True if value is valid, False if invalid
    """
    validate = get_fielddef(fielddef, fields='validate')

    if value == 0:
        # can not complete all validate condition
        # some Tasmota values are not allowed to be 0 on input
        # even though these values are set to 0 on Tasmota initial.
        # so we can't validate 0 values
        return True

    valid = True
    try:
        if isinstance(validate, str): # evaluate strings
            valid = eval(validate.replace('$', 'value'))    # pylint: disable=eval-used
        elif callable(validate):     # use as format function
            valid = validate(value)
    except:     # pylint: disable=bare-except
        valid = False

    return valid

def get_formatcount(format_):
    """
    Get format prefix count

    @param format_:
        format specifier

    @return:
        prefix count or 1 if not specified
    """
    if isinstance(format_, str):
        match = re.search(r'\s*(\d+)', format_)
        if match:
            return int(match.group(0))

    return 1

def get_formattype(format_):
    """
    Get format type and bitsize without prefix

    @param format_:
        format specifier

    @return:
        (format_, 0) or (format without prefix, bitsize)
    """
    formattype = format_
    bitsize = 0
    if isinstance(format_, str):
        match = re.search(r'\s*(\D+)', format_)
        if match:
            formattype = match.group(0)
            bitsize = struct.calcsize(formattype) * 8
    return formattype, bitsize

def get_fieldminmax(fielddef):
    """
    Get minimum, maximum of field based on field format definition

    @param fielddef:
        field format - see "Settings dictionary" above

    @return:
        min, max
    """
    # pylint: disable=bad-whitespace
    minmax = {'c': (0,                   0xff),
              '?': (0,                   1),
              'b': (~0x7f,               0x7f),
              'B': (0,                   0xff),
              'h': (~0x7fff,             0x7fff),
              'H': (0,                   0xffff),
              'i': (~0x7fffffff,         0x7fffffff),
              'I': (0,                   0xffffffff),
              'l': (~0x7fffffff,         0x7fffffff),
              'L': (0,                   0xffffffff),
              'q': (~0x7fffffffffffffff, 0x7fffffffffffffff),
              'Q': (0,                   0x7fffffffffffffff),
              'f': (sys.float_info.min,  sys.float_info.max),
              'd': (sys.float_info.min,  sys.float_info.max),
             }
    # pylint: enable=bad-whitespace
    format_ = get_fielddef(fielddef, fields='format_')
    min_ = 0
    max_ = 0

    minmax_format = minmax.get(format_[-1:], None)
    if minmax_format is not None:
        min_, max_ = minmax_format
        max_ *= get_formatcount(format_)
    elif format_[-1:].lower() in ['s', 'p']:
        # s and p may have a prefix as length
        max_ = get_formatcount(format_)

    return min_, max_

def get_fieldlength(fielddef):
    """
    Get length of a field in bytes based on field format definition

    @param fielddef:
        field format - see "Settings dictionary" above

    @return:
        length of field in bytes
    """
    length = 0
    hardware, format_, addrdef, arraydef = get_fielddef(fielddef, fields='hardware, format_, addrdef, arraydef')

    # <arraydef> contains a integer list
    if isinstance(arraydef, list) and len(arraydef) > 0:
        # arraydef contains a list
        # calc size recursive by sum of all elements
        for _ in range(0, arraydef[0]):
            subfielddef = get_subfielddef(fielddef)
            if len(arraydef) > 1:
                length += get_fieldlength((hardware, format_, addrdef, subfielddef))
            # single array
            else:
                length += get_fieldlength((hardware, format_, addrdef, None))

    elif isinstance(format_, dict):
        # -> iterate through format
        addr = None
        setting = format_
        for name in setting:
            baseaddr = get_fielddef(setting[name], fields='baseaddr')
            _len = get_fieldlength(setting[name])
            if addr != baseaddr:
                addr = baseaddr
                length += _len

    # a simple value
    elif isinstance(format_, str):
        length = struct.calcsize(format_)

    return length

def get_subfielddef(fielddef):
    """
    Get subfield definition from a given field definition

    @param fielddef:
        see Settings desc above

    @return:
        subfield definition
    """
    hardware, format_, addrdef, datadef, arraydef, validate, cmd, converter = get_fielddef(fielddef, fields='hardware, format_, addrdef, datadef, arraydef, validate, cmd, converter')

    # create new arraydef
    if len(arraydef) > 1:
        arraydef = arraydef[1:]
    else:
        arraydef = None

    # create new datadef
    if isinstance(datadef, tuple):
        if cmd is not None:
            datadef = (arraydef, validate, cmd)
        else:
            datadef = (arraydef, validate)
    else:
        datadef = arraydef

    # set new field def
    subfielddef = None
    if converter is not None:
        subfielddef = (hardware, format_, addrdef, datadef, converter)
    else:
        subfielddef = (hardware, format_, addrdef, datadef)

    return subfielddef

def is_filtergroup(group):
    """
    Check if group is valid on filter

    @param grooup:
        group name to check

    @return:
        True if group is in filter, otherwise False
    """
    if ARGS.filter is not None:
        if group is None:
            return False
        if group == VIRTUAL:
            return True
        if (INTERNAL.title() not in (groupname.title() for groupname in ARGS.filter) and group.title() == INTERNAL.title()) \
            or group.title() not in (groupname.title() for groupname in ARGS.filter):
            return False
    return True

def get_fieldvalue(fieldname, fielddef, dobj, addr, idxoffset=0):
    """
    Get single field value from definition

    @param fieldname:
        name of the field
    @param fielddef:
        see Settings desc
    @param dobj:
        decrypted binary config data
    @param addr
        addr within dobj

    @return:
        value read from dobj
    """
    hardware, format_, bits, bitshift, strindex = get_fielddef(fielddef, fields='hardware, format_, bits, bitshift, strindex')

    value_ = 0
    unpackedvalue = struct.unpack_from(format_, dobj, addr)
    _, bitsize = get_formattype(format_)

    if not format_[-1:].lower() in ['s', 'p']:
        for val in unpackedvalue:
            value_ <<= bitsize
            value_ = value_ + val
        value_ = bitsread(value_, bitshift, bits)
    else:
        value_ = ""

        # max length of this field
        maxlength = get_fieldlength(fielddef)

        # pay attention of compressed strings
        compressed_str = False
        try:
            if unpackedvalue[0][0] == 0 and \
               unpackedvalue[0][1] != 0 and \
               CONFIG['info']['template']['flag4'][1]['compress_rules_cpu'] and \
               fieldname == 'rules':
                compressed_str = True
            if CONFIG['info']['template']['scripting_compressed'] and \
               CONFIG['valuemapping'].get('scripting_compressed', 0) == 1 and \
               fieldname == 'script':
                compressed_str = True
        except:     # pylint: disable=bare-except
            pass

        if compressed_str:
            # can't use encode()/decode() 'cause this will result in loosing valuecontent - use hex string instead
            if fieldname == 'rules':
                data = unpackedvalue[0][1:]
                # compressed strings (rule) may contain trailing garbadge from uncompressed string after first \x00
                str_ = data[:data.find(0)].hex()
            elif fieldname == 'script':
                data = unpackedvalue[0]
                # compressed strings (rule) may contain trailing garbadge from uncompressed string after first \x00
                str_ = data[:data.find(0)].hex()
            sarray = None
        else:
            # get unpacked binary value as stripped string
            str_ = str(unpackedvalue[0], STR_CODING, errors='ignore')
            # split into single or multiple list elements delimted by \0
            set_max = get_strindex(hardware, 'SET_MAX')
            sarray = str_.split('\x00', set_max)

        if isinstance(sarray, list):
            # strip trailing \0 bytes
            sarray = [element.rstrip('\x00') for element in sarray]
            if strindex is None:
                # single string
                str_ = sarray[0]
            else:
                # indexed string
                try:
                    str_ = sarray[strindex+idxoffset]
                except:     # pylint: disable=bare-except
                    str_ = ""

        if maxlength:
            if compressed_str:
                if fieldname == 'rules':
                    # re-combine compressed string: \x00 + data
                    value_ = '\x00' + str_
                elif fieldname == 'script':
                    value_ = str_
            else:
                # remove unprintable char
                value_ = "".join(itertools.islice((c for c in str_ if c.isprintable() or c in ('\n', '\r', '\t')), maxlength))

    return value_

def set_fieldvalue(fielddef, dobj, addr, value):
    """
    Set single field value from definition

    @param fielddef:
        see Settings desc
    @param dobj:
        decrypted binary config data
    @param addr
        addr within dobj
    @param value
        new value

    @return:
        new decrypted binary config data
    """
    format_ = get_fielddef(fielddef, fields='format_')
    formatcnt = get_formatcount(format_)
    singletype, bitsize = get_formattype(format_)
    if not format_[-1:].lower() in ['s', 'p']:
        addr += (bitsize // 8) * formatcnt
        for _ in range(0, formatcnt):
            addr -= (bitsize // 8)
            maxunsigned = ((2**bitsize) - 1)
            maxsigned = ((2**bitsize)>>1)-1
            val = value & maxunsigned
            if isinstance(value, int) and value < 0 and val > maxsigned:
                val = ((maxunsigned+1)-val) * (-1)
            try:
                struct.pack_into(singletype, dobj, addr, val)
            except struct.error as err:
                exit_(ExitCode.RESTORE_DATA_ERROR,
                      "Single type {} [fielddef={}, addr=0x{:04x}, value={}] - skipped!".format(err, fielddef, addr, val),
                      type_=LogType.WARNING,
                      doexit=not ARGS.ignorewarning,
                      line=inspect.getlineno(inspect.currentframe()))
            value >>= bitsize
    else:
        try:
            struct.pack_into(format_, dobj, addr, value)
        except struct.error as err:
            exit_(ExitCode.RESTORE_DATA_ERROR,
                  "String type {} [fielddef={}, addr=0x{:04x}, value={} - skipped!".format(err, fielddef, addr, value),
                  type_=LogType.WARNING,
                  doexit=not ARGS.ignorewarning,
                  line=inspect.getlineno(inspect.currentframe()))

    return dobj

def get_field(dobj, config_version, fieldname, fielddef, raw=False, addroffset=0, ignoregroup=False, converter=True):
    """
    Get field value from definition

    @param dobj:
        decrypted binary config data
    @param config_version:
        config_version vvalue from Tasmota configuration
    @param fieldname:
        name of the field
    @param fielddef:
        see Settings desc above
    @param raw
        return raw values (True) or converted values (False)
    @param addroffset
        use offset for baseaddr (used for recursive calls)
        for indexed strings: index into indexed string
    @param ignoregroup
        ignore selected groups if True, filter by groups otherwise
    @param converter
        enable read/write converter if True, raw values otherwise

    @return:
        field mapping
    """
    if isinstance(dobj, str):
        dobj = bytearray(dobj)

    valuemapping = None

    if fieldname == SETTINGVAR:
        return valuemapping

    # get field definition
    hardware, format_, baseaddr, strindex, arraydef, group = get_fielddef(fielddef, fields='hardware, format_, baseaddr, strindex, arraydef, group')

    # filter hardware
    if not HARDWARE.match(hardware, config_version):
        return valuemapping

    # filter groups
    if not ignoregroup and not is_filtergroup(group):
        return valuemapping

    # <arraydef> contains a integer list
    if isinstance(arraydef, list) and len(arraydef) > 0:
        arraymapping = []
        offset = 0
        for i in range(0, arraydef[0]):
            subfielddef = get_subfielddef(fielddef)
            length = get_fieldlength(subfielddef)
            if length != 0:
                if strindex is not None:
                    value = get_field(dobj, config_version, fieldname, subfielddef, raw=raw, addroffset=i, ignoregroup=ignoregroup, converter=converter)
                else:
                    value = get_field(dobj, config_version, fieldname, subfielddef, raw=raw, addroffset=addroffset+offset, ignoregroup=ignoregroup, converter=converter)
                arraymapping.append(value)
            offset += length
        # filter arrays containing only None
        if sum(map(lambda element: element is None, arraymapping)) == len(arraymapping):
            return valuemapping
        valuemapping = arraymapping

    # <format> contains a dict
    elif isinstance(format_, dict):
        mapping_value = {}
        # -> iterate through format
        for name in format_:
            value = None
            value = get_field(dobj, config_version, name, format_[name], raw=raw, addroffset=addroffset, ignoregroup=ignoregroup, converter=converter)
            if value is not None:
                mapping_value[name] = value
        # copy complete returned mapping
        valuemapping = copy.deepcopy(mapping_value)

    # a simple value
    elif isinstance(format_, (str, bool, int, float)):
        if get_fieldlength(fielddef) != 0:
            if strindex is not None:
                value = get_fieldvalue(fieldname, fielddef, dobj, baseaddr, addroffset)
            else:
                value = get_fieldvalue(fieldname, fielddef, dobj, baseaddr+addroffset)
            if converter:
                readmapping = read_converter(value, fielddef, raw=raw)
                if readmapping is False:
                    return valuemapping
                valuemapping = readmapping
            else:
                valuemapping = value

    else:
        exit_(ExitCode.INTERNAL_ERROR, "Wrong mapping format definition: '{}'".format(format_), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))

    return valuemapping

def set_field(dobj, config_version, fieldname, fielddef, restoremapping, addroffset=0, filename=""):
    """
    Get field value from definition

    @param dobj:
        decrypted binary config data
    @param config_version:
        config_version vvalue from Tasmota configuration
    @param fieldname:
        name of the field
    @param fielddef:
        see Settings desc above
    @param restoremapping
        restore mapping with the new value(s)
    @param addroffset
        use offset for baseaddr (used for recursive calls)
    @param filename
        related filename (for messages only)

    @return:
        new decrypted binary config data
    """
    # cast unicode
    fieldname = str(fieldname)

    if fieldname == SETTINGVAR:
        return dobj

    hardware, format_, baseaddr, bits, bitshift, strindex, arraydef, group, writeconverter = get_fielddef(fielddef, fields='hardware, format_, baseaddr, bits, bitshift, strindex, arraydef, group, writeconverter')

    # filter hardware
    if not HARDWARE.match(hardware, config_version):
        return dobj

    # filter groups
    if not is_filtergroup(group):
        return dobj

    # do not write readonly values
    if writeconverter is False:
        return dobj

    # <arraydef> contains a list
    if isinstance(arraydef, list) and len(arraydef) > 0:
        offset = 0
        try:
            if len(restoremapping) > arraydef[0]:
                exit_(ExitCode.RESTORE_DATA_ERROR, "file '{sfile}' array '{sname}[{selem}]' exceeds max number of elements [{smax}]".format(sfile=filename, sname=fieldname, selem=len(restoremapping), smax=arraydef[0]), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))
            for i in range(0, arraydef[0]):
                subfielddef = get_subfielddef(fielddef)
                length = get_fieldlength(subfielddef)
                if length != 0:
                    if i >= len(restoremapping): # restoremapping data list may be shorter than definition
                        break
                    subrestore = restoremapping[i]
                    if strindex is not None:
                        dobj = set_field(dobj, config_version, fieldname, subfielddef, subrestore, addroffset=i, filename=filename)
                    else:
                        dobj = set_field(dobj, config_version, fieldname, subfielddef, subrestore, addroffset=addroffset+offset, filename=filename)
                offset += length
        except:     # pylint: disable=bare-except
            exit_(ExitCode.RESTORE_DATA_ERROR, "file '{sfile}' array '{sname}' couldn't restore, format has changed! Restore value contains {rtype} but an array of size [{smax}] is expected".format(sfile=filename, sname=fieldname, rtype=type(restoremapping), smax=arraydef[0]), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))

    # <format> contains a dict
    elif isinstance(format_, dict):
        for name, rm_fielddef in format_.items():    # -> iterate through format
            try:
                restoremap = restoremapping.get(name, None)
            except:     # pylint: disable=bare-except
                restoremap = None
            if restoremap is not None:
                dobj = set_field(dobj, config_version, name, rm_fielddef, restoremap, addroffset=addroffset, filename=filename)

    # a simple value
    elif isinstance(format_, (str, bool, int, float)):
        valid = True
        err_text = ""
        errformat = ""

        min_, max_ = get_fieldminmax(fielddef)
        value = _value = None
        skip = False

        # simple char value
        if format_[-1:] in ['c']:
            try:
                value = write_converter(restoremapping.encode(STR_CODING)[0], fielddef)
            except Exception as err:    # pylint: disable=broad-except
                exit_(ExitCode.INTERNAL_ERROR, '{}'.format(err), type_=LogType.WARNING, line=inspect.getlineno(inspect.currentframe()))
                valid = False

        # bool
        elif format_[-1:] in ['?']:
            try:
                value = write_converter(bool(restoremapping), fielddef)
            except Exception as err:  # pylint: disable=broad-except
                exit_(ExitCode.INTERNAL_ERROR, '{}'.format(err), type_=LogType.WARNING, line=inspect.getlineno(inspect.currentframe()))
                valid = False

        # integer
        elif format_[-1:] in ['b', 'B', 'h', 'H', 'i', 'I', 'l', 'L', 'q', 'Q', 'P']:
            value = write_converter(restoremapping, fielddef)
            if isinstance(value, str):
                value = int(value, 0)
            else:
                try:
                    value = int(value)
                except Exception as err:  # pylint: disable=broad-except
                    err_text = "field '{}' couldn't restore, format may has changed! {}".format(fieldname, err)
                    valid = False

            if valid:
                # bits
                if bits != 0:
                    bitvalue = value
                    value = struct.unpack_from(format_, dobj, baseaddr+addroffset)[0]
                    # validate restoremapping value
                    valid = validate_value(bitvalue, fielddef)
                    if not valid:
                        err_text = "valid bit range exceeding"
                        value = bitvalue
                    else:
                        mask = (1<<bits)-1
                        if bitvalue > mask:
                            min_ = 0
                            max_ = mask
                            _value = bitvalue
                            valid = False
                        else:
                            if bitshift >= 0:
                                bitvalue <<= bitshift
                                mask <<= bitshift
                            else:
                                bitvalue >>= abs(bitshift)
                                mask >>= abs(bitshift)
                            value &= (0xffffffff ^ mask)
                            value |= bitvalue

                # full size values
                else:
                    # validate restoremapping function
                    valid = validate_value(value, fielddef)
                    if not valid:
                        err_text = "valid range exceeding"
                    _value = value

        # float
        elif format_[-1:] in ['f', 'd']:
            try:
                value = write_converter(float(restoremapping), fielddef)
            except:     # pylint: disable=bare-except
                valid = False

        # string
        elif format_[-1:].lower() in ['s', 'p']:
            # pay attention of compressed strings in script/rules
            if len(restoremapping) > 4 and restoremapping[0] == '\x00':
                value = b'\x00' + bytes.fromhex(restoremapping[1:])
            else:
                value = write_converter(restoremapping.encode(STR_CODING), fielddef)
            err_text = "string length exceeding"
            if value is not None:
                max_ -= 1
                valid = min_ <= len(value) <= max_
            else:
                skip = True
                valid = True
            # handle indexed strings
            if strindex is not None:
                # unpack index str from source baseaddr into str_
                unpackedvalue = struct.unpack_from(format_, dobj, baseaddr)
                str_ = str(unpackedvalue[0], STR_CODING, errors='ignore')
                # split into separate string values
                sarray = str_.split('\x00')
                # limit to SET_MAX
                try:
                    set_max = get_strindex(hardware, 'SET_MAX')
                except:     # pylint: disable=bare-except
                    set_max = CONFIG['info']['template'][SETTINGVAR][HARDWARE.hstr(HARDWARE.ESP)].index('SET_MAX')
                if len(sarray) >= set_max:
                    delrange = len(sarray) - set_max
                    if delrange > 0:
                        del sarray[-delrange:]
                if not isinstance(value, str):
                    value = str(value, STR_CODING, errors='ignore')
                # remember possible value changes
                prevvalue = sarray[strindex+addroffset]
                curvalue = value
                # change indexed string
                sarray[strindex+addroffset] = value
                # convert back to binary string stream
                new_value = '\0'.join(sarray).encode(STR_CODING)
                if len(new_value) > get_fieldlength(fielddef):
                    err_text = "Text pool overflow by {} chars (max {})".format(len(new_value) - get_fieldlength(fielddef), get_fieldlength(fielddef))
                    valid = False
                else:
                    value = new_value

        if value is None and not skip:
            # None is an invalid value
            valid = False

        if valid is None and not skip:
            # validate against object type size
            valid = min_ <= value <= max_
            if not valid:
                err_text = "type range exceeding"
                errformat = " [{smin}, {smax}]"

        if _value is None:
            # copy value before possible change below
            _value = value

        if isinstance(_value, str):
            _value = "'{}'".format(_value)

        if valid:
            if not skip:
                if fieldname not in ('cfg_crc', 'cfg_crc32', 'cfg_timestamp', '_'):
                    if strindex is not None:
                        # do not use address offset for indexed strings
                        dobj = set_fieldvalue(fielddef, dobj, baseaddr, value)
                    else:
                        prevvalue = get_fieldvalue(fieldname, fielddef, dobj, baseaddr+addroffset)
                        dobj = set_fieldvalue(fielddef, dobj, baseaddr+addroffset, value)
                        curvalue = get_fieldvalue(fieldname, fielddef, dobj, baseaddr+addroffset)
                    if prevvalue != curvalue and ARGS.verbose:
                        if isinstance(prevvalue, str):
                            prevvalue = '"{}"'.format(prevvalue)
                        if isinstance(curvalue, str):
                            curvalue = '"{}"'.format(curvalue)
                        message("Value for '{}' changed from {} to {}".format(fieldname, prevvalue, curvalue), type_=LogType.INFO)
        else:
            sformat = "file '{sfile}' - {{'{sname}': {svalue}}} ({serror})"+errformat
            exit_(ExitCode.RESTORE_DATA_ERROR, sformat.format(sfile=filename, sname=fieldname, serror=err_text, svalue=_value, smin=min_, smax=max_), type_=LogType.WARNING, doexit=not ARGS.ignorewarning)

    return dobj

def set_cmnd(cmnds, config_version, fieldname, fielddef, valuemapping, mappedvalue, addroffset=0, idx=None):
    """
    Get Tasmota command mapping from given field value definition

    @param cmnds:
        Tasmota command mapping: { 'group': ['cmnd' <,'cmnd'...>] ... }
    @param config_version:
        config_version vvalue from Tasmota configuration
    @param fieldname:
        name of the field
    @param fielddef:
        see Settings desc above
    @param valuemapping:
        data mapping
    @param mappedvalue
        mappedvalue mapping with the new value(s)
    @param addroffset
        use offset for baseaddr (used for recursive calls)
    @param idx
        optional array index

    @return:
        new Tasmota command mapping
    """
    def set_cmnds(cmnds, group, mappedvalue, idx, readconverter, writeconverter, tasmotacmnd):
        """
        Helper to append Tasmota commands to list
        """
        cmnd = cmnd_converter(mappedvalue, idx, readconverter, writeconverter, tasmotacmnd)
        if group is not None and cmnd is not None:
            if group not in cmnds:
                cmnds[group] = []
            if isinstance(cmnd, list):
                for command in cmnd:
                    cmnds[group].append(command)
            else:
                cmnds[group].append(cmnd)
        return cmnds

    # cast unicode
    fieldname = str(fieldname)

    if fieldname == SETTINGVAR:
        return cmnds

    hardware, format_, arraydef, group, readconverter, writeconverter, tasmotacmnd = get_fielddef(fielddef, fields='hardware, format_, arraydef, group, readconverter, writeconverter, tasmotacmnd')

    # filter hardware
    if not HARDWARE.match(hardware, config_version):
        return cmnds

    # filter groups
    if not is_filtergroup(group):
        return cmnds

    # <arraydef> contains a list
    if isinstance(arraydef, list) and len(arraydef) > 0:
        if idx is None:
            idx = []
        idx.append(0)
        offset = 0
        if len(mappedvalue) > arraydef[0]:
            exit_(ExitCode.RESTORE_DATA_ERROR, "array '{sname}[{selem}]' exceeds max number of elements [{smax}]".format(sname=fieldname, selem=len(mappedvalue), smax=arraydef[0]), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))
        for i in range(0, arraydef[0]):
            subfielddef = get_subfielddef(fielddef)
            length = get_fieldlength(subfielddef)
            if length != 0:
                if i >= len(mappedvalue): # mappedvalue data list may be shorter than definition
                    break
                subrestore = mappedvalue[i]
                idx[len(idx)-1] = i
                cmnds = set_cmnd(cmnds, config_version, fieldname, subfielddef, valuemapping, subrestore, addroffset=addroffset+offset, idx=idx)
            offset += length
        if idx is not None:
            idx.pop(len(idx)-1)
        if len(idx) == 0:
            idx = None

    # <format> contains a dict
    elif isinstance(format_, dict):
        for name, rm_fielddef in format_.items():    # -> iterate through format
            mapped = mappedvalue.get(name, None)
            if mapped is not None:
                cmnds = set_cmnd(cmnds, config_version, name, rm_fielddef, valuemapping, mapped, addroffset=addroffset, idx=idx)

    # a simple value
    elif isinstance(mappedvalue, (str, bool, int, float)):
        if group is not None:
            group = group.title()
        if isinstance(tasmotacmnd, tuple):
            tasmotacmnds = tasmotacmnd
            for tasmotacmnd in tasmotacmnds:
                cmnds = set_cmnds(cmnds, group, mappedvalue, idx, readconverter, writeconverter, tasmotacmnd)
        else:
            if not (isinstance(mappedvalue, str) and len(mappedvalue) > 4 and mappedvalue[0] == '\x00'):
                # normal string
                cmnds = set_cmnds(cmnds, group, mappedvalue, idx, readconverter, writeconverter, tasmotacmnd)
            else:
                # compressed string
                uncompressed_data = bytearray(3072)
                compressed = bytes.fromhex(mappedvalue[1:])
                Unishox().decompress(compressed[1:], len(compressed[1:]), uncompressed_data, len(uncompressed_data))
                try:
                    uncompressed_str = str(uncompressed_data, STR_CODING).split('\x00')[0]
                except UnicodeDecodeError as err:
                    exit_(ExitCode.INVALID_DATA, "Compressed string - {}:\n                   {}".format(err, err.args[1]), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))
                    uncompressed_str = str(uncompressed_data, STR_CODING, 'backslashreplace').split('\x00')[0]

                cmnds = set_cmnds(cmnds, group, uncompressed_str, idx, readconverter, writeconverter, tasmotacmnd)

    return cmnds

def bin2mapping(config, raw=False):
    """
    Decodes binary data stream into pyhton mappings dict

    @param config: dict
        'encode': encoded config data
        "decode": decoded config data
        'info': dict about config data (see get_config_info())
    @param raw: boolean
        True: get full mapped data without conversion and without group filtering
        False: get mapped data with conversion enabled and group filtering

    @return:
        mapped data as dictionary
    """
    # check size if exists
    cfg_size = None
    cfg_size_fielddef = config['info']['template'].get('cfg_size', None)
    if cfg_size_fielddef is not None:
        cfg_size = get_field(config['decode'], HARDWARE.ESP, 'cfg_size', cfg_size_fielddef, raw=True, ignoregroup=True)
        # read size should be same as definied in setting
        if cfg_size > config['info']['template_size']:
            # may be processed
            exit_(ExitCode.DATA_SIZE_MISMATCH, "Number of bytes read does not match - read {}, expected {} byte".format(cfg_size, config['info']['template_size']), type_=LogType.ERROR, line=inspect.getlineno(inspect.currentframe()))
        elif cfg_size < config['info']['template_size']:
            # less number of bytes can not be processed
            exit_(ExitCode.DATA_SIZE_MISMATCH, "Number of bytes read to small to process - read {}, expected {} byte".format(cfg_size, config['info']['template_size']), type_=LogType.ERROR, line=inspect.getlineno(inspect.currentframe()))

    # get/calc crc
    cfg_crc_fielddef = config['info']['template'].get('cfg_crc', None)
    if cfg_crc_fielddef is not None:
        cfg_crc = get_field(config['decode'], HARDWARE.ESP, 'cfg_crc', cfg_crc_fielddef, raw=True, ignoregroup=True)
    else:
        cfg_crc = get_settingcrc(config['decode'])

    # get/calc crc32
    cfg_crc32_fielddef = config['info']['template'].get('cfg_crc32', None)
    if cfg_crc32_fielddef is not None:
        cfg_crc32 = get_field(config['decode'], HARDWARE.ESP, 'cfg_crc32', cfg_crc32_fielddef, raw=True, ignoregroup=True)
    else:
        cfg_crc32 = get_settingcrc32(config['decode'])

    # get config timestamp
    cfg_timestamp_fielddef = config['info']['template'].get('cfg_timestamp', None)
    if cfg_timestamp_fielddef is not None:
        cfg_timestamp = get_field(config['decode'], HARDWARE.ESP, 'cfg_timestamp', cfg_timestamp_fielddef, raw=True, ignoregroup=True)
    else:
        cfg_timestamp = int(time.time())

    if cfg_crc32_fielddef is not None:
        if cfg_crc32 != get_settingcrc32(config['decode']):
            exit_(ExitCode.DATA_CRC_ERROR, 'Data CRC32 error, read 0x{:8x} should be 0x{:8x}'.format(cfg_crc32, get_settingcrc32(config['decode'])), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))
    elif cfg_crc_fielddef is not None:
        if cfg_crc != get_settingcrc(config['decode']):
            exit_(ExitCode.DATA_CRC_ERROR, 'Data CRC error, read 0x{:4x} should be 0x{:4x}'.format(cfg_crc, get_settingcrc(config['decode'])), type_=LogType.WARNING, doexit=not ARGS.ignorewarning, line=inspect.getlineno(inspect.currentframe()))

    # get valuemapping
    if raw:
        valuemapping = get_field(config['decode'], config['info']['hardware'], None, (HARDWARE.ESP, config['info']['template'], 0, (None, None, (VIRTUAL, None))), ignoregroup=True, converter=False)
    else:
        valuemapping = get_field(config['decode'], config['info']['hardware'], None, (HARDWARE.ESP, config['info']['template'], 0, (None, None, (VIRTUAL, None))), ignoregroup=False)
        # remove keys having empty object
        if valuemapping is not None:
            for key in {k: v for k, v in valuemapping.items() if isinstance(v, (dict, list, tuple)) and len(valuemapping[k]) == 0}:
                valuemapping.pop(key, None)

    # add header info
    valuemapping['header'] = {
        'timestamp':datetime.utcfromtimestamp(cfg_timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        'data': {
            'crc':      hex(get_settingcrc(config['decode'])),
            'size':     len(config['decode']),
        },
        'template': {
            'version':  {'name':get_versionstr(config['info']['template_version']),
                         'id':hex(config['info']['template_version'])},
            'crc':      hex(cfg_crc),
        },
        'env': {
            'platform': platform.platform(),
            'system': '{} {} {} {}'.format(platform.system(), platform.machine(), platform.release(), platform.version()),
            'python': platform.python_version(),
            'script': '{} v{}'.format(os.path.basename(__file__), METADATA['VERSION_BUILD'])
        }
    }
    if ARGS.debug:
        valuemapping['header']['env'].update({'param': {}})
        for key in ARGS.__dict__:
            if str(key) != 'password':
                valuemapping['header']['env']['param'].update({str(key): eval('ARGS.{}'.format(key))})  # pylint: disable=eval-used

    if cfg_crc_fielddef is not None and cfg_size is not None:
        valuemapping['header']['template'].update({'size': cfg_size})
    if cfg_crc32_fielddef is not None:
        valuemapping['header']['template'].update({'crc32': hex(cfg_crc32)})
        valuemapping['header']['data'].update({'crc32': hex(get_settingcrc32(config['decode']))})
    if config['info']['version'] != 0x0:
        valuemapping['header']['data'].update({'version': {'name':get_versionstr(config['info']['version']),
                                                           'id':hex(config['info']['version'])}})
    cfg_hardware_def = config['info']['template'].get('config_version', None)
    if cfg_hardware_def is not None:
        cfg_hardware = get_field(config['decode'], HARDWARE.ESP, 'config_version', cfg_hardware_def, raw=True, ignoregroup=True)
        valuemapping['header']['data'].update({'hardware': HARDWARE.str(cfg_hardware)})

    return valuemapping

def mapping2bin(config, jsonconfig, filename=""):
    """
    Encodes into binary data stream

    @param config: dict
        'encode': encoded config data
        "decode": decoded config data
        "mapping": mapped config data
        'info': dict about config data (see get_config_info())
    @param jsonconfig:
        restore data mapping
    @param filename:
        name of the restore file (for error output only)

    @return:
        changed binary config data (decrypted) or None on error
    """
    # make empty binarray array
    _buffer = bytearray()
    # add data
    _buffer.extend(config['decode'])

    if config['info']['template'] is not None:
        # iterate through restore data mapping
        for name, data in jsonconfig.items():
            # key must exist in both dict
            setting_fielddef = config['info']['template'].get(name, None)
            if setting_fielddef is not None:
                set_field(_buffer, config['info']['hardware'], name, setting_fielddef, data, addroffset=0, filename=filename)
            else:
                if name != 'header':
                    exit_(ExitCode.RESTORE_DATA_ERROR, "Restore file '{}' contains obsolete name '{}', skipped".format(filename, name), type_=LogType.WARNING, doexit=not ARGS.ignorewarning)

        # CRC32 calc takes precedence over CRC
        cfg_crc32_setting = config['info']['template'].get('cfg_crc32', None)
        if cfg_crc32_setting is not None:
            crc32 = get_settingcrc32(_buffer)
            struct.pack_into(cfg_crc32_setting[1], _buffer, cfg_crc32_setting[2], crc32)
        else:
            cfg_crc_setting = config['info']['template'].get('cfg_crc', None)
            if cfg_crc_setting is not None:
                crc = get_settingcrc(_buffer)
                struct.pack_into(cfg_crc_setting[1], _buffer, cfg_crc_setting[2], crc)
        return _buffer

    exit_(ExitCode.UNSUPPORTED_VERSION, "File '{}', Tasmota configuration version v{} not supported".format(filename, get_versionstr(config['info']['version'])), type_=LogType.WARNING, doexit=not ARGS.ignorewarning)

    return None

def mapping2cmnd(config):
    """
    Encodes mapping data into Tasmota command mapping

    @param config: dict
        'encode': encoded config data
        "decode": decoded config data
        "mapping": mapped config data
        'info': dict about config data (see get_config_info())

    @return:
        Tasmota command mapping {group: [cmnd <,cmnd <,...>>]}
    """
    cmnds = {}
    # iterate through restore data mapping
    for name, mapping in config['groupmapping'].items():
        # key must exist in both dict
        setting_fielddef = config['info']['template'].get(name, None)
        if setting_fielddef is not None:
            cmnds = set_cmnd(cmnds, config['info']['hardware'], name, setting_fielddef, config['groupmapping'], mapping, addroffset=0)
        else:
            if name != 'header':
                exit_(ExitCode.RESTORE_DATA_ERROR, "Restore file contains obsolete name '{}', skipped".format(name), type_=LogType.WARNING, doexit=not ARGS.ignorewarning)
    # cleanup duplicates
    for key in list(cmnds):
        cmnds[key] = list(dict.fromkeys(cmnds[key]))

    return cmnds

def backup(backupfile, backupfileformat, config):
    """
    Create backup file

    @param backupfile:
        Raw backup filename from program args
    @param backupfileformat:
        Backup file format
    @param config: dict
        'encode': encoded config data
        "decode": decoded config data
        "mapping": mapped config data
        'info': dict about config data (see get_config_info())
    """
    def backup_dmp(backup_filename, config):
        # do dmp file write
        with open(backup_filename, "wb") as backupfp:
            backupfp.write(config['encode'])
    def backup_bin(backup_filename, config):
        # do bin file write
        with open(backup_filename, "wb") as backupfp:
            backupfp.write(config['decode'])
            backupfp.write(struct.pack('<L', BINARYFILE_MAGIC))
    def backup_json(backup_filename, config):
        # do json file write
        with codecs.open(backup_filename, "w", encoding=STR_CODING) as backupfp:
            backupfp.write(get_jsonstr(config['groupmapping'], ARGS.jsonsort, ARGS.jsonindent, ARGS.jsoncompact))

    backups = {
        FileType.DMP.lower():("Tasmota", FileType.DMP, backup_dmp),
        FileType.BIN.lower():("binary", FileType.BIN, backup_bin),
        FileType.JSON.lower():("JSON", FileType.JSON, backup_json)
        }

    # possible extension in filename overrules possible given -t/--backup-type parameter
    _, ext = os.path.splitext(backupfile)
    if ext.lower() == '.'+FileType.BIN.lower():
        backupfileformat = FileType.BIN
    elif ext.lower() == '.'+FileType.DMP.lower():
        backupfileformat = FileType.DMP
    elif ext.lower() == '.'+FileType.JSON.lower():
        backupfileformat = FileType.JSON

    dryrun = ""
    if ARGS.dryrun:
        if ARGS.verbose:
            message("Do not write backup files for dry run", type_=LogType.INFO)
        dryrun = SIMULATING

    fileformat = None
    if backupfileformat.lower() in backups:
        _backup = backups[backupfileformat.lower()]
        fileformat = _backup[0]
        backup_filename = make_filename(backupfile, _backup[1], config['valuemapping'])
        if ARGS.verbose:
            message("{}Writing backup file '{}' ({} format)".format(dryrun, backup_filename, fileformat), type_=LogType.INFO)
        if not ARGS.dryrun:
            try:
                _backup[2](backup_filename, config)
            except Exception as err:    # pylint: disable=broad-except
                exit_(ExitCode.INTERNAL_ERROR, "'{}' {}".format(backup_filename, err), line=inspect.getlineno(inspect.currentframe()))

    if fileformat is not None and (ARGS.verbose or ((ARGS.backupfile is not None or ARGS.restorefile is not None) and not ARGS.output)):
        message("{}Backup successful to '{}' ({} format)"\
            .format(dryrun, backup_filename, fileformat), type_=LogType.INFO if ARGS.verbose else None)

def restore(restorefile, backupfileformat, config):
    """
    Restore from file

    @param encode_cfg:
        binary config data (encrypted)
    @param backupfileformat:
        Backup file format
    @param config: dict
        'encode': encoded config data
        "decode": decoded config data
        "mapping": mapped config data
        'info': dict about config data (see get_config_info())
    """
    global EXIT_CODE    # pylint: disable=global-statement

    new_encode_cfg = None

    restorefileformat = None
    if backupfileformat.lower() == 'bin':
        restorefileformat = FileType.BIN
    elif backupfileformat.lower() == 'dmp':
        restorefileformat = FileType.DMP
    elif backupfileformat.lower() == 'json':
        restorefileformat = FileType.JSON
    restorefilename = make_filename(restorefile, restorefileformat, config['valuemapping'])
    filetype = get_filetype(restorefilename)

    if filetype == FileType.DMP:
        if ARGS.verbose:
            message("Reading restore file '{}' (Tasmota format)".format(restorefilename), type_=LogType.INFO)
        try:
            with open(restorefilename, "rb") as restorefp:
                new_encode_cfg = restorefp.read()
        except Exception as err:    # pylint: disable=broad-except
            exit_(ExitCode.INTERNAL_ERROR, "'{}' {}".format(restorefilename, err), line=inspect.getlineno(inspect.currentframe()))

    elif filetype == FileType.BIN:
        if ARGS.verbose:
            message("Reading restore file '{}' (Binary format)".format(restorefilename), type_=LogType.INFO)
        try:
            with open(restorefilename, "rb") as restorefp:
                restorebin = restorefp.read()
        except Exception as err:    # pylint: disable=broad-except
            exit_(ExitCode.INTERNAL_ERROR, "'{}' {}".format(restorefilename, err), line=inspect.getlineno(inspect.currentframe()))
        decode_cfg = None
        header_format = '<L'
        if struct.unpack_from(header_format, restorebin, 0)[0] == BINARYFILE_MAGIC:
            # remove file format identifier (outdated header at the beginning)
            decode_cfg = restorebin[struct.calcsize(header_format):]
        elif struct.unpack_from(header_format, restorebin, len(restorebin)-struct.calcsize(header_format))[0] == BINARYFILE_MAGIC:
            # remove file format identifier (new append format)
            decode_cfg = restorebin[:len(restorebin)-struct.calcsize(header_format)]
        if decode_cfg is not None:
            # process binary to binary config
            new_encode_cfg = decrypt_encrypt(decode_cfg)

    elif filetype in (FileType.JSON, FileType.INVALID_JSON):
        if ARGS.verbose:
            message("Reading restore file '{}' (JSON format)".format(restorefilename), type_=LogType.INFO)
        try:
            with codecs.open(restorefilename, "r", encoding=STR_CODING) as restorefp:
                jsonconfig = json.load(restorefp)
        except ValueError as err:
            exit_(ExitCode.JSON_READ_ERROR, "File '{}' invalid JSON: {}".format(restorefilename, err), line=inspect.getlineno(inspect.currentframe()))
        # process json config to binary config
        new_decode_cfg = mapping2bin(config, jsonconfig, restorefilename)
        new_encode_cfg = decrypt_encrypt(new_decode_cfg)

    elif filetype == FileType.FILE_NOT_FOUND:
        exit_(ExitCode.FILE_NOT_FOUND, "File '{}' not found".format(restorefilename), line=inspect.getlineno(inspect.currentframe()))
    elif filetype == FileType.INCOMPLETE_JSON:
        exit_(ExitCode.JSON_READ_ERROR, "File '{}' incomplete JSON, missing name 'header'".format(restorefilename), line=inspect.getlineno(inspect.currentframe()))
    elif filetype == FileType.INVALID_BIN:
        exit_(ExitCode.FILE_READ_ERROR, "File '{}' invalid BIN format".format(restorefilename), line=inspect.getlineno(inspect.currentframe()))
    else:
        exit_(ExitCode.FILE_READ_ERROR, "File '{}' unknown error".format(restorefilename), line=inspect.getlineno(inspect.currentframe()))

    if new_encode_cfg is not None:
        new_decode_cfg = decrypt_encrypt(new_encode_cfg)

        # Platform compatibility check
        if filetype in (FileType.DMP, FileType.BIN):
            new_config_version = get_config_info(new_decode_cfg)['hardware']
        else:
            try:
                new_config_version = jsonconfig['config_version']
            except:     # pylint: disable=bare-except
                new_config_version = HARDWARE.config_versions.index(HARDWARE.ESP82)
        config_version = config['info']['hardware']
        if config_version != new_config_version:
            exit_(ExitCode.RESTORE_DATA_ERROR, "Data incompatibility: {} '{}' hardware is '{}', restore file '{}' is for hardware '{}'".format(\
                "File" if ARGS.filesource is not None else "Device",
                ARGS.filesource if ARGS.filesource is not None else ARGS.httpsource,
                HARDWARE.str(config_version),
                restorefilename,
                HARDWARE.str(new_config_version)), type_=LogType.WARNING, doexit=not ARGS.ignorewarning)

        # Data version compatibility check
        if filetype in (FileType.DMP, FileType.BIN):
            version_new_data = get_config_info(new_decode_cfg)['version']
            version_device = config['info']['version']
            if version_device != version_new_data:
                exit_(ExitCode.RESTORE_DATA_ERROR, "Restore binary data incompatibility: {} '{}' v'{}', restore file '{}' v'{}'".format(\
                    "File" if ARGS.filesource is not None else "Device",
                    ARGS.filesource if ARGS.filesource is not None else ARGS.httpsource,
                    get_versionstr(version_device),
                    restorefilename,
                    get_versionstr(version_new_data)), type_=LogType.WARNING, doexit=not ARGS.ignorewarning)

        if ARGS.verbose:
            # get binary header and template to use
            message("Config file contains data of Tasmota v{}".format(get_versionstr(config['info']['version'])), type_=LogType.INFO)
        if ARGS.forcerestore or new_encode_cfg != config['encode']:
            dryrun = ""
            if ARGS.dryrun:
                if ARGS.verbose:
                    message("Configuration data changed but leaving untouched, simulating writes for dry run", type_=LogType.INFO)
                dryrun = SIMULATING
                error_code = 0
            # write config direct to device via http
            if ARGS.httpsource is not None:
                if not ARGS.dryrun:
                    if ARGS.verbose:
                        message("{}Push new data to '{}' using restore file '{}'".format(dryrun, ARGS.httpsource, restorefilename), type_=LogType.INFO)
                    error_code, error_str = push_http(new_encode_cfg)
                if error_code:
                    exit_(ExitCode.UPLOAD_CONFIG_ERROR, "Config data upload failed - {}".format(error_str), line=inspect.getlineno(inspect.currentframe()))
                else:
                    if ARGS.verbose or ((ARGS.backupfile is not None or ARGS.restorefile is not None) and not ARGS.output):
                        message("{}Restore successful to device '{}' from '{}'".format(dryrun, ARGS.httpsource, restorefilename), type_=LogType.INFO if ARGS.verbose else None)

            # write config direct to mqttsource via mqtt
            elif ARGS.mqttsource is not None:
                if not ARGS.dryrun:
                    if ARGS.verbose:
                        message("{}Push new data to '{}' using restore file '{}'".format(dryrun, ARGS.mqttsource, restorefilename), type_=LogType.INFO)
                    error_code, error_str = push_mqtt(new_encode_cfg)
                if error_code:
                    exit_(ExitCode.UPLOAD_CONFIG_ERROR, "Config data upload failed - {}".format(error_str), line=inspect.getlineno(inspect.currentframe()))
                else:
                    if ARGS.verbose or ((ARGS.backupfile is not None or ARGS.restorefile is not None) and not ARGS.output):
                        message("{}Restore successful to device '{}' from '{}'".format(dryrun, ARGS.mqttsource, restorefilename), type_=LogType.INFO if ARGS.verbose else None)

            # write config from a file
            elif ARGS.filesource is not None:
                if ARGS.verbose:
                    message("{}Write new data to file '{}' using restore file '{}'".format(dryrun, ARGS.filesource, restorefilename), type_=LogType.INFO)
                if not ARGS.dryrun:
                    try:
                        with open(ARGS.filesource, "wb") as outputfile:
                            outputfile.write(new_encode_cfg)
                    except Exception as err:    # pylint: disable=broad-except
                        exit_(ExitCode.INTERNAL_ERROR, "'{}' {}".format(ARGS.filesource, err), line=inspect.getlineno(inspect.currentframe()))
                if ARGS.verbose or ((ARGS.backupfile is not None or ARGS.restorefile is not None) and not ARGS.output):
                    message("{}Restore successful to file '{}' from '{}'".format(dryrun, ARGS.filesource, restorefilename), type_=LogType.INFO if ARGS.verbose else None)

        else:
            EXIT_CODE = ExitCode.RESTORE_SKIPPED
            if ARGS.verbose or ((ARGS.backupfile is not None or ARGS.restorefile is not None) and not ARGS.output):
                message("Restore skipped, configuration data unchanged", type_=LogType.INFO if ARGS.verbose else None)

def output_tasmotacmnds(tasmotacmnds):
    """
    Print Tasmota command mapping

    @param tasmotacmnds:
        Tasmota command mapping {group: [cmnd <,cmnd <,...>>]}
    """
    def output_tasmotasubcmnds(cmnds, sort_=False):
        # check if cmnds contains concatenated rules
        reg = re.compile(r'Rule[1-3]\s*[+]')
        concated_rules = any(reg.match(line) for line in cmnds)

        if ARGS.cmndusebacklog:

            # search for counting cmnds
            regexp = r'^(\w+)\d{1,3}\s+\S*'
            reg = re.compile(regexp)
            cmnds_counting = list(dict.fromkeys(list(re.search(regexp, item)[1] for item in cmnds if reg.match(item))))

            # iterate through counting commands
            for cmnd in cmnds_counting:

                # get origin commands from counting matchs
                reg = re.compile(cmnd+r'\d{1,3}\s+\S*')
                backlog_cmnds = list(filter(reg.match, cmnds))

                # join cmnds with attend Tasmota Backlog limitations
                i = 0
                backlog = "Backlog "
                for backlog_cmnd in backlog_cmnds:
                    # use Backlog for all except concatenated rules
                    if not (concated_rules and re.search(r'Rule[1-3]{1}\s+[^0-9]', backlog_cmnd) is not None):
                        # take into account of max backlog limits
                        if i >= MAX_BACKLOG or (len(backlog)+len(backlog_cmnd)+1) > MAX_BACKLOGLEN:
                            cmnds.append(backlog)
                            i = 0
                            backlog = "Backlog "
                        if i > 0:
                            backlog += ";"
                        backlog += backlog_cmnd
                        cmnds.remove(backlog_cmnd)
                        i += 1
                if i > 0:
                    cmnds.append(backlog)
        if concated_rules:
            # do not sort group containing concatenated rules
            sort_ = False
        for cmnd in sorted(cmnds, key=lambda cmnd: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', cmnd)]) if sort_ else cmnds:
            print("{}{}".format(" "*ARGS.cmndindent, cmnd))

    groups = get_grouplist(CONFIG['info']['template'])

    if ARGS.cmndgroup:
        for group in groups:
            if group.title() in (groupname.title() for groupname in tasmotacmnds):
                cmnds = tasmotacmnds[group]
                print()
                print("# {}:".format(group))
                output_tasmotasubcmnds(cmnds, ARGS.cmndsort)

    else:
        cmnds = []
        for group in groups:
            if group.title() in (groupname.title() for groupname in tasmotacmnds):
                cmnds.extend(tasmotacmnds[group])
        output_tasmotasubcmnds(cmnds, ARGS.cmndsort)

def parseargs():
    """
    Program argument parser

    @return:
        configargparse.parse_args() result
    """
    class HelpFormatter(configargparse.HelpFormatter):
        """
        Class for customizing the help output
        """

        def _format_action_invocation(self, action):
            """
            Reformat multiple metavar output
                -d <host>, --device <host>, --host <host>
            to single output
                -d, --device, --host <host>
            """

            orgstr = configargparse.HelpFormatter._format_action_invocation(self, action)
            if orgstr and orgstr[0] != '-': # only optional arguments
                return orgstr
            res = getattr(action, '_formatted_action_invocation', None)
            if res:
                return res

            options = orgstr.split(', ')
            if len(options) <= 1:
                action._formatted_action_invocation = orgstr    # pylint: disable=protected-access
                return orgstr

            return_list = []
            for option in options:
                meta = ""
                arg = option.split(' ')
                if len(arg) > 1:
                    meta = arg[1]
                return_list.append(arg[0])
            if len(meta) > 0 and len(return_list) > 0:
                return_list[len(return_list)-1] += " "+meta
            action._formatted_action_invocation = ', '.join(return_list)    # pylint: disable=protected-access
            return action._formatted_action_invocation  # pylint: disable=protected-access

    global PARSER   # pylint: disable=global-statement
    PARSER = configargparse.ArgumentParser(description='Backup/Restore Tasmota configuration data.',
                                           epilog='The arguments -s <filename|host|url> must be given.',
                                           add_help=False,
                                           formatter_class=lambda prog: HelpFormatter(prog))    # pylint: disable=unnecessary-lambda


    source = PARSER.add_argument_group('Source',
                                       'Read/Write Tasmota configuration from/to')
    source.add_argument('-s', '--source',
                        metavar='<filename|host|url>',
                        dest='source',
                        default=DEFAULTS['source']['source'],
                        help="source used for the Tasmota configuration (default: {}). "
                        "Specify source type, path, file, user, password, hostname, port and topic at once as an URL. "
                        "The URL must be in the form 'scheme://[username[:password]@]host[:port][/topic]|pathfile'"
                        "where scheme is 'file' for a tasmota binary config file, 'http' for a Tasmota HTTP web connection "
                        "{}".format(DEFAULTS['source']['source'],
                            "and 'mqtt(s)' for Tasmota MQTT transport ('mqtts' uses a TLS connection to MQTT server)" if MQTT_MODULE else ""))
    source.add_argument('-f', '--file', dest='filesource', default=DEFAULTS['source']['filesource'], help=configargparse.SUPPRESS)
    source.add_argument('--tasmota-file', dest='filesource', help=configargparse.SUPPRESS)
    source.add_argument('-d', '--device', dest='httpsource', default=DEFAULTS['source']['httpsource'], help=configargparse.SUPPRESS)
    source.add_argument('-m', '--mqtt', dest='mqttsource', default=DEFAULTS['source']['mqttsource'], help=configargparse.SUPPRESS)
    source.add_argument('--host', dest='httpsource', help=configargparse.SUPPRESS)
    source.add_argument('-P', '--port', dest='port', default=DEFAULTS['source']['port'], help=configargparse.SUPPRESS)
    source.add_argument('-u', '--username', dest='username', default=DEFAULTS['source']['username'], help=configargparse.SUPPRESS)
    source.add_argument('-p', '--password',
                        metavar='<password>',
                        dest='password',
                        default=DEFAULTS['source']['password'],
                        help="Web server password on HTTP source (set by Tasmota 'WebPassword' command), "
                        "MQTT server password in MQTT source (set by Tasmota 'MqttPassword' command) (default: {})".format(DEFAULTS['source']['password']))

    mqtt = PARSER.add_argument_group('MQTT' if MQTT_MODULE else None,
                                     'MQTT transport settings' if MQTT_MODULE else None)
    mqtt.add_argument('--fulltopic',
                      metavar='<topic>',
                      dest='fulltopic',
                      default=DEFAULTS['source']['fulltopic'],
                      help="Optional MQTT transport fulltopic used for accessing Tasmota device (default: {})".format(DEFAULTS['source']['fulltopic']) if MQTT_MODULE else configargparse.SUPPRESS)
    mqtt.add_argument('--cafile',
                      metavar='<file>',
                      dest='cafile',
                      default=DEFAULTS['source']['cafile'],
                      help="Enables SSL/TLS connection: path to a or filename of the Certificate Authority certificate files that are to be treated as trusted by this client (default {})".format(DEFAULTS['source']['cafile']) if SSL_MODULE and MQTT_MODULE else configargparse.SUPPRESS)
    mqtt.add_argument('--certfile',
                      metavar='<file>',
                      dest='certfile',
                      default=DEFAULTS['source']['certfile'],
                      help="Enables SSL/TLS connection: filename of a PEM encoded client certificate file (default {})".format(DEFAULTS['source']['certfile']) if SSL_MODULE and MQTT_MODULE else configargparse.SUPPRESS)
    mqtt.add_argument('--keyfile',
                      metavar='<file>',
                      dest='keyfile',
                      default=DEFAULTS['source']['keyfile'],
                      help="Enables SSL/TLS connection: filename of a PEM encoded client private key file (default {})".format(DEFAULTS['source']['keyfile']) if SSL_MODULE and MQTT_MODULE else configargparse.SUPPRESS)
    mqtt.add_argument('--insecure',
                      dest='insecure',
                      action='store_true',
                      default=DEFAULTS['source']['insecure'],
                      help="suppress verification of the MQTT server hostname in the server certificate (default {})".format(DEFAULTS['source']['insecure']) if SSL_MODULE and MQTT_MODULE else configargparse.SUPPRESS)
    mqtt.add_argument('--keepalive',
                      metavar='<sec>',
                      dest='keepalive',
                      type=int,
                      default=DEFAULTS['source']['keepalive'],
                      help="keepalive timeout for the client (default {})".format(DEFAULTS['source']['keepalive']) if MQTT_MODULE else configargparse.SUPPRESS)

    backres = PARSER.add_argument_group('Backup/Restore',
                                        'Backup & restore specification')
    backres.add_argument('-i', '--restore-file',
                         metavar='<restorefile>',
                         dest='restorefile',
                         default=DEFAULTS['backup']['backupfile'],
                         help="file to restore configuration from (default: {}). Replacements: @v=firmware version from config, @d=devicename, @f=friendlyname1, @h=hostname from config, @H=device hostname (http source only)".format(DEFAULTS['backup']['restorefile']))
    backres.add_argument('-o', '--backup-file',
                         metavar='<backupfile>',
                         dest='backupfile',
                         action='append',
                         default=DEFAULTS['backup']['backupfile'],
                         help="file to backup configuration to, can be specified multiple times (default: {}). Replacements: @v=firmware version from config, @d=devicename, @f=friendlyname1, @h=hostname from config, @H=device hostname (http source only), @F=configuration filename from MQTT request (mqtt source only)".format(DEFAULTS['backup']['backupfile']))
    backup_file_formats = ['json', 'bin', 'dmp']
    backres.add_argument('-t', '--backup-type',
                         metavar='|'.join(backup_file_formats),
                         dest='backupfileformat',
                         choices=backup_file_formats,
                         default=DEFAULTS['backup']['backupfileformat'],
                         help="backup filetype (default: '{}')".format(DEFAULTS['backup']['backupfileformat']))
    backres.add_argument('-E', '--extension',
                         dest='extension',
                         action='store_true',
                         default=DEFAULTS['backup']['extension'],
                         help="append filetype extension for -i and -o filename{}".format(' (default)' if DEFAULTS['backup']['extension'] else ''))
    backres.add_argument('-e', '--no-extension',
                         dest='extension',
                         action='store_false',
                         default=DEFAULTS['backup']['extension'],
                         help="do not append filetype extension, use -i and -o filename as passed{}".format(' (default)' if not DEFAULTS['backup']['extension'] else ''))
    backres.add_argument('-F', '--force-restore',
                         dest='forcerestore',
                         action='store_true',
                         default=DEFAULTS['backup']['forcerestore'],
                         help="force restore even configuration is identical{}".format(' (default)' if DEFAULTS['backup']['forcerestore'] else ''))


    jsonformat = PARSER.add_argument_group('JSON output',
                                           'JSON format specification. To revert an option, insert "dont" or "no" after "json", e.g. --json-no-indent, --json-dont-show-pw')
    jsonformat.add_argument('--json-indent',
                            metavar='<indent>',
                            dest='jsonindent',
                            type=int,
                            default=DEFAULTS['jsonformat']['indent'],
                            help="pretty-printed JSON output using indent level (default: '{}'). -1 disables indent.".format(DEFAULTS['jsonformat']['indent']))
    jsonformat.add_argument('--json-no-indent', '--json-dont-indent', '--jsonno-indent', '--jsondont-indent', '--json-noindent', '--json-dontindent', '--jsonnoindent', '--jsondontindent',
                            dest='jsonindent',
                            action='store_const', const=-1,
                            help=configargparse.SUPPRESS)

    jsonformat.add_argument('--json-compact',
                            dest='jsoncompact',
                            action='store_true',
                            default=DEFAULTS['jsonformat']['compact'],
                            help="compact JSON output by eliminate whitespace{}".format(' (default)' if DEFAULTS['jsonformat']['compact'] else ''))
    jsonformat.add_argument('--json-no-compact', '--json-dont-compact', '--jsonno-compact', '--jsondont-compact', '--json-nocompact', '--json-dontcompact', '--jsonnocompact', '--jsondontcompact',
                            dest='jsoncompact',
                            action='store_false',
                            help=configargparse.SUPPRESS)

    jsonformat.add_argument('--json-show-pw',
                            dest='jsonhidepw',
                            action='store_false',
                            default=DEFAULTS['jsonformat']['hidepw'],
                            help="unhide passwords{}".format(' (default)' if not DEFAULTS['jsonformat']['hidepw'] else ''))
    jsonformat.add_argument('--json-no-show-pw', '--json-dont-show-pw', '--jsonno-show-pw', '--jsondont-show-pw', '--json-noshow-pw', '--json-dontshow-pw', '--jsonnoshow-pw', '--jsondontshow-pw',
                            dest='jsonhidepw',
                            action='store_true',
                            help=configargparse.SUPPRESS)
    # for backward compatibility only
    jsonformat.add_argument('--json-hide-pw', dest='jsonhidepw', action='store_true', help=configargparse.SUPPRESS)
    jsonformat.add_argument('--json-unhide-pw', dest='jsonhidepw', action='store_false', help=configargparse.SUPPRESS)

    # for backward compatibility only
    jsonformat.add_argument('--json-sort', dest='jsonsort', action='store_true', default=DEFAULTS['jsonformat']['sort'], help=configargparse.SUPPRESS)
    jsonformat.add_argument('--json-unsort', '--json-no-sort', '--json-dont-sort', dest='jsonsort', action='store_false', help=configargparse.SUPPRESS)


    cmndformat = PARSER.add_argument_group('Tasmota command output',
                                           'Tasmota command output format specification. To revert an option, insert "dont" or "no" after "cmnd", e.g. --cmnd-no-indent, --cmnd-dont-sort')
    cmndformat.add_argument('--cmnd-indent',
                            metavar='<indent>',
                            dest='cmndindent',
                            type=int,
                            default=DEFAULTS['cmndformat']['indent'],
                            help="Tasmota command grouping indent level (default: '{}'). 0 disables indent".format(DEFAULTS['cmndformat']['indent']))
    cmndformat.add_argument('--cmnd-no-indent', '--cmnd-dont-indent', '--cmndno-indent', '--cmnddont-indent', '--cmnd-noindent', '--cmnd-dontindent', '--cmndnoindent', '--cmnddontindent',
                            dest='cmndindent',
                            action='store_const', const=0,
                            help=configargparse.SUPPRESS)

    cmndformat.add_argument('--cmnd-groups',
                            dest='cmndgroup',
                            action='store_true',
                            default=DEFAULTS['cmndformat']['group'],
                            help="group Tasmota commands{}".format(' (default)' if DEFAULTS['cmndformat']['group'] else ''))
    cmndformat.add_argument('--cmnd-no-groups', '--cmnd-dont-groups', '--cmndno-groups', '--cmnddont-groups', '--cmnd-nogroups', '--cmnd-dontgroups', '--cmndnogroups', '--cmnddontgroups',
                            dest='cmndgroup',
                            action='store_false',
                            help=configargparse.SUPPRESS)

    cmndformat.add_argument('--cmnd-sort',
                            dest='cmndsort',
                            action='store_true',
                            default=DEFAULTS['cmndformat']['sort'],
                            help="sort Tasmota commands{}".format(' (default)' if DEFAULTS['cmndformat']['sort'] else ''))
    cmndformat.add_argument('--cmnd-no-sort', '--cmnd-dont-sort', '--cmndno-sort', '--cmnddont-sort', '--cmnd-nosort', '--cmnd-dontsort', '--cmndnosort', '--cmnddontsort', '--cmnd-unsort',
                            dest='cmndsort',
                            action='store_false',
                            help=configargparse.SUPPRESS)

    cmndformat.add_argument('--cmnd-use-rule-concat',
                            dest='cmnduseruleconcat',
                            action='store_true',
                            default=DEFAULTS['cmndformat']['useruleconcat'],
                            help="use rule concatenation with + for Tasmota 'Rule' command{}".format(' (default)' if DEFAULTS['cmndformat']['useruleconcat'] else ''))
    cmndformat.add_argument('--cmnd-no-use-rule-concat', '--cmnd-donot-use-rule-concat', '--cmndno-use-rule-concat', '--cmnddonot-use-rule-concat', '--cmnd-nouse-rule-concat', '--cmnd-donotuse-rule-concat', '--cmndnouse-rule-concat', '--cmnddonotuse-rule-concat',
                            dest='cmnduseruleconcat',
                            action='store_false',
                            help=configargparse.SUPPRESS)

    cmndformat.add_argument('--cmnd-use-backlog',
                            dest='cmndusebacklog',
                            action='store_true',
                            default=DEFAULTS['cmndformat']['usebacklog'],
                            help="use 'Backlog' for Tasmota commands as much as possible{}".format(' (default)' if DEFAULTS['cmndformat']['usebacklog'] else ''))
    cmndformat.add_argument('--cmnd-no-use-backlog', '--cmnd-donot-use-backlog', '--cmndno-use-backlog', '--cmnddonot-use-backlog', '--cmnd-nouse-backlog', '--cmnd-donotuse-backlog', '--cmndnouse-backlog', '--cmnddonotuse-backlog',
                            dest='cmndusebacklog',
                            action='store_false',
                            help=configargparse.SUPPRESS)


    common = PARSER.add_argument_group('Common', 'Optional arguments')
    common.add_argument('-c', '--config',
                        metavar='<configfile>',
                        dest='configfile',
                        default=DEFAULTS['common']['configfile'],
                        is_config_file=True,
                        help="program config file - can be used to set default command parameters (default: {})".format(DEFAULTS['common']['configfile']))

    common.add_argument('-S', '--output',
                        dest='output',
                        action='store_true',
                        default=DEFAULTS['common']['output'],
                        help="display output regardsless of backup/restore usage{}".format(" (default)" if DEFAULTS['common']['output'] else " (default do not output on backup or restore usage)"))
    output_formats = ['json', 'cmnd', 'command']
    common.add_argument('-T', '--output-format',
                        metavar='|'.join(output_formats),
                        dest='outputformat',
                        choices=output_formats,
                        default=DEFAULTS['common']['outputformat'],
                        help="display output format (default: '{}')".format(DEFAULTS['common']['outputformat']))
    groups = get_grouplist(SETTINGS[0][2])
    if VIRTUAL in groups:
        groups.remove(VIRTUAL)
    common.add_argument('-g', '--group',
                        dest='filter',
                        metavar='<groupname>',
                        choices=groups,
                        nargs='+',
                        type=lambda s: s.title(),
                        default=DEFAULTS['common']['filter'],
                        help="limit data processing to command groups (default {})".format("no filter" if DEFAULTS['common']['filter'] is None else DEFAULTS['common']['filter']))
    common.add_argument('-w', '--ignore-warnings',
                        dest='ignorewarning',
                        action='store_true',
                        default=DEFAULTS['common']['ignorewarning'],
                        help="do not exit on warnings{}. Not recommended, used by your own responsibility!".format(' (default)' if DEFAULTS['common']['ignorewarning'] else ''))
    common.add_argument('--dry-run',
                        dest='dryrun',
                        action='store_true',
                        default=DEFAULTS['common']['ignorewarning'],
                        help="test program without changing configuration data on device or file{}".format(' (default)' if DEFAULTS['common']['dryrun'] else ''))


    info = PARSER.add_argument_group('Info', 'Extra information')
    info.add_argument('--debug',
                      dest='debug',
                      action='store_true',
                      help=configargparse.SUPPRESS)
    info.add_argument('-h', '--help',
                      dest='shorthelp',
                      action='store_true',
                      help='show usage help message and exit')
    info.add_argument("-H", "--full-help",
                      action="help",
                      help="show full help message and exit")
    info.add_argument('-v', '--verbose',
                      dest='verbose',
                      action='store_true',
                      help='produce more output about what the program does')
    info.add_argument('-V', '--version',
                      dest='version',
                      action='count',
                      help="show program's version number and exit")

    _args = PARSER.parse_args()

    if _args.version is not None:
        print(PROG)
        if _args.version or _args.debug:
            print()
            print("Script:   {}".format(os.path.basename(__file__)))
            print("Python:   {}".format(platform.python_version()))
            print("Platform: {} - {}".format(platform.platform(), platform.machine()))
            print("OS:       {} {} {}".format(platform.system(), platform.release(), platform.version()))
            print("Time:     {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        sys.exit(ExitCode.OK)

    return _args

if __name__ == "__main__":
    ARGS = parseargs()
    if ARGS.shorthelp:
        shorthelp()

    if not MQTT_MODULE:
        ARGS.mqttsource = None

    # check for ambiguous source parameters
    if sum(map(lambda i: i is not None, (ARGS.source, ARGS.httpsource, ARGS.mqttsource, ARGS.filesource))) > 1:
        exit_(ExitCode.ARGUMENT_ERROR, "I am confused! Several sources have been specified by -s, -d or -f parameter - limit it to a single one", line=inspect.getlineno(inspect.currentframe()))

    # default no configuration available
    CONFIG['encode'] = None

    if ARGS.debug:
        # Check whole setting definition
        check_setting_definition()

    # set the source type based on the criteria
    if ARGS.source is not None:
        # check source args
        URLPARSE = urllib.parse.urlparse(urllib.parse.quote(ARGS.source, safe='/:@'))
        # http(s)
        #   ARGS.source = http(s)://<user>:<password>@tasmota:<port>
        if URLPARSE.scheme in ('http', 'https'):
            ARGS.httpsource = ARGS.source

        # mqtt(s)
        #   ARGS.source = mqtt(s)://<user>:<password>@tasmota:<port>
        elif MQTT_MODULE and URLPARSE.scheme in ('mqtt', 'mqtts'):
            ARGS.mqttsource = ARGS.source

        # file:
        #   ARGS.source = file:// or (not http(s)and not mqtt(s) and <source> exists)
        elif URLPARSE.scheme in ('file',) or (
            ARGS.httpsource is None and
            ARGS.mqttsource is None and
            os.path.isfile(ARGS.source) and
            get_filetype(ARGS.source) == FileType.DMP
            ):
            ARGS.filesource = ARGS.source
        else:
            ARGS.httpsource = ARGS.source

    if sum(map(lambda i: i is not None, (ARGS.source, ARGS.httpsource, ARGS.mqttsource, ARGS.filesource))) == 0:
        shorthelp()

    # souce is a file: pull config from Tasmota file
    if ARGS.filesource is not None:
        CONFIG['encode'] = load_tasmotaconfig(ARGS.filesource)

    # source is httpsource: load config from Tasmota http webserver
    if ARGS.httpsource is not None:
        CONFIG['encode'] = pull_http()

    # source is mqttsource: load config from Tasmota by MQTT request
    if ARGS.mqttsource is not None:
        CONFIG['encode'] = pull_mqtt()

    if CONFIG['encode'] is None:
        # no config source given
        shorthelp(False)
        print()
        print(PARSER.epilog)
        sys.exit(ExitCode.OK)

    if len(CONFIG['encode']) == 0:
        exit_(ExitCode.FILE_READ_ERROR,
              "Unable to read configuration data from {}'{}'"\
              .format('Device ' if ARGS.httpsource is not None else 'Data ' if ARGS.mqttsource is not None else 'File ',
              ARGS.httpsource if ARGS.httpsource is not None else ARGS.mqttsource if ARGS.mqttsource is not None else ARGS.filesource),
              line=inspect.getlineno(inspect.currentframe()))

    # decrypt Tasmota config
    CONFIG['decode'] = decrypt_encrypt(CONFIG['encode'])

    # config dict
    CONFIG['info'] = get_config_info(CONFIG['decode'])

    # decode into mapping dictionary
    # first we need full mapped data for function macros in 2. step
    CONFIG['valuemapping'] = bin2mapping(CONFIG, raw=True)
    # second decode data using function macros
    CONFIG['groupmapping'] = bin2mapping(CONFIG, raw=False)

    # check version compatibility
    if CONFIG['info']['version'] is not None:
        if ARGS.verbose:
            message("{}'{}' is using Tasmota v{} on {}"\
                    .format('Device ' if ARGS.httpsource is not None else 'Data ' if ARGS.mqttsource is not None else 'File ',
                    ARGS.httpsource if ARGS.httpsource is not None else ARGS.mqttsource if ARGS.mqttsource is not None else ARGS.filesource,
                    get_versionstr(CONFIG['info']['version']),
                    HARDWARE.str(CONFIG['info']['hardware'])),
                    type_=LogType.INFO)
        SUPPORTED_VERSION = sorted(SETTINGS, key=lambda s: s[0], reverse=True)[0][0]
        if CONFIG['info']['version'] > SUPPORTED_VERSION and not ARGS.ignorewarning:
            try:
                COLUMNS = os.get_terminal_size()[0]
            except:     # pylint: disable=bare-except
                COLUMNS = 80
            exit_(ExitCode.UNSUPPORTED_VERSION, \
                "\n           ".join(textwrap.wrap(\
                "Tasmota configuration data v{} currently unsupported! "
                "The read configuration data is newer than the last supported v{} by this program. "
                "Newer Tasmota versions may contain changed data structures so that the data with "
                "older versions may become incompatible. You can force proceeding at your own risk "
                "by appending the parameter '--ignore-warnings'. "
                "Be warned: Forcing can lead to unpredictable results for your Tasmota device. "
                "In the worst case, your Tasmota device  will not respond and you will have to flash "
                "it again using the serial interface. If you are unsure and do not know the  changes "
                "in the configuration structure, you may able to use the developer version of this "
                "program from https://github.com/tasmota/decode-config/tree/development.", \
                COLUMNS - 16)) \
                .format(get_versionstr(CONFIG['info']['version']), get_versionstr(SUPPORTED_VERSION)),
                  type_=LogType.WARNING, doexit=not ARGS.ignorewarning)

    if ARGS.backupfile is not None:
        # backup to file(s)
        for BACKUPFILE in ARGS.backupfile:
            backup(BACKUPFILE, ARGS.backupfileformat, CONFIG)

    if ARGS.restorefile is not None:
        # restore from file
        restore(ARGS.restorefile, ARGS.backupfileformat, CONFIG)

    if (ARGS.backupfile is None and ARGS.restorefile is None) or ARGS.output:
        if ARGS.outputformat == 'json':
            # json screen output
            print(get_jsonstr(CONFIG['groupmapping'], ARGS.jsonsort, ARGS.jsonindent, ARGS.jsoncompact))

        if ARGS.outputformat in ('cmnd', 'command'):
            # Tasmota command output
            output_tasmotacmnds(mapping2cmnd(CONFIG))

    if EXIT_CODE != ExitCode.OK and ARGS.ignorewarning:
        EXIT_CODE = ExitCode.OK
    sys.exit(EXIT_CODE)
