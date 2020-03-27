# decode-config

Convert, backup and restore configuration data of devices flashed with [Tasmota firmware](https://github.com/arendst/Tasmota).

[![development](https://img.shields.io/badge/development-v8.2.0.1-blue.svg)](https://github.com/tasmota/decode-config/tree/development)
[![GitHub download](https://img.shields.io/github/downloads/tasmota/decode-config/total.svg)](https://github.com/tasmota/decode-config/releases/latest)
[![License](https://img.shields.io/github/license/tasmota/decode-config.svg)](LICENSE)

If you like **decode-config** give it a star or fork it:

[![GitHub stars](https://img.shields.io/github/stars/tasmota/decode-config.svg?style=social&label=Star)](https://github.com/tasmota/decode-config/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/tasmota/decode-config.svg?style=social&label=Fork)](https://github.com/tasmota/decode-config/network)

In comparison with the [Tasmota](https://github.com/arendst/Tasmota) build-in "Backup/Restore Configuration" function the **decode-config** tool:

* uses a human readable and editable [JSON](http://www.json.org/)-format for backup/restore
* can restore previously backed up and modified [JSON](http://www.json.org/)-format files
* is able to process any subsets of configuration data
* can convert data from older Tasmota versions (from version v5.10.0) to a newer one and vice versa
* is able to create [Tasmota](https://github.com/arendst/Tasmota) compatible command list for the most available commands

Comparing backup files created by **decode-config** and *.dmp files created by [Tasmota](https://github.com/arendst/Tasmota) "Backup/Restore Configuration":

| Configuration           | decode-config JSON file | Tasmota *.dmp file |
|:------------------------|:-----------------------:|:------------------:|
| encrypted               |           No            |         Yes        |
| readable                |           Yes           |         No         |
| editable                |           Yes           |         No         |
| batch processing        |           Yes           |         No         |
| Backup/Restore subsets  |           Yes           |         No         |

**decode-config** is compatible with [Tasmota](https://github.com/arendst/Tasmota) starting from v5.10.0 up to now.

## Content

**This is the developer branch which contains decode-config matching the latest Tasmota developer version.**

This branch does not contain any binaries. If you want to use a precompiled **decode-config** binary
you can either use binaries from [master branch](https://github.com/tasmota/decode-config/tree/master) or
latest [Release](https://github.com/tasmota/decode-config/releases).

> If you want to run the development **decode-config.py** from this branch, you need an
installed [Python](https://en.wikipedia.org/wiki/Python_(programming_language)) environment.
See [Running as Python script](#running-as-python-script) for more details.

### Files

| File                     | Description |
|:-------------------------|:------------------------------------------------------------------------|
| `build`                  | contains files to build executables                                     |
| `decode-config.py`       | Python source file running under your local Python environment          |
| `README.md`              | This content                                                            |

- [decode-config](#decode-config)
  - [Content](#content)
    - [Files](#files)
  - [Running the program](#running-the-program)
    - [Prerequisite](#prerequisite)
    - [Running as Python script](#running-as-python-script)
      - [Linux](#linux)
      - [Windows 10](#windows-10)
      - [MacOS](#macos)
      - [All OS](#all-os)
  - [File Formats](#file-formats)
    - [.dmp Format](#dmp-format)
    - [.json Format](#json-format)
    - [.bin Format](#bin-format)
    - [File extensions](#file-extensions)
  - [Usage](#usage)
    - [Test run](#test-run)
    - [Basics](#basics)
    - [Save backup file](#save-backup-file)
    - [Restore backup file](#restore-backup-file)
    - [Output to screen](#output-to-screen)
      - [JSON output](#json-output)
      - [Tasmota command output](#tasmota-command-output)
    - [Filter data](#filter-data)
    - [Parameter configuration file](#parameter-configuration-file)
    - [More arguments](#more-arguments)
      - [Parameter notes](#parameter-notes)
    - [Examples](#examples)
      - [Parameter config file](#parameter-config-file)
        - [my.conf](#myconf)
      - [Using Tasmota binary configuration files](#using-tasmota-binary-configuration-files)
      - [Use batch processing](#use-batch-processing)

## Running the program

The program does not have a graphical user interface (GUI), you have to run it from your OS command line using [program arguments](#more-arguments).

**decode-config** needs a [Python](https://en.wikipedia.org/wiki/Python_(programming_language)) environment to run.
If you don't want to install Python you can either use the binaries from [master branch](https://github.com/tasmota/decode-config/tree/master) or
latest [Release](https://github.com/tasmota/decode-config/releases).

### Prerequisite

[Tasmota](https://github.com/arendst/Tasmota) provides its configuration data by http request only. To receive and send configuration data from Tasmota devices directly the http WebServer in Tasmota must be enabled:

* when using your own compiled firmware you have to compile your firmware with web-server (`#define USE_WEBSERVER` and `#define WEB_SERVER 2`).
* enable web-server in admin mode (command [WebServer 2](https://tasmota.github.io/docs/#/Commands?id=wi-fi))

> Note: Using MQTT for exchanging Tasmota configuration data is not support by Tasmota itself; so **decode-config** is unable using this way.

### Running as Python script

If you want to run **decode-config.py** from this development branch, an installed [Python](https://en.wikipedia.org/wiki/Python_(programming_language)) environment is neccessary.

> Note: Due to the [Python 2.7 EOL](https://github.com/python/devguide/pull/344) in Jan 2020 Python 2.x is no longer supported.

#### Linux

Install [Python 3.x](https://www.python.org/downloads/), Pip and follow [library installation for all OS](#all-os) below.

```bash
sudo apt-get install python3 python3-pip
```

#### Windows 10

Install [Python 3.x](https://www.python.org/downloads/windows/) as described and follow [library installation for all OS](#all-os) below.

#### MacOS

Install [Python 3.x](https://www.python.org/downloads/mac-osx/) as described and follow [library installation for all OS](#all-os) below.

#### All OS

After python and pip is installed, install dependencies:

```bash
pip3 install requests configargparse
```

## File Formats

**decode-config** handles the following backup/restore file formats:

### .dmp Format

This format is binary encrypted and is identical to a Tasmota configuration file saved by Tasmota web interface using "Configuration/Backup Configuration".

### .json Format

This format is decrypted, human readable, editable and contains the configuration data in [JSON](http://www.json.org/)-format.
This file format will be created by **decode-config** using the `--backup-file` with `--backup-type json` parameter (that's the default) and can also be used for the `--restore-file` parameter.

> Note: The keys used within the JSON file are based on the variable names of Tasmota source code in [settings.h](https://github.com/arendst/Tasmota/blob/master/tasmota/settings.h) so they do not have the same naming as known for Tasmota web commands. However, since the variable names are self-explanatory, there should be no difficulties in assigning the functionality of the variables.

### .bin Format

This format is binary decrypted. The difference to the original Tasmota format is on the one hand the decrypted form of the binary data and on the other hand an additional 4 attached bytes to distinguish between the original [.dmp File Format](#dmp-format) and this .bin format.
The decrypted binary format allows viewing and changing (using a hex editor) the pure Tasmota configuration binary data based on the address information in the Tasmota source code (tasmota/settings.h).

This file format will be created by **decode-config** using the `--backup-file` with `--backup-type bin` parameter and can also be used for the `--restore-file` parameter.

### File extensions

File extensions will be choose based on file contents and/or `--backup-type` parameter. You don't need to append exensions for your file.
If you want to use your own extensions, disable auto extension by using the `--no-extension` parameter.

## Usage

For an overview start the program without any parameter and you will get a small help screen.  
For full help start the program with parameter `-H`: `decode-config -H`

> Note: Replace the program name `decode-config` within examples with your one, e.g. `decode-config.py` running as Python executable, `decode-config_win64` for Windows or `decode-config_mac`under MacOS.

### Test run

To test your parameter you can prevent writing any changes to your device or file by appending `--dry-run`:

```bash
decode-config -d tasmota-4281 -i backupfile --dry-run
```

### Basics

At least pass a source where you want to read the configuration data from using `-f <filename>` or `-d <host>`:

The source can be either a

* device hostname or IP using the `-d <host>` parameter
* `.dmp` configuration file using `-f <filename>` parameter

Examples:

```bash
decode-config -d tasmota-4281
decode-config -d 192.168.10.92
decode-config -f tasmota-4281.dmp
```

will output a human readable configuration in [JSON](http://www.json.org/)-format:

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

### Save backup file

To save the output as backup file use `--backup-file <filename>`.

You can use placeholders **@v** for _Tasmota Version_, **@f** for first _Friendlyname_ and **@h** or **@H** for _Hostname_:

```bash
decode-config -d tasmota-4281 --backup-file Config_@f_@v
```

If your Tasmota web interface is protected by WebPassword command use

```bash
decode-config -d tasmota-4281 -p <yourpassword> --backup-file Config_@f_@v
```

This will create a file like `Config_Tasmota_8.2.0.json` (the part `Tasmota` and `8.2.0` will choosen related to your device configuration).

### Restore backup file

Reading back a previously saved backup file use the `--restore-file <filename>` parameter. This will read the (possibly changed) configuration data from this file and send it back to the source device or filename.

To restore the previously save backup file `Config_Tasmota_8.2.0.json` to device `tasmota-4281` use:

```bash
decode-config -d tasmota-4281 --restore-file Config_Tasmota_8.2.0
```

or

```bash
decode-config -d tasmota-4281 --restore-file Config_@f_@v
```

with password set by WebPassword:

```bash
decode-config -d tasmota-4281 -p <yourpassword> --restore-file Config_@f_@v
```

> Note: For JSON file formats you can use files containing a subset of configuration data only. For example: You want to change the data for location (altitude, latitude, longitude) only, use a JSON file with the content

```json
{
  "altitude": 0,
  "latitude": 48.85836,
  "longitude": 2.294442
}
```

Be aware to keep the JSON-format valid. For example: When cutting unnecessary content from a given JSON backup file, consider to remove the last comma on same indent level:

Invalid JSON format (useless comma in line 3: `...2.294442,`):

```json
{
  "latitude": 48.85836,
  "longitude": 2.294442,
}
```

Valid JSON format:

```json
{
  "latitude": 48.85836,
  "longitude": 2.294442
}
```

### Output to screen

Output to screen is the default when calling the program without any backup or restore parameter. Screen output is suppressed if using any backup or restore parameter. In that case you can force screen output by using the `--output` parameter.

#### JSON output

The default backup format is [JSON](#json-format). In any case you can force JSON backup format using the `--output-format json` parameter.

Example:

```bash
decode-config -d tasmota-4281 -c my.conf -x Wifi --output-format json
```

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

> Note: JSON output contains all configuration data as default. To [filter](#filter-data) the JSON output use the `-g` or `--group` parameter.

#### Tasmota command output

**decode-config** is able to translate the configuration data to (most all) Tasmota commands. To output your configuration as Tasmota commands use `--output-format cmnd` or `--output-format command`.

Example:

```bash
decode-config -d tasmota-4281 -c my.conf -g Wifi --output-format cmnd
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
  SSId2 wlan.1
  WebPassword myPaszxwo!z
  WebServer 2
  WifiConfig 5
```

> Note: A very few specific module commands (like MPC230xx, KNX and some display commands) are not supported.

### Filter data

The huge number of Tasmota configuration data can be overstrained and confusing, so the most of the configuration data are grouped into categories.

With **decode-config** the following categories are available:   `Display`, `Domoticz`, `Internal`, `KNX`, `Led`, `Logging`, `MCP230xx`, `MQTT`, `Main`, `Management`, `Pow`, `Sensor`, `Serial`, `SetOption`, `RF`, `System`, `Timers`, `Wifi`

These are similary to the categories on [Tasmota Command Wiki](https://tasmota.github.io/docs/#/Commands?id=command-list).

To filter outputs to a subset of groups use the `-g` or `--group` arg concatenating the grooup you want, e. g.

```bash
decode-config -d tasmota-4281 -c my.conf --output-format cmnd --group Main MQTT Management Wifi
```

### Parameter configuration file

Program parameter starting with `--` (eg. `--file`) can also be set into parameter configration file (specified via `-c` parameter) so you can write ofte used program parameter into your own file.

For example: The http authentication credentials `--username` and `--password` is predestinated to store it in a file instead using it on your command line as argument - also JSON intend can be configured once in your own parameter file:

```conf
[source]
username = admin
password = myPaszxwo!z

[JSON]
json-indent 2
```

Save this text file as e.g. `my.conf` and use it with `-c` parameter:

```bash
decode-config -c my.conf -d tasmota-4281
```

Config file syntax allows: key=value, flag=true, stuff=[a,b,c].
For details see [https://pypi.org/project/ConfigArgParse](https://pypi.org/project/ConfigArgParse/)).

If a parameter is specified in more than one place (parameter file and command line) then commandline value will overrule the parameter file value. This is usefull if you use the same argument or a basic set of arguments and want to change a parameter once without the need to edit your parameter configuration file.

### More arguments

For better reading each short written arg (minus sign `-`) has a corresponding long version (two minus signs `--`), eg. `--device` for `-d` or `--file` for `-f` (note: not even all `--` arg has a corresponding `-` one).

A short list of possible program args is displayed using `-h` or `--help`.

For advanced help use `-H` or `--full-help`:

```help
usage: decode-config.py [-f <filename>] [-d <host>] [-P <port>]
                        [-u <username>] [-p <password>] [-i <filename>]
                        [-o <filename>] [-t json|bin|dmp] [-E] [-e] [-F]
                        [--json-indent <indent>] [--json-compact]
                        [--json-hide-pw] [--json-show-pw]
                        [--cmnd-indent <indent>] [--cmnd-groups]
                        [--cmnd-nogroups] [--cmnd-sort] [--cmnd-unsort]
                        [-c <filename>] [-S] [-T json|cmnd|command]
                        [-g {Control,Display,Domoticz,Internal,Knx,Light,Management,Mqtt,Power,Rf,Rules,Sensor,Serial,Setoption,Shutter,System,Timer,Wifi} [{Control,Display,Domoticz,Internal,Knx,Light,Management,Mqtt,Power,Rf,Rules,Sensor,Serial,Setoption,Shutter,System,Timer,Wifi} ...]]
                        [--ignore-warnings] [--dry-run] [-h] [-H] [-v] [-V]

Backup/Restore Tasmota configuration data. Args that start with '--' (eg. -f)
can also be set in a config file (specified via -c). Config file syntax
allows: key=value, flag=true, stuff=[a,b,c] (for details, see syntax at
https://goo.gl/R74nmi). If an arg is specified in more than one place, then
commandline values override config file values which override defaults.

Source:
  Read/Write Tasmota configuration from/to

  -f, --file, --tasmota-file <filename>
                        file to retrieve/write Tasmota configuration from/to
                        (default: None)'
  -d, --device, --host <host>
                        hostname or IP address to retrieve/send Tasmota
                        configuration from/to (default: None)
  -P, --port <port>     TCP/IP port number to use for the host connection
                        (default: 80)
  -u, --username <username>
                        host HTTP access username (default: admin)
  -p, --password <password>
                        host HTTP access password (default: None)

Backup/Restore:
  Backup & restore specification

  -i, --restore-file <filename>
                        file to restore configuration from (default: None).
                        Replacements: @v=firmware version from config,
                        @f=device friendly name from config, @h=device
                        hostname from config, @H=device hostname from device
                        (-d arg only)
  -o, --backup-file <filename>
                        file to backup configuration to (default: None).
                        Replacements: @v=firmware version from config,
                        @f=device friendly name from config, @h=device
                        hostname from config, @H=device hostname from device
                        (-d arg only)
  -t, --backup-type json|bin|dmp
                        backup filetype (default: 'json')
  -E, --extension       append filetype extension for -i and -o filename
                        (default)
  -e, --no-extension    do not append filetype extension, use -i and -o
                        filename as passed
  -F, --force-restore   force restore even configuration is identical

JSON output:
  JSON format specification

  --json-indent <indent>
                        pretty-printed JSON output using indent level
                        (default: 'None'). -1 disables indent.
  --json-compact        compact JSON output by eliminate whitespace
  --json-hide-pw        hide passwords
  --json-show-pw, --json-unhide-pw
                        unhide passwords (default)

Tasmota command output:
  Tasmota command output format specification

  --cmnd-indent <indent>
                        Tasmota command grouping indent level (default: '2').
                        0 disables indent
  --cmnd-groups         group Tasmota commands (default)
  --cmnd-nogroups       leave Tasmota commands ungrouped
  --cmnd-sort           sort Tasmota commands (default)
  --cmnd-unsort         leave Tasmota commands unsorted

Common:
  Optional arguments

  -c, --config <filename>
                        program config file - can be used to set default
                        command args (default: None)
  -S, --output          display output regardsless of backup/restore usage
                        (default do not output on backup or restore usage)
  -T, --output-format json|cmnd|command
                        display output format (default: 'json')
  -g, --group {Control,Display,Domoticz,Internal,Knx,Light,Management,Mqtt,Power,Rf,Rules,Sensor,Serial,Setoption,Shutter,System,Timer,Wifi}
                        limit data processing to command groups (default no
                        filter)
  --ignore-warnings     do not exit on warnings. Not recommended, used by your
                        own responsibility!
  --dry-run             test program without changing configuration data on
                        device or file

Info:
  Extra information

  -h, --help            show usage help message and exit
  -H, --full-help       show full help message and exit
  -v, --verbose         produce more output about what the program does
  -V, --version         show program's version number and exit

Either argument -d <host> or -f <filename> must be given.
```

#### Parameter notes

* Filename replacement macros **@h** and **@H**:
  * **@h**
The **@h** replacement macro uses the hostname configured with the Tasomta Wifi `Hostname <host>` command (defaults to `%s-%04d`). It will not use the network hostname of your device because this is not available when working with files only (e.g. `--file <filename>` as source).
To prevent having a useless % in your filename, **@h** will not replaced by configuration data hostname if this contains '%' characters.
  * **@H**
If you want to use the network hostname within your filename, use the **@H** replacement macro instead - but be aware this will only replaced if you are using a network device as source (`-d`, `--device`, `--host`); it will not work when using a file as source (`-f`, `--file`)

### Examples

#### Parameter config file

> Note: The example contains .ini style sections `[...]`. Sections are always treated as comment and serves as clarity only.
For further details of config file syntax see [https://pypi.org/project/ConfigArgParse](https://pypi.org/project/ConfigArgParse/).

##### my.conf

```conf
[Source]
username = admin
password = myPaszxwo!z

[JSON]
json-indent 2
```

#### Using Tasmota binary configuration files

1. Restore a Tasmota configuration file

  ```bash
  decode-config -c my.conf -d tasmota --restore-file Config_Tasmota_6.2.1.dmp
  ```

1. Backup device using Tasmota configuration compatible format

   a) use file extension to choice the file format

  ```bash
  decode-config -c my.conf -d tasmota --backup-file Config_@f_@v.dmp
  ```

   b) use args to choice the file format

  ```bash
    decode-config -c my.conf -d tasmota --backup-type dmp --backup-file Config_@f_@v
  ```

#### Use batch processing

```bash
for device in tasmota1 tasmota2 tasmota3; do ./decode-config -c my.conf -d $device -o Config_@f_@v
```

or under windows

```batch
for device in (tasmota1 tasmota2 tasmota3) do decode-config -c my.conf -d %device -o Config_@f_@v
```

will produce JSON configuration files for host tasmota1, tasmota2 and tasmota3 using friendly name and Tasmota firmware version for backup filenames.
