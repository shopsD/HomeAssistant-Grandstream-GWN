# HomeAssistant-Grandstream-GWN

## Overview

This project connects Grandstream GWN Manager with Home Assistant in two ways:

- `gwn`: the core library for authenticating with GWN Manager, reading data, and sending updates
- `custom_components`: a Home Assistant integration workspace
- `mqtt`: the GWN-to-MQTT bridge application, including Home Assistant MQTT auto-discovery support

At a high level, the bridge polls GWN Manager, publishes network/device/SSID data to MQTT, listens for MQTT commands, and sends supported changes back to GWN Manager.

## Repository Layout

- `gwn/`
  - Core library for talking to GWN Manager
  - Contains authentication, request helpers, constants, and request data models
- `mqtt/`
  - Runnable bridge application
  - Contains config parsing, MQTT transport, the GWN/MQTT manager, and the packaged default config
- `custom_components/grandstream_gwn/`
  - Home Assistant custom integration workspace
  - Separate from the MQTT bridge app
- `mqtt/data/config.yml`
  - Example configuration file used by the bridge

## Building And Running

There is currently no Docker support.

### Requirements

- Python 3.13+
- `pip`

### Setup

1. Install `uv`:

```bash
pip install uv
```

2. Install project dependencies:

```bash
uv sync
```

### Run

Run the bridge with:

```bash
uv run gwn_mqtt
```

To use a custom config file:

```bash
uv run gwn_mqtt --config_path "/path/to/config.yml"
```

If `--config_path` is omitted, the app uses its bundled `./data/config.yml` default inside the `mqtt` package.

## Configuration

The bridge reads YAML with three top-level sections:

- `mqtt`
- `gwn`
- `logging`

Below is the full supported config surface based on the current code and the sample file in `mqtt/data/config.yml`.

### `mqtt`

- `host`: MQTT broker hostname or IP.
  - Default: `127.0.0.1`
- `port`: MQTT broker port.
  - Default: `1883`
- `username`: Optional MQTT username.
  - Default: `null`
- `password`: Optional MQTT password.
  - Default: `null`
- `client_id`: Optional MQTT client ID.
  - Default: `null`
- `keepalive`: MQTT keepalive interval in seconds.
  - Default: `60`
- `topic`: Root topic used by the bridge.
  - Default: `gwn`
- `tls`: Enable TLS for the MQTT connection.
  - Default: `false`
- `verify_tls`: Verify MQTT TLS certificates.
  - Default: `true`
- `no_publish`: Connect and listen, but do not publish to MQTT.
  - Default: `false`

#### `mqtt.homeassistant`

Controls MQTT Home Assistant auto-discovery output.

- `application_autodiscovery`: Publish discovery for the bridge application device.
  - Default: `false`
- `default_network_autodiscovery`: Default discovery behavior for networks not explicitly listed below.
  - Default: `false`
- `default_device_autodiscovery`: Default discovery behavior for devices not explicitly listed below.
  - Default: `false`
- `default_ssid_autodiscovery`: Default discovery behavior for SSIDs not explicitly listed below.
  - Default: `false`

##### Per-object auto-discovery lists

These fields accept a YAML list. Each item must be either:

- a single raw ID/MAC, which uses the matching default mode
- a single key/value pair, where the value is `true` or `false`

Supported fields:

- `network_autodiscovery`
  - Keys are network IDs
- `device_autodiscovery`
  - Keys are MAC addresses
- `ssid_autodiscovery`
  - Keys are SSID IDs

Examples:

```yaml
network_autodiscovery:
  - 1
  - 2: true

device_autodiscovery:
  - "AA:BB:CC:DD:EE:FF": false
  - "AA:BB:CC:DD:EE:F0": true

ssid_autodiscovery:
  - 3: false
  - 4
```

##### Name override lists

These fields accept a YAML list of single key/value pairs:

- `network_name_override`
  - Keys are network IDs
- `device_name_override`
  - Keys are MAC addresses
- `ssid_name_override`
  - Keys are SSID IDs

These overrides only change the names shown in Home Assistant discovery output.
They do not rename the underlying GWN network, device, or SSID.

Examples:

```yaml
network_name_override:
  - 1: "Office"

device_name_override:
  - "AA:BB:CC:DD:EE:FF": "Lobby AP"

ssid_name_override:
  - 2: "Guest Wi-Fi"
```

### `gwn`

This section is required.

- `app_id`: GWN application ID.
  - Required
- `secret_key`: GWN secret key.
  - Required
- `url`: Base URL for GWN Manager.
  - Default: `https://localhost:8443`
- `username`: Optional GWN Manager username.
  - Default: `null`
- `password`: Optional GWN Manager password.
  - Default: `null`
  - If provided, the app hashes it before login using the browser-compatible client-side scheme currently implemented by the project
- `page_size`: Page size for paginated GWN API requests.
  - Default: `10`
  - Must be `>= 1`
- `max_pages`: Maximum number of pages to request.
  - Default: `0`
  - `0` means unlimited
  - Must be `>= 0`
- `refresh_period_s`: Polling interval in seconds.
  - Default: `30`
  - Must be `>= 0`
- `exclude_passphrase`: List of SSID IDs whose passphrase should not be published.
  - Default: empty list
- `exclude_ssid`: List of SSID IDs to exclude entirely.
  - Default: empty list
- `exclude_device`: List of device MAC addresses to exclude entirely.
  - Default: empty list
- `exclude_network`: List of network IDs to exclude entirely.
  - Default: empty list
- `no_publish`: Read from GWN Manager but do not send write commands back.
  - Default: `false`

#### Username/password note

- `username` and `password` are both optional
- if one is provided, the other must also be provided
- when present, they enable the project’s additional username/password login flow used for more authoritative SSID-to-device correlation
- when absent, the project falls back to its non-username/password behavior

#### Exclusion note

- `exclude_passphrase` only stops passphrase publication
- SSID updates still require a passphrase when the underlying GWN endpoint requires one

### `logging`

- `level`: Logging level.
  - Supported: `FATAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`, `NONE`
  - Default: `INFO`
- `location`: Log output location.
  - Supported: `syslog`, `file`, `console`
  - Default: `console`
- `output_path`: Required when `location: file`.
  - Default: `null`
- `size`: Rotation threshold.
  - Default: `0`
  - `0` means no rotation
- `files`: Number of rotated files to keep.
  - Default: `1`

## Supported Home Assistant Entities

The MQTT bridge can publish Home Assistant MQTT discovery entities for the bridge application, networks, devices, and SSIDs.

The tables below reflect the entities currently emitted by the bridge code.

### Application

| Scope | Entity Type | Name | Read/Write | Notes |
| --- | --- | --- | --- | --- |
| Application | `update` | Update Application | Read/Write | Install action publishes an application update command |
| Application | `sensor` | Available Version | Read-only | Latest application version exposed by the bridge |
| Application | `sensor` | Current Version | Read-only | Running bridge version |
| Application | `button` | Restart | Write | Sends a restart command to the bridge |

### Network

| Scope | Entity Type | Name | Read/Write | Backing Value |
| --- | --- | --- | --- | --- |
| Network | `text` | Name | Read/Write | `networkName` |
| Network | `sensor` | Country | Read-only | `countryDisplay` |
| Network | `sensor` | Timezone | Read-only | `timezone` |

### Device

| Scope | Entity Type | Name | Read/Write | Backing Value |
| --- | --- | --- | --- | --- |
| Device | `button` | Reboot | Write | Reboot command |
| Device | `update` | Update Firmware | Read/Write | Firmware install action |
| Device | `button` | Reset | Write | Reset command |
| Device | `sensor` | Network | Read-only | Home Assistant display name for the parent network |
| Device | `binary_sensor` | Status | Read-only | `status` |
| Device | `switch` | Wireless | Read/Write | `wireless` |
| Device | `sensor` | IPv4 | Read-only | `ip` |
| Device | `sensor` | IPv6 | Read-only | `ipv6` |
| Device | `sensor` | Current Firmware | Read-only | `versionFirmware` |
| Device | `sensor` | Available Firmware | Read-only | `newFirmware` |
| Device | `sensor` | CPU Usage | Read-only | `cpuUsage` |
| Device | `sensor` | Temperature | Read-only | `temperature` |
| Device | `sensor` | SSIDs | Read-only | Derived from assigned SSID list |
| Device | `sensor` | Up Time | Read-only | `upTime` |
| Device | `number` | 2.4Ghz Channel | Read/Write | `channel_2_4` |
| Device | `number` | 5Ghz Channel | Read/Write | `channel_5` |
| Device | `number` | 6Ghz Channel | Read/Write | `channel_6` |
| Device | `sensor` | MAC | Read-only | `mac` |

### SSID

| Scope | Entity Type | Name | Read/Write | Backing Value |
| --- | --- | --- | --- | --- |
| SSID | `switch` | Assign `<device>` | Read/Write | Device membership for the SSID |
| SSID | `switch` | Enabled | Read/Write | `ssidEnable` |
| SSID | `switch` | Captive Portal | Read/Write | `portalEnabled` |
| SSID | `number` | VLAN ID | Read/Write | `ssidVlanid` |
| SSID | `switch` | Client Isolation | Read/Write | `clientIsolationEnabled` |
| SSID | `switch` | 2.4GHz Station | Read/Write | `ghz2_4_Enabled` |
| SSID | `switch` | 5GHz Station | Read/Write | `ghz5_Enabled` |
| SSID | `switch` | 6GHz Station | Read/Write | `ghz6_Enabled` |
| SSID | `text` | WiFi Passphrase | Read/Write | `ssidKey` |
| SSID | `switch` | Hide WiFi | Read/Write | `ssidSsidHidden` |
| SSID | `sensor` | Clients Online | Read-only | `onlineDevices` |
| SSID | `sensor` | Network | Read-only | Home Assistant display name for the parent network |
| SSID | `text` | SSID | Read/Write | `ssidName` |

### Current Writable Values

The bridge currently exposes write paths for the following values over MQTT/Home Assistant:

| Scope | Writable Values |
| --- | --- |
| Application | Restart, update application |
| Network | Network name |
| Device | Reboot, reset, update firmware, wireless state, 2.4 GHz channel, 5 GHz channel, 6 GHz channel |
| SSID | Device assignment, enabled state, captive portal, VLAN ID, client isolation, 2.4 GHz enable, 5 GHz enable, 6 GHz enable, passphrase, hidden state, SSID name |

## Example

Start from the sample file at:

```text
mqtt/data/config.yml
```

Then run:

```bash
uv run gwn_mqtt --config_path "/path/to/your/config.yml"
```
