# decode-config

Convert, backup and restore configuration data of devices flashed with [Tasmota firmware](https://github.com/arendst/Tasmota).

<!-- markdownlint-disable MD033 -->
<img src="https://github.com/tasmota/decode-config/blob/master/media/pic/decode-config.png" alt="Overview" title="decode-config Overview" width="600">

<!-- markdownlint-disable MD033 -->
[![master](https://img.shields.io/badge/master-v12.3.1.0-blue.svg)](https://github.com/tasmota/decode-config/tree/master)
[![GitHub download](https://img.shields.io/github/downloads/tasmota/decode-config/total.svg)](https://github.com/tasmota/decode-config/releases/latest)
[![PyPI version](https://badge.fury.io/py/decode-config.svg)](https://badge.fury.io/py/decode-config)
![PyPI downloads](https://img.shields.io/pypi/dm/decode-config?label=pypi%20downloads)
[![License](https://img.shields.io/github/license/tasmota/decode-config.svg)](LICENSE)

If you like **decode-config** give it a star or fork it and contribute:

[![GitHub stars](https://img.shields.io/github/stars/tasmota/decode-config.svg?style=social&label=Star)](https://github.com/tasmota/decode-config/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/tasmota/decode-config.svg?style=social&label=Fork)](https://github.com/tasmota/decode-config/network)
[![donate](https://img.shields.io/badge/donate-PayPal-blue.svg)](https://paypal.me/NorbertRichterDE)

In comparison with the [Tasmota](https://github.com/arendst/Tasmota) build-in "*Backup Configuration*" / "*Restore Configuration*" function the **decode-config** tool:

* uses a human readable and editable [JSON](http://www.json.org/)-format for backup/restore
* can restore previously backed up and modified JSON-format files
* is able to process any subsets of configuration data
* can convert data from older Tasmota versions (from version v5.10.0) to a newer one and vice versa
* is able to create Tasmota compatible command list for the most available commands

Comparing backup files created by **decode-config** and [.dmp](#dmp-format) files created by Tasmota "*Backup Configuration*" / "*Restore Configuration*":

| Configuration           | decode-config JSON file | Tasmota *.dmp file |
|:------------------------|:-----------------------:|:------------------:|
| encrypted               |           No            |         Yes        |
| readable                |           Yes           |         No         |
| editable                |           Yes           |         No         |
| batch processing        |           Yes           |         No         |
| Backup/Restore subsets  |           Yes           |         No         |

**decode-config** is compatible with all [Tasmota](https://github.com/arendst/Tasmota) versions, starting from Tasmota v5.10.0 up to the current one.

## Development

Using the latest development version of decode-config is only necessary if you also use the latest development version of Tasmota.

<!-- markdownlint-disable MD033 -->
[![development version](https://img.shields.io/badge/development-v12.3.1.6-blue.svg)](https://github.com/tasmota/decode-config/tree/development)

## Table of contents

* [Development](#development)
* [Table of contents](#table-of-contents)
* [Running the program](#running-the-program)
  * [Installation](#installation)
* [Usage](#usage)
  * [Basics](#basics)
  * [Tasmota source](#tasmota-source)
  * [Format JSON output](#format-json-output)
  * [Parameter file](#parameter-file)
  * [Save backup](#save-backup)
  * [Restore backup](#restore-backup)
  * [Auto file extensions](#auto-file-extensions)
  * [Test your parameter](#test-your-parameter)
  * [Console outputs](#console-outputs)
  * [Filter by groups](#filter-by-groups)
* [Usage examples](#usage-examples)
  * [Using Tasmota binary configuration files](#using-tasmota-binary-configuration-files)
  * [Using JSON editable file](#using-json-editable-file)
  * [Use batch processing](#use-batch-processing)
* [File Formats](#file-formats)
  * [.dmp format](#dmp-format)
  * [.json format](#json-format-1)
  * [.bin format](#bin-format)
* [Program parameter list](#program-parameter-list)
  * [--full-help](#--full-help)
  * [Parameter notes](#parameter-notes)
  * [Obsolete parameters](#obsolete-parameters)
* [Generated Tasmota commands](#generated-tasmota-commands)
* [Program return codes](#program-return-codes)

## Running the program

### Installation

**decode-config.py** needs an installed [Python](https://en.wikipedia.org/wiki/Python_%28programming_language%29) environment - (see [Prerequisite](#prerequisite)).

After you have installed your Python environment, there are two ways to install deocde-config:

#### Installation using PyPi

```shell
pip install decode-config
```

The program does not have a graphical user interface (GUI), you have to run it from your OS command line using [program arguments](#usage) - see [Usage](#usage) for more details.

#### Manual installation

This is only necessary if you want to run **decode-config.py** from [development branch](https://github.com/tasmota/decode-config/tree/development). First install the required modules manually

```shell
python -m pip install -r requirements.txt
```

After that you can use the Phython script **decode-config.py** as normal program:

```shell
decode-config.py
```

#### Prerequisite

Since **decode-config.py** is a Python program, it requires an installed [Python](https://en.wikipedia.org/wiki/Python_%28programming_language%29) environment.

##### Linux

Install [Python 3.x](https://www.python.org/downloads/) and Pip:

```bash
sudo apt-get install python3 python3-pip
```

##### Windows

Install [Python 3.x](https://www.python.org/downloads/windows/) as described

##### MacOS

Install [Python 3.x](https://www.python.org/downloads/mac-osx/) as described

## Usage

For an overview start the program without any parameter and you will get a short help:

<!-- markdownlint-capture -->
<!-- markdownlint-disable MD031 -->
```bash
decode-config.py
```

This prints a short help:

```help
usage: decode-config.py [-s <filename|host|url>] [-p <password>]
                        [--fulltopic <topic>] [--cafile <file>]
                        [--certfile <file>] [--keyfile <file>] [--insecure]
                        [--keepalive <sec>] [-i <restorefile>]
                        [-o <backupfile>] [-t json|bin|dmp] [-E] [-e] [-F]
                        [--json-indent <indent>] [--json-compact]
                        [--json-show-pw] [--cmnd-indent <indent>]
                        [--cmnd-groups] [--cmnd-sort]
                        [--cmnd-use-rule-concat] [--cmnd-use-backlog]
                        [-c <configfile>] [-S] [-T json|cmnd|command]
                        [-g <groupname> [<groupname> ...]] [-w] [--dry-run]
                        [-h] [-H] [-v] [-V]
```

For advanced help run **decode-config** with parameter `--full--help` or `-H`. This will print a [Program parameter list](#program-parameter-list).

> **Note**  
If you're missing older parameters, don't worry, they're still there (see [Obsolete parameters](#obsolete-parameters)).

### Basics

To get a program result, pass at least a [Tasmota source](#tasmota-source) from which you want to read the configuration data.

### Tasmota source

The Tasmota source determines where the configuration data should be loaded from and saved to.
A source can be an offline file or an online Tasmota device accessed via HTTP or indirectly via MQTT.

Use `--source` parameter to determine the configuration data source:

#### Binary (*.dmp) file (Offline)

Source is a Tasmota configuration file (having extension `.dmp`).

Pass the filename direclty or encoded as a [file-URL](https://en.wikipedia.org/wiki/URL):

```bash
decode-config --source tasmota-4281.dmp
decode-config -s file://path/to/tasmota-4281.dmp
```

#### HTTP connection (Online)

Source is an online HTTP connection to a running Tasmota device. To use this source, **decode-config** must have access to the network on which Tasmota is running, [Tasmota Webserver](https://tasmota.github.io/docs/Commands/#webserver) running in admin mode (`WebServer 2`) is mandatory.

Specify the hostname, IP o or [http-url](https://en.wikipedia.org/wiki/URL) of the Tasmota device.

An optionally required HTTP password, username and different HTTP port of the device can be specified via [URL](https://en.wikipedia.org/wiki/URL) or separately via `--username`, `--password` and `--port`

```bash
decode-config --source tasmota-4281
decode-config -s 192.168.10.92
decode-config --source http://tasmota-4281 --password myPaszxwo!z
decode-config --source http://admin:myPaszxwo!z@tasmota-4281:8000
decode-config --source http://admin:myPaszxwo!z@tasmota-4281/cs?
```

An appended HTTP path (here "`/cs?`") is ignored.

#### MQTT transission (Online)

Source is a MQTT server and topic where an online Tasmota device is connected to. To use this source, **decode-config** does not need to have access to the same network that Tasmota is running on, it just needs access to the MQTT server that Tasmota also uses.

##### MQTT connection parameter

Specify the hostname or IP of the MQTT server (possibly also specify username and password for the MQTT server) and the Tasmota MQTT topic. The **decode-config** connection to MQTT server also allows SSL/TLS connection.

The MQTT username and password must be encoded within the URL (the parameter `--password` can not be used for that, it has a different function here).  
If the username/password combination for the **decode-config** MQTT connection is different from the one used by Tasmota itself (Tasmota command `MQTTPassword`), the Tasmota MQTT password must be specified via the `--password` parameter.

The Tasmota topic can be specfied either within the [URL path](https://en.wikipedia.org/wiki/URL#Syntax) component or using optional `--fulltopic` parameter.  
The topic must be the full topic of the Tasmota device without any trailing command or result part. You can use any of the prefixed topic (*cmnd*, *stat* or *tele* topic) or use the placeholder *%prefix%* for it, example  
`%prefix%/tasmota-4281` or `tele/tasmota-4281` are valid topics  
`cmnd/tasmota-4281/POWER` or `tele/tasmota-4281/STATE` are invalid topics due to the trailing part.

For SSL/TLS connection to MQTT server use `mqtts://` [URL scheme](https://en.wikipedia.org/wiki/URL#Syntax).

```bash
decode-config --source mqtts://mybroker.example.com/%prefx%/tasmota-4281
decode-config --source mqtts://mybroker.example.com:8883/tele/tasmota-4281
decode-config --source mqtts://mqttuser:myBrokerPaszxwo!z@mybroker.example.com  --fulltopic tele/tasmota-4281
decode-config --source mqtts://mqttuser:myBrokerPaszxwo!z@mybroker.example.com/tele/tasmota-4281 --password myTasmotaMQTTPaszxwo!z
```

For own certifications use the parameters `--cafile`, `--certfile` and `--keyfile`. To suppress certification verification use `--insecure`.

For none SSL/TLS connection to MQTT server use `mqtt://` [URL scheme](https://en.wikipedia.org/wiki/URL#Syntax).

```bash
decode-config --source mqtt://mybroker.example.com/%prefx%/tasmota-4281
decode-config --source mqtt://mybroker.example.com:1883/tele/tasmota-4281
decode-config --source mqtt://mqttuser:myBrokerPaszxwo!z@mybroker.example.com  --fulltopic tele/tasmota-4281
decode-config --source mqtt://mqttuser:myBrokerPaszxwo!z@mybroker.example.com/tele/tasmota-4281 --password myTasmotaMQTTPaszxwo!z
```

### Format JSON output

All basic examples above will output a readable configuration in [JSON](http://www.json.org/)-format, e.g.:

```json
{"altitude": 112, "baudrate": 115200, "blinkcount": 10, "blinktime": 10,...
"ws_width": [1, 3, 5]}
```

> **Note**  
The json names (like `"altitude"` or `"blinktime"` are internal names from Tasmotas [settings.h](https://github.com/arendst/Tasmota/blob/master/tasmota/include/tasmota_types.h) STRUCT `Settings` and are not the same as known from Tasmota [web-console commands](https://tasmota.github.io/docs/Commands/). However, since most variable names are self-describing, the functional meaning should be given in most cases.

The default JSON output can be formatted for better reading using the `--json-indent <n>` parameter:

```bash
decode-config --source tasmota-4281 --password "myPaszxwo!z" --json-indent 2
```

This will print a pretty better readable format and the example above becomes:

```json
{
  "altitude": 112,
  "baudrate": 115200,
  "blinkcount": 10,
  "blinktime": 10,
  ...
  "ws_width": [
    1,
    3,
    5
  ]
}
```

### Parameter file

Because the number of parameters are growing, it would be difficult to enter all these parameters again and again. In that case it is best to use a configuration file that contains your standard parameters and which we then have to specify as the only additional parameter.  
[Program parameter](#program-parameter-list) starting with `--` (eg. `--username`) can be set into such a configuration file. Simply write each neccessary parameter including possible value without dashes into a text file. For a better identification of this file, extension `.conf` is recommended:

Writing all the previous used device parameter in a file, create the text file `my.conf` and insert:

```conf
[source]
username = admin
password = myPaszxwo!z

[JSON]
json-indent 2
```

> **Hint**  
Group names enclosed in square brackets [ ], like `[source]` in the example, are optional and ignored - you can use them to increase readability.

Now we can use it with `-c` parameter:

```bash
decode-config -c my.conf -s tasmota-4281
```

> **Note**  
For further of parameter file syntax see [https://pypi.org/project/ConfigArgParse](https://pypi.org/project/ConfigArgParse/)).

If parameters are specified in more than one place (parameter file and command line), the commandline parameters will overrule the file parameters. This is usefull if you use a basic set of parameters and want to change parameter once without the need to edit your configuration file:

```bash
decode-config -c my.conf -s tasmota-4281 --json-indent 4
```

Here JSON will be output with indent of 4 spaces instead of the `2` set from `my.conf`-

### Save backup

To save data from a device or [*.dmp](#dmp-format) file into a backup file, use `--backup-file <filename>`.

#### Backup filename macros

You can use the following placeholders within filenames:

* **@v** is replaced by *Tasmota Version* (backup & restore filenames)
* **@d** is replaced by *Devicename* (backup & restore filenames)
* **@f** is replaced by first *Friendlyname1* (backup & restore filenames)
* **@h** is replaced by the *Hostname* from configuration data (backup & restore filenames)  
Note: This is the static hostname which is configured by the command *Hostname*, for real hostname from a device use macro the **@H**)
* **@H** is replaced by the live device hostname  (only for http sources, backup & restore filenames)  
Note: This can be different to the configured hostname as this can contain also macros).source
* **@F** is replaced by the filename of MQTT request (only for MQTT sources, backup filenames only).  
This is usually the filename that Tasmota uses when saving the configuration in the WebUI.

Example:

```bash
decode-config -c my.conf -s tasmota-4281 --backup-file Config_@d_@v
```

This will create a file like `Config_Tasmota_10.1.json` (the part `Tasmota` and `10.1` will choosen related to your device configuration).

#### Save multiple backup at once

Since **decode-config** v8.2.0.5 the `--backup-file` parameter can be specified multiple times. With that it's easy to create different backup with different names and/or different formats at once:

```bash
decode-config -c my.conf -s tasmota-4281 -o Config_@d_@v -o Backup_@H.json -o Backup_@H.dmp
```

creates three backup files:

* `Config_Tasmota_10.1.json` using JSON format
* `Backup_tasmota-4281.json` using JSON format
* `Backup_tasmota-4281.dmp` using Tasmota configuration file format

### Restore backup

Reading back a previously saved backup file, use the `--restore-file <filename>` parameter.

To restore the previously save backup file `Config_Tasmota_10.1.json` to device `tasmota-4281` use:

```bash
decode-config -c my.conf -s tasmota-4281 --restore-file Config_Tasmota_10.1
```

Restore operation also allows placeholders **@v**, **@d**, **@f**, **@h** or **@H** like in backup filenames so we can use the same naming as for the backup process:

```bash
decode-config -c my.conf -s tasmota-4281 --restore-file Config_@d_@v
```

> **Note**  
Placeholders used in restore filenames only work as long as the underlying data of the device has not changed between backup and restore, since **decode-config** first read them from the config file or the device to replace it.

#### Restore subset of data

If you use the default JSON format for backup files you can also use files containing a subset of configuration data only.

Example: You want to change the data for location (altitude, latitude, longitude) only, create a JSON file `location.json` with the content

```json
{
  "altitude": 0,
  "latitude": 48.85836,
  "longitude": 2.294442
}
```

Set this location for a device:

```bash
decode-config -c my.conf -s tasmota-4281 -i location
```

> **Hint**  
Keep the JSON-format valid e.g. when cutting unnecessary content from a given JSON backup file, consider to remove the last comma on same indent level:  
Invalid JSON (useless comma in line 3: `...2.294442,`):<pre>{
  "latitude": 48.85836,
  "longitude": 2.294442,
}</pre>valid JSON:<pre>{
  "latitude": 48.85836,
  "longitude": 2.294442
}</pre>

Using subsets of data JSON files are powerfull possibilitiy to create various personal standard configuration files that are identical for all your Tasmota devices and that you can then reuse for newly configure Tasmotas.

### Auto file extensions

File extensions are selected based on the file content and / or the `--backup-type` parameter. You don't need to add extensions to your file:

* If you omit the file extensions, one of `.dmp`, `.bin` or `.json` is used depending on the selected backup type
* If you omit the `--backup-type` parameter and the selected file name has one of the standard extensions `.dmp`, `.bin` or `.json`, the backup type is set based on the extension.

If you use your own extensions, deactivate the automatic extension using the `--no-extension` parameter and use the optional `--backup-type` parameter if neccessary.

Examples:

* `decode-config --source tasmota-4281 --backup-file tasmota-4281.bin`<br>
is identical with<br>
`decode-config --source tasmota-4281 --backup-type bin --backup-file tasmota-4281`<br>
In both cases the backup file `tasmota-4281.bin` is created.
* `decode-config --source tasmota-4281 --restore-file tasmota-4281.json`<br>
is identical with<br>
`decode-config --source tasmota-4281 --restore-file tasmota-4281`<br>
In both cases the backup file `tasmota-4281.json` will tried to restore (remember `--backup-type json` is the default)
* whereas<br>
`decode-config --source tasmota-4281 --no-extension --restore-file tasmota-4281`<br>
will fail if `tasmota-4281` does not exist and<br>
`decode-config --source tasmota-4281 --no-extension --backup-file tasmota-4281`<br>
will create a json backup file named `tasmota-4281` (without the extension).

### Test your parameter

To test your parameter append `--dry-run`:

```bash
decode-config -s tasmota-4281 -i backupfile --dry-run
```

This runs the complete process but prevent writing any changes to a device or file.

### Console outputs

Output to the console screen is the default when calling the program without any backup or restore parameter.  
Screen output is suppressed when using backup or restore parameter. In that case you can force screen output with `--output`.

The console screen output supports two formats:

* [JSON](#json-format):<br>
This is identical with the backup/restore [json file Format](#json-format) but printed on screen standard output.
* [Tasmota command](#tasmota-web-command-format):<br>
This outputs the most (but not all!) configuration data as Tasmota [web-console commands](https://tasmota.github.io/docs/Commands/).

#### JSON format

The default console output format is [JSON](#json-format) (optional you can force JSON backup format using `--output-format json`).

Example:

```bash
decode-config -c my.conf -s tasmota-4281 --group Wifi
```

will output data like

```json
{
  ...
  "hostname": "%s-%04d",
  "ip_address": [
    "0.0.0.0",
    "192.168.12.1",
    "255.255.255.0",
    "192.168.12.1"
  ],
  "ntp_server": [
    "ntp.localnet.home",
    "ntp2.localnet.home",
    "192.168.12.1"
  ],
  "sta_active": 0,
  "sta_config": 5,
  "sta_pwd": [
    "myWlAnPaszxwo!z",
    "myWlAnPaszxwo!z2"
  ],
  "sta_ssid": [
    "wlan.1",
    "my-wlan"
  ],
  "web_password": "myPaszxwo!z",
  "webserver": 2
  ...
}
```

This also allows direct processing on the command line, e.g. to display all `ntp_server` only

```bash
decode-config -c my.conf -s tasmota-4281 | jq '.ntp_server'
```

outputs

```json
[
  "ntp.localnet.home",
  "ntp2.localnet.home",
  "192.168.12.1"
]
```

> **Hint**  
JSON output contains all configuration data as default. To [filter](#filter-by-groups) the JSON output by functional groups, use the `-g` or `--group` parameter.

#### Tasmota web command format

**decode-config** is able to translate the configuration data to (most all) Tasmota web commands. To output your configuration as Tasmota commands use `--output-format command` (or the short form `-T cmnd`).

Example:

```bash
decode-config -c my.conf -s tasmota-4281 --group Wifi --output-format cmnd
```

```conf
# Wifi:
  AP 0
  Hostname %s-%04d
  IPAddress1 0.0.0.0
  IPAddress2 192.168.12.1
  IPAddress3 255.255.255.0
  IPAddress4 192.168.12.1
  NtpServer1 ntp.localnet.home
  NtpServer2 ntp2.localnet.home
  NtpServer3 192.168.12.1
  Password1 myWlAnPaszxwo!z
  Password2 myWlAnPaszxwo!z2
  SSId1 wlan.1
  SSId2 my-wlan
  WebPassword myPaszxwo!z
  WebServer 2
  WifiConfig 5
```

> **Note**  
A very few specific commands are [unsupported](#generated-tasmota-commands). These are commands from device-specific groups which are very dependent on the Tasmota program code whose implementation is very complex to keep in sync on Tasmota code changes - see also [Generated Tasmota commands](#generated-tasmota-commands).

##### Use of 'Backlog' for Tasmota commands

Because individual Tasmota commands such as `SetOption`, `WebColor` etc. are often repeat themselves and might want to be used together, commands of the same name can be summarized using the Tasmota `Backlog` command. The **decode-config** parameter `--cmnd-use-backlog` enables the use of Tasmota `Backlog`.

With the use of `--cmnd-use-backlog` our example configuration

```conf
# Wifi:
  AP 0
  Hostname %s-%04d
  IPAddress1 0.0.0.0
  IPAddress2 192.168.12.1
  IPAddress3 255.255.255.0
  IPAddress4 192.168.12.1
  NtpServer1 ntp.localnet.home
  NtpServer2 ntp2.localnet.home
  NtpServer3 192.168.12.1
  Password1 myWlAnPaszxwo!z
  Password2 myWlAnPaszxwo!z2
  SSId1 wlan.1
  SSId2 my-wlan
  WebPassword myPaszxwo!z
  WebServer 2
  WifiConfig 5
```

becomes to

```conf
# Wifi:
  AP 0
  Hostname %s-%04d
  Backlog IPAddress1 0.0.0.0;IPAddress2 192.168.12.1;IPAddress3 255.255.255.0;IPAddress4 192.168.12.1
  Backlog NtpServer1 ntp.localnet.home;NtpServer2 ntp2.localnet.home;NtpServer3 192.168.12.1
  Backlog Password1 myWlAnPaszxwo!z;Password2 myWlAnPaszxwo!z2
  Backlog SSId1 wlan.1;SSId2 my-wlan
  WebPassword myPaszxwo!z
  WebServer 2
  WifiConfig 5
```

`--cmnd-use-backlog` gets really interesting for `SetOptionxx`, `WebSensorxx`, `Sensorxx`, `Memxx`, `Gpioxx` and more...

### Filter by groups

The huge number of Tasmota configuration data can be overstrained and confusing, so the most of the configuration data are grouped into categories.

The following groups are available: `Control`, `Display`, `Domoticz`, `Internal`, `Knx`, `Light`, `Management`, `Mqtt`, `Power`, `Rf`, `Rules`, `Sensor`, `Serial`, `Setoption`, `Shutter`, `System`, `Timer`, `Wifi`, `Zigbee`

These are similary to the categories on [Tasmota Command Documentation](https://tasmota.github.io/docs/Commands/).

To filter outputs to a subset of groups, use the `-g` or `--group` parameter, concatenating the groups you want, e. g.

```bash
decode-config -s tasmota-4281 -c my.conf --output-format cmnd --group Main MQTT Management Wifi
```

Filtering by groups affects the entire output, regardless of whether screen output or backup file.

## Usage examples

### Using Tasmota binary configuration files

These examples use an online Tasmota device accessed over HTTP. The hostname of the Tasmota device is `tasmota-2f5d44-4281`

#### Backup an online Tasmota device via HTTP into a Tasmota configuration file

##### Use args to choice the file format

```bash
  decode-config -c my.conf -s tasmota-2f5d44-4281 --backup-type dmp --backup-file Config_@d_@v
```

##### Use file extension to choice the file format

```bash
decode-config -c my.conf -s tasmota-2f5d44-4281 --backup-file Config_@d_@v.dmp
```

#### Restore a Tasmota configuration file to an online Tasmota device via HTTP

```bash
decode-config -c my.conf -s http://tasmota-2f5d44-4281 --restore-file Config_@d_@v.dmp
```

### Using JSON editable file

These examples use an online Tasmota device that is accessed indirectly via MQTT.

In these examples, the MQTT server parameters are the same as those used by Tasmota itself:

* MQTT Server: `mybroker.example.com`
* MQTT Username: `mqttuser`
* MQTT Password: `myBrokerPaszxwo!z`
* Tasmota topic: `tele/tasmota_2F5D44`

#### Backup an online Tasmota device via MQTT into a JSON file

##### Use an unencrypted MQTT connection

MQTT server uses a non default port 42110

```bash
decode-config -s mqtt://mqttuser:myBrokerPaszxwo!z@mybroker.example.com:42110/tele/tasmota_2F5D44 --backup-file Config_2f5d44-4281.json
```

##### Use SSL/TLS MQTT connection

Limit the configuration data to the groups `Control`, `Management` and `SetOption`

```bash
decode-config -s mqtts://mqttuser:myBrokerPaszxwo!z@mybroker.example.com --fulltopic tele/tasmota_2F5D44 --backup-file Config_2f5d44-4281.json -g Control Management SetOption
```

#### Restore a JSON file to an online Tasmota device via MQTT

```bash
decode-config -s mqtts://mqttuser:myBrokerPaszxwo!z@mybroker.example.com/tele/tasmota_2F5D44 --restore-file Config_2f5d44-4281.json
```

### Use batch processing

Linux

```bash
for device in tasmota1 tasmota2 tasmota3; do ./decode-config -c my.conf -s $device -o Config_@d_@v
```

under Windows

```batch
for device in (tasmota1 tasmota2 tasmota3) do decode-config -c my.conf -s %device -o Config_@d_@v
```

will produce JSON configuration files for host tasmota1, tasmota2 and tasmota3 using friendly name and Tasmota firmware version for backup filenames.

## File Formats

**decode-config** handles the following three file formats for backup and restore:

### .dmp format

This is the original format used by Tasmota (created via the Tasmota web interface "*Configuration*" / "*Backup Configuration*" and can be read in with "*Configuration*" / "*Restore Configuration*". The format is binary encrypted.

This file format can be created by **decode-config** using the backup function (`--backup-file <filename>`) with the additional parameter `--backup-type dmp`.

### .json format

This format uses the [JSON](http://www.json.org/) notation and contains the complete configuration data in plain text, human readable and editable.

The .json format can be created by **decode-config** using the backup function (`--backup-file <filename>`) (for better identification you can append the optional parameter `--backup-type json`, but that's optional as json is the default backup format).

In contrast to the other two binary formats [.dmp](#dmp-format) and [.bin](#bin-format), this type of format also allows the [partial modification](#restore-subset-of-data) of configurations.

> **Note**  
The keys used within the JSON file are based on the variable names of Tasmota source code in [settings.h](https://github.com/arendst/Tasmota/blob/master/tasmota/include/tasmota_types.h) so they do not have the same naming as known for Tasmota web commands. However, since the variable names are self-explanatory, there should be no difficulties in assigning the functionality of the variables.

### .bin format

This format is binary with the same structure as the [.dmp](#dmp-format) format. The differences to .dmp are:

* .bin is decrypted
* .bin has 4 additional bytes at the end of the file

The .bin format can be created by **decode-config** using the backup function (`--backup-file <filename>`) with the additional parameter `--backup-type bin`.

This format is actually only used to view the configuration data directly in binary form without conversion.  
It is hardly possible to change the binary data, since a checksum is formed over the data and this would have to be calculated and adjusted in case of any change.

## Program parameter list

For better reading each short written parameter using a single dash `-` has a corresponding long version with two dashes `--`, eg. `--source` for `-s`.  
Note: Not even all double dash `--` parameter has a corresponding single dash one `-` but each single dash variant has a double dash equivalent.

A short list of possible program args is displayed using `-h` or `--help`.

### --full-help

For advanced help use parameter `-H` or `--full-help`:

```help
usage: decode-config.py [-s <filename|host|url>] [-p <password>]
                        [--fulltopic <topic>] [--cafile <file>]
                        [--certfile <file>] [--keyfile <file>] [--insecure]
                        [--keepalive <sec>] [-i <restorefile>]
                        [-o <backupfile>] [-t json|bin|dmp] [-E] [-e] [-F]
                        [--json-indent <indent>] [--json-compact]
                        [--json-show-pw] [--cmnd-indent <indent>]
                        [--cmnd-groups] [--cmnd-sort]
                        [--cmnd-use-rule-concat] [--cmnd-use-backlog]
                        [-c <configfile>] [-S] [-T json|cmnd|command]
                        [-g <groupname> [<groupname> ...]] [-w] [--dry-run]
                        [-h] [-H] [-v] [-V]

Backup/Restore Tasmota configuration data. Args that start with '--' (eg.
-s) can also be set in a config file (specified via -c). Config file syntax
allows: key=value, flag=true, stuff=[a,b,c] (for details, see syntax at
https://goo.gl/R74nmi). If an arg is specified in more than one place, then
commandline values override config file values which override defaults.

Source:
  Read/Write Tasmota configuration from/to

  -s, --source <filename|host|url>
                        source used for the Tasmota configuration (default:
                        None). Specify source type, path, file, user,
                        password, hostname, port and topic at once as an
                        URL. The URL must be in the form 'scheme://[username
                        [:password]@]host[:port][/topic]|pathfile'where
                        scheme is 'file' for a tasmota binary config file,
                        'http' for a Tasmota HTTP web connection and
                        'mqtt(s)' for Tasmota MQTT transport ('mqtts' uses a
                        TLS connection to MQTT server)
  -p, --password <password>
                        Web server password on HTTP source (set by Tasmota
                        'WebPassword' command), MQTT server password in MQTT
                        source (set by Tasmota 'MqttPassword' command)
                        (default: None)

MQTT:
  MQTT transport settings

  --fulltopic <topic>   Optional MQTT transport fulltopic used for accessing
                        Tasmota device (default: )
  --cafile <file>       Enables SSL/TLS connection: path to a or filename of
                        the Certificate Authority certificate files that are
                        to be treated as trusted by this client (default
                        None)
  --certfile <file>     Enables SSL/TLS connection: filename of a PEM
                        encoded client certificate file (default None)
  --keyfile <file>      Enables SSL/TLS connection: filename of a PEM
                        encoded client private key file (default None)
  --insecure            suppress verification of the MQTT server hostname in
                        the server certificate (default False)
  --keepalive <sec>     keepalive timeout for the client (default 60)

Backup/Restore:
  Backup & restore specification

  -i, --restore-file <restorefile>
                        file to restore configuration from (default: None).
                        Replacements: @v=firmware version from config,
                        @d=devicename, @f=friendlyname1, @h=hostname from
                        config, @H=device hostname (http source only)
  -o, --backup-file <backupfile>
                        file to backup configuration to, can be specified
                        multiple times (default: None). Replacements:
                        @v=firmware version from config, @d=devicename,
                        @f=friendlyname1, @h=hostname from config, @H=device
                        hostname (http source only), @F=configuration
                        filename from MQTT request (mqtt source only)
  -t, --backup-type json|bin|dmp
                        backup filetype (default: 'json')
  -E, --extension       append filetype extension for -i and -o filename
                        (default)
  -e, --no-extension    do not append filetype extension, use -i and -o
                        filename as passed
  -F, --force-restore   force restore even configuration is identical

JSON output:
  JSON format specification. To revert an option, insert "dont" or "no"
  after "json", e.g. --json-no-indent, --json-dont-show-pw

  --json-indent <indent>
                        pretty-printed JSON output using indent level
                        (default: 'None'). -1 disables indent.
  --json-compact        compact JSON output by eliminate whitespace
  --json-show-pw        unhide passwords (default)

Tasmota command output:
  Tasmota command output format specification. To revert an option, insert
  "dont" or "no" after "cmnd", e.g. --cmnd-no-indent, --cmnd-dont-sort

  --cmnd-indent <indent>
                        Tasmota command grouping indent level (default:
                        '2'). 0 disables indent
  --cmnd-groups         group Tasmota commands (default)
  --cmnd-sort           sort Tasmota commands (default)
  --cmnd-use-rule-concat
                        use rule concatenation with + for Tasmota 'Rule'
                        command
  --cmnd-use-backlog    use 'Backlog' for Tasmota commands as much as
                        possible

Common:
  Optional arguments

  -c, --config <configfile>
                        program config file - can be used to set default
                        command parameters (default: None)
  -S, --output          display output regardsless of backup/restore usage
                        (default do not output on backup or restore usage)
  -T, --output-format json|cmnd|command
                        display output format (default: 'json')
  -g, --group <groupname>
                        limit data processing to command groups (default no
                        filter)
  -w, --ignore-warnings
                        do not exit on warnings. Not recommended, used by
                        your own responsibility!
  --dry-run             test program without changing configuration data on
                        device or file

Info:
  Extra information

  -h, --help            show usage help message and exit
  -H, --full-help       show full help message and exit
  -v, --verbose         produce more output about what the program does
  -V, --version         show program's version number and exit

The arguments -s <filename|host|url> must be given.
```

> **Note**  
If you miss parameters here that are already in use, don't worry, they are still there.  
For details see [Obsolete parameters](#obsolete-parameters)

### Parameter notes

* Filename replacement macros **@h** and **@H**:
  * **@h**
The **@h** replacement macro uses the hostname configured with the Tasomta Wifi `Hostname <host>` command (defaults to `%s-%04d`). It will not use the network hostname of your device because this is not available when working with files only (e.g. `--source <filename>` as source).
To prevent having an useless % in your filename, **@h** will not replaced by hostname if this contains '%' characters.
  * **@H**
If you want to use the network hostname within your filename, use the **@H** replacement macro instead - but be aware this will only replaced if you are using a network device as source (`<hostname>`, `<ip>`, `<url>`); it will not work when using a file as source (`<filename>`)

### Obsolete parameters

The parameters listed here continue to work and are supported, but are no longer listed in the parameter list:

#### Obsolete source parameters

The following source selection parameters are completely replaced by a single used [`-s`](#--full-help) or [`--source`](#--full-help) parameter; use [`-s`](#--full-help) or [`--source`](#--full-help) with a [http-url](https://en.wikipedia.org/wiki/URL):

* `-f`, `--file`, `--tasmota-file`, `tasmotafile` `<filename>`  
file used for the Tasmota configuration (default: None)'
* `-d`, `--device`, `--host` `<host|url>`  
hostname, IP-address or url used for the Tasmota configuration (default: None)
* `-P`, `--port` `<port>`  
TCP/IP port number to use for the host connection (default: 80)
* `-u`, `--username` `<username>`  
host HTTP access username (default: admin)

#### Obsolete JSON formating parameters

* `--json-unhide-pw` same as `--json-show-pw`
* `--json-hide-pw` same as `--json-dont-show-pw`
* `--json-sort` sorts JSON output (this is the default)
* `--json-unsort` prevents JSON sorting

## Generated Tasmota commands

The following table shows the Tasmota command generated by **decode-config**:

* **Supported**  
These commands will be generated using parameter `--output-format cmnd`.
* **Ad hoc**  
These Tasmota commands are used for immediate action and do not change settings - so these cannot be created.
* **Unsupported**  
These Tasmota commands are unsupported and not implemented in **decode-config**

| Group          | Supported                   | *Ad hoc*               |`Unsupported`|
|----------------|-----------------------------|------------------------|-------------|
| **Control**    | BlinkCount                  | *Backlog*              |             |
|                | BlinkTime                   | *Buzzer*               |             |
|                | ButtonDebounce              | *FanSpeed*             |             |
|                | DevGroupName                | *LedPower*             |             |
|                | DevGroupShare               |                        |             |
|                | DevGroupTie                 |                        |             |
|                | Interlock                   |                        |             |
|                | LedMask                     |                        |             |
|                | LedPwmMode<x\>              |                        |             |
|                | LedPwmOn                    |                        |             |
|                | LedPwmOff                   |                        |             |
|                | LedState                    |                        |             |
|                | Power<x\>                   |                        |             |
|                | PowerOnState                |                        |             |
|                | PulseTime<x\>               |                        |             |
|                | SwitchDebounce              |                        |             |
|                | SwitchMode<x\>              |                        |             |
|                | Webbutton<x\>               |                        |             |
|                | WCAEC<sup>2</sup>           |                        |             |
|                | WCAECDSP<sup>2</sup>        |                        |             |
|                | WCAECValue<sup>2</sup>      |                        |             |
|                | WCAELevel<sup>2</sup>       |                        |             |
|                | WCAGCGain<sup>2</sup>       |                        |             |
|                | WCAWB<sup>2</sup>           |                        |             |
|                | WCAWBGain<sup>2</sup>       |                        |             |
|                | WCBPC<sup>2</sup>           |                        |             |
|                | WCBrightness<sup>2</sup>    |                        |             |
|                | WCClock<sup>2</sup>         |                        |             |
|                | WCColorbar<sup>2</sup>      |                        |             |
|                | WCContrast<sup>2</sup>      |                        |             |
|                | WCDCW<sup>2</sup>           |                        |             |
|                | WCFeature<sup>2</sup>       |                        |             |
|                | WCFlip<sup>2</sup>          |                        |             |
|                | WCGainCeiling<sup>2</sup>   |                        |             |
|                | WCGammaCorrect<sup>2</sup>  |                        |             |
|                | WCLensCorrect<sup>2</sup>   |                        |             |
|                | WCMirror<sup>2</sup>        |                        |             |
|                | WCResolution<sup>2</sup>    |                        |             |
|                | WCRtsp<sup>2</sup>          |                        |             |
|                | WCSAuth<sup>2</sup>         |                        |             |
|                | WCSaturation<sup>2</sup>    |                        |             |
|                | WCSpecialEffect<sup>2</sup> |                        |             |
|                | WCStream<sup>2</sup>        |                        |             |
|                | WCWBMode<sup>2</sup>        |                        |             |
|                | WCWPC<sup>2</sup>           |                        |             |
| **Management** | DeepSleepTime               | *Delay*                |             |
|                | DeviceName                  | *Gpios*                |             |
|                | Emulation                   | *I2Cscan*              |             |
|                | FriendlyName<x\>            | *Modules*              |             |
|                | Gpio<x\>                    | *Reset*                |             |
|                | I2CDriver<x\>               | *Restart*              |             |
|                | Ifx                         | *State*                |             |
|                | IfxBucket                   | *Status*               |             |
|                | IfxHost                     | *Upgrade*              |             |
|                | IfxPassword                 | *Upload*               |             |
|                | IfxPort                     | *SSPMLog<sup>2</sup>*  |             |
|                | IfxUser                     | *SSPEnergy<sup>2</sup>*|             |
|                | IfxRP                       | *SSPHistory<sup>2</sup>*|            |
|                | IfxPeriod                   | *SSPScan<sup>2</sup>*  |             |
|                | IfxSensor                   | *SSPIamHere<sup>2</sup>*|            |
|                | L1MusicSync                 |                        |             |
|                | LogHost                     |                        |             |
|                | LogPort                     |                        |             |
|                | Module                      |                        |             |
|                | Module2                     |                        |             |
|                | MqttLog                     |                        |             |
|                | NtpServer<x\>               |                        |             |
|                | OtaUrl                      |                        |             |
|                | Pwm<x\>                     |                        |             |
|                | PwmFrequency                |                        |             |
|                | PwmRange                    |                        |             |
|                | RtcNtpserver                |                        |             |
|                | SaveData                    |                        |             |
|                | SerialLog                   |                        |             |
|                | Sleep                       |                        |             |
|                | SSPMDisplay<sup>2</sup>     |                        |             |
|                | SysLog                      |                        |             |
|                | Template                    |                        |             |
|                | Time                        |                        |             |
|                | TimeSTD                     |                        |             |
|                | TimeDST                     |                        |             |
|                | Timezone                    |                        |             |
|                | TouchThres<sup>2</sup>      |                        |             |
|                | TuyaMCU                     |                        |             |
|                | TuyaTempSetRes              |                        |             |
|                | WebLog                      |                        |             |
|                | WebTime                     |                        |             |
| **WiFi**       | CORS                        | *AP*                   |             |
|                | DnsTimeout                  | *Ping<x\>*             |             |
|                | Ethernet<sup>2</sup>        | *WebSend*              |             |
|                | EthAddress<sup>2</sup>      | *Publish*              |             |
|                | EthClockMode<sup>2</sup>    | *Publish2*             |             |
|                | EthType<sup>2</sup>         |                        |             |
|                | EthIPAddress<sup>2</sup>    |                        |             |
|                | EthSubnetmask<sup>2</sup>   |                        |             |
|                | EthGateway<sup>2</sup>      |                        |             |
|                | EthDNSServer<sup>2</sup>    |                        |             |
|                | EthDNSServer2<sup>2</sup>   |                        |             |
|                | Hostname                    |                        |             |
|                | IPAddress<x\>               |                        |             |
|                | Password<x\>                |                        |             |
|                | RgxAddress                  |                        |             |
|                | RgxNAPT                     |                        |             |
|                | RgxPassword                 |                        |             |
|                | RgxSsid                     |                        |             |
|                | RgxState                    |                        |             |
|                | RgxSubnet                   |                        |             |
|                | Ssid<x\>                    |                        |             |
|                | WebColor<x\>                |                        |             |
|                | WebPassword                 |                        |             |
|                | WebRefresh                  |                        |             |
|                | WebSensor<x\>               |                        |             |
|                | WebServer                   |                        |             |
|                | Wifi                        |                        |             |
|                | WifiConfig                  |                        |             |
|                | WifiPower                   |                        |             |
| **MQTT**       | ButtonRetain                | *Subscribe*            |             |
|                | ButtonTopic                 | *Unsubscribe*          |             |
|                | FullTopic                   |                        |             |
|                | GroupTopic<x\>              |                        |             |
|                | InfoRetain                  |                        |             |
|                | MqttClient                  |                        |             |
|                | MqttFingerprint             |                        |             |
|                | MqttHost                    |                        |             |
|                | MqttKeepAlive               |                        |             |
|                | MqttPassword                |                        |             |
|                | MqttPort                    |                        |             |
|                | MqttRetry                   |                        |             |
|                | MqttUser                    |                        |             |
|                | MqttTimeout                 |                        |             |
|                | MqttWifiTimeout             |                        |             |
|                | PowerRetain                 |                        |             |
|                | Prefix<x\>                  |                        |             |
|                | SensorRetain                |                        |             |
|                | StateRetain                 |                        |             |
|                | StateText<x\>               |                        |             |
|                | StatusRetain                |                        |             |
|                | SwitchRetain                |                        |             |
|                | SwitchTopic                 |                        |             |
|                | TelePeriod                  |                        |             |
|                | Topic                       |                        |             |
| **Rules**      | CalcRes                     | *Add<x\>*              |             |
|                | Mem<x\>                     | *Event*                |             |
|                | Rule<x\>                    | *Mult<x\>*             |             |
|                | Script                      | *RuleTimer<x\>*        |             |
|                |                             | *Scale<x\>*            |             |
|                |                             | *Sub<x\>*              |             |
|                |                             | *Var<x\>*              |             |
| **Telegram**   | TmState                     |                        |             |
| **Timer**      | Latitude                    |                        |             |
|                | Longitude                   |                        |             |
|                | Timers                      |                        |             |
|                | Timer<x\>                   |                        |             |
| **Sensor**     | Altitude                    | *Bh1750MTime<x\>*      | `AdcParam`  |
|                | AmpRes                      | *GlobalHum*            |             |
|                | AS3935AutoNF                | *GlobalTemp*           |             |
|                | AS3935AutoDisturber         | *Sensor27*             |             |
|                | AS3935AutoNFMax             | *Sensor50*             |             |
|                | AS3935MQTTEvent             | *Sensor52*             |             |
|                | AS3935NFTime                | *Sensor53*             |             |
|                | AS3935NoIrqEvent            | *Sensor60<sup>1</sup>* |             |
|                | AS3935DistTime              |                        |             |
|                | AS3935SetMinStage           |                        |             |
|                | Bh1750Resolution<x\>        |                        |             |
|                | Counter<x\>                 |                        |             |
|                | CounterDebounce             |                        |             |
|                | CounterDebounceLow          |                        |             |
|                | CounterDebounceHigh         |                        |             |
|                | CounterType<x\>             |                        |             |
|                | HumOffset                   |                        |             |
|                | HumRes                      |                        |             |
|                | PressRes                    |                        |             |
|                | OT_Flags                    |                        |             |
|                | OT_Save_Setpoints           |                        |             |
|                | OT_TBoiler                  |                        |             |
|                | OT_TWater                   |                        |             |
|                | Sensor13                    |                        |             |
|                | Sensor15                    |                        |             |
|                | Sensor18                    |                        |             |
|                | Sensor20                    |                        |             |
|                | Sensor29                    |                        |             |
|                | Sensor34                    |                        |             |
|                | Sensor40                    |                        |             |
|                | Sensor54                    |                        |             |
|                | Sensor68                    |                        |             |
|                | Sensor96                    |                        |             |
|                | Shift595DeviceCount         |                        |             |
|                | SpeedUnit                   |                        |             |
|                | TempRes                     |                        |             |
|                | TempOffset                  |                        |             |
|                | VoltRes                     |                        |             |
|                | WattRes                     |                        |             |
|                | WeightRes                   |                        |             |
|                | Wiper<x\>                   |                        |             |
| **Power**      | AmpRes                      | *CurrentSet*           |             |
|                | CurrentCal                  | *FrequencySet*         |             |
|                | CurrentHigh                 | *ModuleAddress*        |             |
|                | CurrentLow                  | *PowerSet*             |             |
|                | EnergyRes                   | *Status8*              |             |
|                | EnergyToday                 | *Status9*              |             |
|                | EnergyTotal                 | *VoltageSet*           |             |
|                | EnergyYesterday             |                        |             |
|                | FreqRes                     |                        |             |
|                | MaxPower                    |                        |             |
|                | MaxPowerHold                |                        |             |
|                | MaxPowerWindow              |                        |             |
|                | PowerCal                    |                        |             |
|                | PowerDelta                  |                        |             |
|                | PowerHigh                   |                        |             |
|                | PowerLow                    |                        |             |
|                | Tariff<x\>                  |                        |             |
|                | VoltageCal                  |                        |             |
|                | VoltageHigh                 |                        |             |
|                | VoltageLow                  |                        |             |
|                | VoltRes                     |                        |             |
|                | WattRes                     |                        |             |
| **Light**      | DimmerRange                 | *Channel<x\>*          | `Color<x>`  |
|                | DimmerStep                  | *CT*                   | `Dimmer`    |
|                | Fade                        | *CTRange*              |             |
|                | LedTable                    | *HsbColor*             |             |
|                | Pixels                      | *Led<x\>*              |             |
|                | PWMDimmerPWMs               | *Palette*              |             |
|                | RGBWWTable                  | *White*                |             |
|                | Rotation                    | *VirtualCT*            |             |
|                | Scheme                      |                        |             |
|                | ShdLeadingEdge              |                        |             |
|                | ShdWarmupBrightness         |                        |             |
|                | ShdWarmupTime               |                        |             |
|                | Speed                       |                        |             |
|                | StepPixels                  |                        |             |
|                | Wakeup                      |                        |             |
|                | WakeupDuration              |                        |             |
| **RF**         | RfProtocol                  | *RfRaw*                | `RfCode`    |
|                | RfTimeOut                   |                        | `RfHigh`    |
|                |                             |                        | `RfHost`    |
|                |                             |                        | `RfKey<x>`  |
|                |                             |                        | `RfLow`     |
|                |                             |                        | `RfSync`    |
| **IR**         |                             | *IRsend<x\>*           |             |
|                |                             | *IRhvac*               |             |
| **SetOption**  | SetOption<x\>               |                        |             |
| **Serial**     | Baudrate                    | *SerialSend<x\>*       |             |
|                | ModbusBaudrate              | *SSerialSend<x\>*      |             |
|                | ModbusSerialConfig          | *TCPStart*             |             |
|                | SBaudrate                   | *TuyaSend<x\>*         |             |
|                | SerialConfig                |                        |             |
|                | SerialDelimiter             |                        |             |
|                | SSerialConfig               |                        |             |
|                | SSerialSend9                |                        |             |
|                | TCPBaudrate                 |                        |             |
|                | TCPConfig                   |                        |             |
| **Domoticz**   | DomoticzIdx<x\>             |                        |             |
|                | DomoticzKeyIdx<x\>          |                        |             |
|                | DomoticzSensorIdx<x\>       |                        |             |
|                | DomoticzSwitchIdx<x\>       |                        |             |
|                | DomoticzUpdateTimer         |                        |             |
| **KNX**        | KNX_ENABLED                 | *KnxTx_Cmnd<x\>*       | `KNX_PA`    |
|                | KNX_ENHANCED                | *KnxTx_Val<x\>*        | `KNX_GA<x>` |
|                |                             |                        | `KNX_CB<x>` |
| **Display**    | DisplayAddress              | *Display*              |             |
|                | DisplayDimmer               | *DisplayText*          |             |
|                | DisplayILIMode              |                        |             |
|                | DisplayInvert               |                        |             |
|                | DisplayMode                 |                        |             |
|                | DisplayModel                |                        |             |
|                | DisplayRefresh              |                        |             |
|                | DisplaySize                 |                        |             |
|                | DisplayType                 |                        |             |
|                | DisplayRotate               |                        |             |
|                | DisplayCols                 |                        |             |
|                | DisplayRows                 |                        |             |
|                | DisplayFont                 |                        |             |
|                | DisplayWidth                |                        |             |
|                | DisplayHeight               |                        |             |
| **Shutter**    | ShutterButton<x\>           | *ShutterClose<x\>*     |             |
|                | ShutterCalibration<x\>      | *ShutterFrequency<x\>* |             |
|                | ShutterCloseDuration<x\>    | *ShutterOpen<x\>*      |             |
|                | ShutterEnableEndStopTime<x\>| *ShutterSetClose<x\>*  |             |
|                | ShutterInvert<x\>           | *ShutterStop<x\>*      |             |
|                | ShutterInvertWebButtons<x\> | *ShutterStopClose<x\>* |             |
|                | ShutterLock<x\>             | *ShutterStopOpen<x\>*  |             |
|                | ShutterMode<x\>             | *ShutterStopPosition<x\>*|           |
|                | ShutterMotorDelay<x\>       | *ShutterStopToggle<x\>*|             |
|                | ShutterMotorStop            | *ShutterStopToggleDir<x\>*|          |
|                | ShutterOpenDuration<x\>     | *ShutterToggle<x\>*    |             |
|                | ShutterPosition<x\>         | *ShutterToggleDir<x\>* |             |
|                | ShutterPWMRange<x\>         |                        |             |
|                | ShutterRelay<x\>            |                        |             |
|                | ShutterSetHalfway<x\>       |                        |             |
|                | ShutterTiltConfig<x\>       |                        |             |
| **Telegram**   | TmChatId                    | *TmPoll*               |             |
|                | TmState                     | *TmSend*               |             |
|                | TmToken                     |                        |             |
| **Zigbee**     | ZbConfig                    | *ZbBind*               |             |
|                |                             | *ZbForget*             |             |
|                |                             | *ZbLight*              |             |
|                |                             | *ZbName*               |             |
|                |                             | *ZbPermitJoin*         |             |
|                |                             | *ZbPing*               |             |
|                |                             | *ZbSend*               |             |
|                |                             | *ZbStatus<x\>*         |             |
|                |                             | *ZbUnbind*             |             |
| **Bluetooth**  |                             | *- all -*              |             |
| **Stepper Motors** |                         | *- all -*              |             |
| **MP3 Player** |                             | *- all -*              |             |

> **Notes**  
<sup>1</sup> `Sensor60 13` sets the latitude/longitude, use `Latitude` and `Logitude` command instead.  
<sup>2</sup> ESP32 only

## Program return codes

**decode-config** returns the following codes:

* **0** - successful:  
The process has successful finished  

* **1** = restore skipped:  
Unchanged data, restore not executed  

* **2** = program argument error:  
Wrong program parameter used (data source missing)  

* **3** = file not found  

* **4** = data size mismatch:  
The data size read from source does not match the excpected size  

* **5** = data CRC error:  
The read data contains wrong CRC  

* **6** = unsupported configuration version:  
The source data contains data from an unsupported (Sonoff-)Tasmota version  

* **7** = configuration file read error:  
There was an error during read of configuration source file  

* **8** = JSON file decoding error:  
There was an error within the read JSON file  

* **9** = restore file data error:  
Error occured by writing new binary data  

* **10** = device data download error:  
Source device connected but configuration data could not be downloaded (WebServer missing, disabled)  

* **11** = device data upload error:  
Source device connected but configuration data could not be uploaded (WebServer missing, disabled, connection lost...)  

* **12** = invalid configuration data:  
The configuration data source contains invalid basic data (wrong platform id...)  

* **20** = python module missing:  
A neccessary python library module is missing  

* **21** = internal error:  
An unexpected internal error occured  

* **22** = HTTP connection error:  
Source device HTTP connection lost or unavailable  

* **23** = MQTT connection error:  
MQTT server connection error  

* **24...** = python library exit code:  
An unexpected internal library error occured  

* **4xx**/**5xx** = HTTP errors  
