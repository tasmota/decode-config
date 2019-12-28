# decode-config

_decode-config_ backup and restore configuration data of [Tasmota](http://tasmota.com/)-devices.

In comparison with the Tasmota build-in "Backup/Restore Configuration" function

* _decode-config_ uses human readable and editable [JSON](http://www.json.org/)-format for backup/restore
* _decode-config_ can restore previously backup and changed [JSON](http://www.json.org/)-format files
* _decode-config_ is able to create Tasmota compatible command list for the most available commands
* _decode-config_ can handle subsets of configuration data
* _decode-config_ can convert data from all older versions starting v5.10.0 into newer one and reverse.

Comparing backup files created by *decode-config.py* and *.dmp files created by Tasmota "Backup/Restore Configuration":

| &nbsp;                  | decode-config.py *.json file      | Tasmota *.dmp file             |
|:------------------------|:---------------------------------:|:-----------------------------------:|
| Encrypted               |                No                 |                 Yes                 |
| Readable                |               Yes                 |                  No                 |
| Editable                |               Yes                 |                  No                 |
| Batch processing        |               Yes                 |                  No                 |
| Backup/Restore subsets  |               Yes                 |                  No                 |

_decode-config_ is compatible with Tasmota starting from v5.10.0 up to now.

## Content

**This is the master branch which contains _decode-config_ matching official Tasmota release.**

> If you are using Tasmota from development branch the _decode-config_ version from this master branch can be outdated.
You can then use the [developer branch](https://github.com/tasmota/decode-config/tree/development) which contains
an up-to-date version matching the latest Tasmota developer version.

### Files

| File                     | Description |
|:-------------------------|:------------------------------------------------------------------------|
| `build`                  | contains files to build executables                                     |
| `decode-config.py`       | Python source file running under your local Python environment          |
| `decode-config_linux`    | Linux executable running standalone                                     |
| `decode-config_mac`      | macOS executable running standalone                                     |
| `decode-config_win32.exe`| Windows 32bit executable running standalone                             |
| `decode-config_win64.exe`| Windows 64bit executable running standalone                             |
| `README.md`              | This content                                                            |

* [Running the program](#running-the-program)
  * [Prerequisite](#prerequisite)
  * [Running as Python script](#running-as-python-script)
    * [Linux](#linux)
    * [Windows 10](#windows-10)
    * [MacOS](#macos)
    * [All OS](#all-os)
* [File Formats](#file-formats)
  * [.dmp File Format](#dmp-format)
  * [.json File Format](#json-format)
  * [.bin File Format](#bin-format)
  * [File extensions](#file-extensions)
* [Usage](#usage)
  * [Test run](#test-run)
  * [Basics](#basics)
  * [Save backup file](#save-backup-file)
  * [Restore backup file](#restore-backup-file)
  * [Output to screen](#output-to-screen)
    * [JSON output](#json-output)
    * [Tasmota command output](#tasmota-command-output)
  * [Filter data](#filter-data)
  * [Program parameter configuration file](#program-parameter-configuration-file)
  * [More program arguments](#more-program-arguments)
    * [Program parameter notes](#program-parameter-notes)
  * [Examples](#examples)
    * [Parameter config file](#parameter-config-file)
    * [Using Tasmota binary configuration files](#using-tasmota-binary-configuration-files)
    * [Use batch processing](#use-batch-processing)

## Running the program

The program does not have any graphical user interface (GUI), it is needed to run it on command line using [program arguments](#more-program-arguments).

For Windows, MacOS and Linux you can simply use the program on your OS command line [executable related to your OS](#files).

### Prerequisite

Tasmota provides its configuration data by http request only. To receive and send configuration data from Tasmota devices directly the http WebServer in Tasmota must be enabled:

* when using your own compiled firmware you have to compile your firmware with web-server (`#define USE_WEBSERVER` and `#define WEB_SERVER 2`).
* enable web-server in admin mode (command [WebServer 2](https://tasmota.github.io/docs/#/Commands?id=wi-fi))

> Note: Using MQTT for exchanging Tasmota configuration data is not support by Tasmota itself; so _decode-config_ is unable using this way.

### Running as Python script

If you want to run the Python source _decode-config.py_, an installed [Python](https://en.wikipedia.org/wiki/Python_(programming_language)) environment is neccessary.

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

_decode-config_ handles the following backup/restore file formats:

### .dmp Format

This format is binary encrypted and is the same as used by Tasmota "Backup/Restore Configuration" web interface.

### .json Format

This format is decrypted, human readable, editable and contains the configuration data in [JSON](http://www.json.org/)-format.
This file format will be created by _decode-config_ using the `--backup-file` with `--backup-type json` parameter (that's the default) and can also be used for the `--restore-file` parameter.

> Note: The keys used within the JSON file are based on the variable names of Tasmota source code in [settings.h](https://github.com/arendst/Tasmota/blob/master/tasmota/settings.h) so they do not have the same naming as known for Tasmota web commands.

### .bin Format

This format is binary decrypted and is nearly the same as used by Tasmota "Backup/Restore Configuration" web interface. The difference between ths format and the original Tasmota dmp format is an additonal header of 4 bytes at the beginning of this file; also the decrypted status lets you observe (and change) the original binary data using a hex editor.

This file format will be created by _decode-config_ using the `--backup-file` with `--backup-type bin` parameter and can also be used for the `--restore-file` parameter.

### File extensions

File extensions will be choose based on file contents and/or `--backup-type` parameter. You don't need to append exensions for your file.
If you want to use your own extensions, disable auto extension by using the `--no-extension` parameter.

## Usage

For an overview start the program without any parameter and you will get a small help screen.  
For full help start the program with parameter `-H`: `decode-config -H`

> Note: Replace the program name `decode-config` within examples with your one, e.g. `decode-config_win64` for Windows or `decode-config_mac`under MacOS.

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

This will create a file like `Config_Tasmota_8.1.0.json` (the part `Tasmota` and `8.1.0` will choosen related to your device configuration).

### Restore backup file

Reading back a previously saved backup file use the `--restore-file <filename>` parameter. This will read the (possibly changed) configuration data from this file and send it back to the source device or filename.

To restore the previously save backup file `Config_Tasmota_6.2.1.json` to device `tasmota-4281` use:

```bash
decode-config -d tasmota-4281 --restore-file Config_Tasmota_6.2.1.json
```

with password set by WebPassword:

```bash
decode-config -d tasmota-4281 -p <yourpassword> --restore-file Config_Tasmota_6.2.1.json
```

> Note: For JSON file formats you can also use files containing a subset of configuration data. For example: You want to change othe three configuration data for location (altitude, latitude, longitude) only use a JSON file with the content

```json
{
  "altitude": 0,
  "latitude": 48.85836,
  "longitude": 2.294442
}
```

Be aware to keep a valid JSON-format. For example: When cutting unnecessary content from a given JSON backup file, consider to remove the last comma:

Invalid JSON format:

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

Output to screen is the default when calling the program backup or restore parameter. The output is prevented when using backup or restore parameter. In that case you can force screen output using the `--output` parameter.

#### JSON output

The default backup format is [JSON](#json-format). You can force JSON backup using the `--output-format json` parameter.

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

_decode-config_ is able to translate the configuration data to (most all) Tasmota commands. To output your configuration as Tasmota commands use `--output-format cmnd` or `--output-format command`.

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

With _decode-config_ the following categories are available:   `Display`, `Domoticz`, `Internal`, `KNX`, `Led`, `Logging`, `MCP230xx`, `MQTT`, `Main`, `Management`, `Pow`, `Sensor`, `Serial`, `SetOption`, `RF`, `System`, `Timers`, `Wifi`

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

### More program arguments

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
                        [-g {Control,Devices,Display,Domoticz,Internal,Knx,Light,Management,Mqtt,Power,Rf,Rules,Sensor,Serial,Setoption,Shutter,System,Timer,Wifi} [{Control,Devices,Display,Domoticz,Internal,Knx,Light,Management,Mqtt,Power,Rf,Rules,Sensor,Serial,Setoption,Shutter,System,Timer,Wifi} ...]]
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
  -g, --group {Control,Devices,Display,Domoticz,Internal,Knx,Light,Management,Mqtt,Power,Rf,Rules,Sensor,Serial,Setoption,Shutter,System,Timer,Wifi}
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

#### Program parameter notes

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
  `decode-config -c my.conf -d tasmota --restore-file Config_Tasmota_6.2.1.dmp`
  ```
  
1. Backup device using Tasmota configuration compatible format
  
   a) use file extension to choice the file format
  
  ```bash
  `decode-config -c my.conf -d tasmota --backup-file Config_@f_@v.dmp`
  ```

   b) use args to choice the file format

  ```bash
  `decode-config -c my.conf -d tasmota --backup-type dmp --backup-file Config_@f_@v`
  ```

#### Use batch processing

```bash
for device in tasmota1 tasmota2 tasmota3; do ./decode-config -c my.conf -d $device -o Config_@f_@v
```

or under windows

```bat
    for device in (tasmota1 tasmota2 tasmota3) do decode-config -c my.conf -d %device -o Config_@f_@v
```

will produce JSON configuration files for host tasmota1, tasmota2 and tasmota3 using friendly name and Tasmota firmware version for backup filenames.
