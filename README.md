# decode-config
_decode-config_ backup and restore configuration data of [Tasmota](http://tasmota.com/)-devices.

**Note**: This current development branch can not write string settings back to v8.x.x.x Tasmota developer settings, read only!

In comparison with the Tasmota build-in "Backup/Restore Configuration" function
* _decode-config_ uses human readable and editable [JSON](http://www.json.org/)-format for backup/restore,
* _decode-config_ can restore previously backup and changed [JSON](http://www.json.org/)-format files,
* _decode-config_ is able to create Tasmota compatible command list for the most available commands

Comparing backup files created by *decode-config.py* and *.dmp files created by Tasmota "Backup/Restore Configuration":

| &nbsp;                  | decode-config.py *.json file      | Tasmota *.dmp file             |
|:------------------------|:---------------------------------:|:-----------------------------------:|
| Encrypted               |                No                 |                 Yes                 |
| Readable                |               Yes                 |                  No                 |
| Editable                |               Yes                 |                  No                 |
| Batch processing        |               Yes                 |                  No                 |

_decode-config_ is able to process configuration data for Tasmota starting v5.10.0 up to current version.

## Content

**This is the developer branch which contains _decode-config_ matching the latest Tasmota developer version.**

It could be you want to use a stable version matching the latest officical Tasmota release only;  
then use the offical latest [_decode-config_ Release](https://github.com/tasmota/decode-config/releases) or the 
[_decode-config_ master branch](https://github.com/tasmota/decode-config/tree/master) which contains
a version matching the latest offical Tasmota release.

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

* [Prerequisite](#prerequisite)
* [File Types](#file-types)
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
  * [Configuration file](#configuration-file)
  * [More program arguments](#more-program-arguments)
    * [Program parameter notes](#program-parameter-notes)
  * [Examples](#examples)
    * [Config file](#config-file)
    * [Using Tasmota binary configuration files](#using-tasmota-binary-configuration-files)
    * [Use batch processing](#use-batch-processing)

# Running the program
The program does not have any graphical user interface (GUI), it is needed to run it on command line using [program arguments](#more-program-arguments).

For Windows, MacOS and Linux there is no prerequisite, simply use the command line [executable related to your OS](#files).

## Running as Python script
If you want to run the Python source _decode-config.py_, an installed [Python](https://en.wikipedia.org/wiki/Python_(programming_language)) environment is neccessary.

**Note**: Due to the [Python 2.7 EOL](https://github.com/python/devguide/pull/344) in Jan 2020 Python 2.x is no longer supported.

### Prerequisite
#### Linux
Install [Python 3.x](https://www.python.org/downloads/), Pip and follow [library installation for all OS](#all-os) below.
```
sudo apt-get install python3 python3-pip 
```

#### Windows 10
Install [Python 3.x](https://www.python.org/downloads/windows/) as described and follow [library installation for all OS](#all-os) below.

#### MacOS
Install [Python 3.x](https://www.python.org/downloads/mac-osx/) as described and follow [library installation for all OS](#all-os) below.

#### All OS
After python and pip is installed, install dependencies:
```
pip3 install requests configargparse
```

## Tasmota Webserver
Because _decode-config_ uses the Tasmota http capability to receive and send configuration data, the Tasmota http WebServer must be available and enabled:

  * To backup or restore configurations from or to a Tasmota device you need a firmare with enabled web-server in admin mode (command [WebServer 2](https://tasmota.github.io/docs/#/Commands?id=wi-fi)). This is the Tasmota default.
  * If using your own compiled firmware be aware to enable the web-server (`#define USE_WEBSERVER` and `#define WEB_SERVER 2`).

**Note**: MQTT is currently not possible as long as Tasmota does not support configuration data transmission this way.

## File Types
_decode-config_ can handle the following backup file types:
### .dmp Format
Configuration data as used by Tasmota "Backup/Restore Configuration" web interface.
This format is binary and encrypted.
### .json Format
Configuration data in [JSON](http://www.json.org/)-format.
This format is decrypted, human readable and editable and can also be used for the `--restore-file` parameter.
This file will be created by _decode-config_ using the `--backup-file` with `--backup-type json` parameter, this is the default.
### .bin Format
Configuration data in binary format.
This format is binary decryptet, editable (e.g. using a hex editor) and can also be used for `--restore-file` command.
It will be created by _decode-config_ using `--backup-file` with `--backup-type bin`.
Note:
The .bin file contains the same information as the original .dmp file from Tasmota "Backup/Restore Configuration" but it is decrpted and  4 byte longer than an original (it is a prefix header at the beginning). .bin file data starting at address 4 contains the same as the **struct SYSCFG** from Tasmota [settings.h](https://github.com/arendst/Tasmota/blob/master/tasmota/settings.h) in decrypted format.

#### File extensions
You don't need to append exensions for your file name as _decode-config_ uses auto extension as default. The extension will be choose based on file contents and `--backup-type` parameter.
If you do not want using auto extensions use the `--no-extension` parameter.

## Usage
For an overview start the program without any parameter and you will get a small help screen.  
For full help start the program with parameter `-H`: `decode-config -H`

### Test run
To test your parameter you can prevent writing any changes of configuation to your device or file by appending `--dry-run` on program command line:
`decode-config.py -d tasmota-4281 -i backupfile --dry-run`

### Basics
At least pass a source where you want to read the configuration data from using `-f <filename>` or `-d <host>`:

The source can be either
* a Tasmota device hostname or IP using the `-d <host>` parameter
* a Tasmota `*.dmp` configuration file using `-f <filename>` parameter

Example:

    decode-config.py -d tasmota-4281

will output a human readable configuration in [JSON](http://www.json.org/)-format:

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


### Save backup file
To save the output as backup file use `--backup-file <filename>`, you can use placeholder for Version, Friendlyname and Hostname:

    decode-config.py -d tasmota-4281 --backup-file Config_@f_@v

If you have setup a WebPassword within Tasmota, use

    decode-config.py -d tasmota-4281 -p <yourpassword> --backup-file Config_@f_@v

will create a file like `Config_Tasmota_6.4.0.json` (the part `Tasmota` and `6.4.0` will choosen related to your device configuration). Because the default backup file format is JSON, you can read and change it with any raw text editor.

### Restore backup file
Reading back a saved (and possible changed) backup file use the `--restore-file <filename>` parameter. This will read the (changed) configuration data from this file and send it back to the source device or filename.

To restore the previously save backup file `Config_Tasmota_6.2.1.json` to device `tasmota-4281` use:

    decode-config.py -d tasmota-4281 --restore-file Config_Tasmota_6.2.1.json

with password set by WebPassword:

    decode-config.py -d tasmota-4281 -p <yourpassword> --restore-file Config_Tasmota_6.2.1.json

### Output to screen
To force screen output use the `--output` parameter.

Output to screen is default enabled when calling the program with a source parameter (-f or -d) but without any backup or restore parameter.

#### JSON output
The default output format is [JSON](#json-format). You can force JSON output using the `--output-format json` parameter.

Example:

    decode-config.py -d tasmota-4281 -c my.conf -x Wifi --output-format json

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

Note: JSON output always contains all configuration data like the backup file except you are using `--group` arg.


#### Tasmota command output
_decode-config_ is able to translate the configuration data to (most all) Tasmota commands. To output your configuration as Tasmota commands use `--output-format cmnd` or `--output-format command`.

Example:

    decode-config.py -d tasmota-4281 -c my.conf -g Wifi --output-format cmnd

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

Note: A few very specific module commands like MPC230xx, KNX and some Display commands are not supported. These are still available by JSON output.

### Filter data
The huge number of Tasmota configuration data can be overstrained and confusing, so the most of the configuration data are grouped into categories.

With _decode-config_ the following categories are available:   `Display`, `Domoticz`, `Internal`, `KNX`, `Led`, `Logging`, `MCP230xx`, `MQTT`, `Main`, `Management`, `Pow`, `Sensor`, `Serial`, `SetOption`, `RF`, `System`, `Timers`, `Wifi`

These are similary to the categories on [Tasmota Command Wiki](https://tasmota.github.io/docs/#/Commands?id=command-list).

To filter outputs to a subset of groups use the `-g` or `--group` arg concatenating the grooup you want, e. g.

    decode-config.py -d tasmota-4281 -c my.conf --output-format cmnd --group Main MQTT Management Wifi


### Configuration file
Each argument that start with `--` (eg. `--file`) can also be set in a config file (specified via -c). Config file syntax allows: key=value, flag=true, stuff=[a,b,c] (for details, see syntax at [https://pypi.org/project/ConfigArgParse](https://pypi.org/project/ConfigArgParse/)).

If an argument is specified in more than one place, then commandline values override config file values which override defaults. This is usefull if you always use the same argument or a basic set of arguments.

The http authentication credentials `--username` and `--password` is predestinated to store it in a file instead using it on your command line as argument:

e.g. my.conf:

    [source]
    username = admin
    password = myPaszxwo!z

To make a backup file from example above you can now pass the config file instead using the password on command line:

    decode-config.py -d tasmota-4281 -c my.conf --backup-file Config_@f_@v



### More program arguments
For better reading each short written arg (minus sign `-`) has a corresponding long version (two minus signs `--`), eg. `--device` for `-d` or `--file` for `-f` (note: not even all `--` arg has a corresponding `-` one).

A short list of possible program args is displayed using `-h` or `--help`.

For advanced help use `-H` or `--full-help`:

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


#### Program parameter notes

* Filename replacement macros **@h** and **@H**:
  * **@h**
The **@h** replacement macro uses the hostname configured with the Tasomta Wifi `Hostname <host>` command (defaults to `%s-%04d`). It will not use the network hostname of your device because this is not available when working with files only (e.g. `--file <filename>` as source).
To prevent having a useless % in your filename, **@h** will not replaced by configuration data hostname if this contains '%' characters.
  * **@H**
If you want to use the network hostname within your filename, use the **@H** replacement macro instead - but be aware this will only replaced if you are using a network device as source (`-d`, `--device`, `--host`); it will not work when using a file as source (`-f`, `--file`)


### Examples
The most of the examples are for linux command line. Under Windows call the program using `python decode-config.py ...`.

#### Config file
Note: The example contains .ini style sections `[...]`. Sections are always treated as comment and serves as clarity only.
For further details of config file syntax see [https://pypi.org/project/ConfigArgParse](https://pypi.org/project/ConfigArgParse/).

*my.conf*

    [Source]
    username = admin
    password = myPaszxwo!z

    [JSON]
    json-indent 2

#### Using Tasmota binary configuration files

1. Restore a Tasmota configuration file

    `decode-config.py -c my.conf -d tasmota --restore-file Config_Tasmota_6.2.1.dmp`

2. Backup device using Tasmota configuration compatible format

   a) use file extension to choice the file format

    `decode-config.py -c my.conf -d tasmota --backup-file Config_@f_@v.dmp`

   b) use args to choice the file format

    `decode-config.py -c my.conf -d tasmota --backup-type dmp --backup-file Config_@f_@v`

#### Use batch processing

    for device in tasmota1 tasmota2 tasmota3; do ./decode-config.py -c my.conf -d $device -o Config_@f_@v

or under windows

    for device in (tasmota1 tasmota2 tasmota3) do python decode-config.py -c my.conf -d %device -o Config_@f_@v

will produce JSON configuration files for host tasmota1, tasmota2 and tasmota3 using friendly name and Tasmota firmware version for backup filenames.
