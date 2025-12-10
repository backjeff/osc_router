## OSC Router

**Version 1.1.0**

A simple, standalone OSC router tool with GUI, ETL-style mapping, live debug logging, and external JSON configuration.
Useful for router and transforming OSC messages between applications such as **Reaper**, **Resolume**, lighting consoles, controllers, or any OSC-enabled device.

## Features

### ✔ Fixed Listen IP

* Automatically detects the host computer's primary IP.
* Displayed in the GUI (read-only).
* Only the **port** is user-configurable.

### ✔ Transform & Forward OSC Messages

* Incoming OSC messages are matched against mappings in `config.json`.
* If matched → transformed and forwarded.
* If not matched and `forward_unmapped = true` → forwarded unchanged.
* If not matched and `forward_unmapped = false` → ignored.

### ✔ External JSON Configuration

Mappings live entirely in `config.json`, not inside the EXE.
You can modify mappings at any time without rebuilding the application.

### ✔ Scrollable Debug Log

Shows:

* Incoming OSC messages
* Outgoing transformed messages
* Ignored events
* Server start/stop logs
* Config load status

### ✔ Single-Executable Deployment

Buildable with PyInstaller (`--onefile`).
Icon support included (`favicon.ico` via resource_path).

## Files

```
osc_router.py       → main application
config.json             → user-editable routing configuration
favicon.ico             → optional app icon
```

## Configuration

The application loads mappings from a `config.json` file located in the same directory as the script or the built EXE.

### Example `config.json`

```json
{
  "forward_unmapped": true,
  "mappings": [
    {
      "in_address": "/source",
      "in_value": 1,
      "out_address": "/layer1/clip1/connect",
      "out_args": [1]
    },
    {
      "in_address": "/source",
      "in_value": 2,
      "out_address": "/layer1/clip2/connect",
      "out_args": [1]
    }
  ]
}
```

### How Mappings Work

Each mapping has:

| Key           | Description                                 |
| ------------- | ------------------------------------------- |
| `in_address`  | Incoming OSC address to match               |
| `in_value`    | The first argument to match (can be `null`) |
| `out_address` | New OSC address to send                     |
| `out_args`    | List of arguments to send                   |

Mappings are stored internally as:

```
(in_address, in_value) → (out_address, out_args)
```

## GUI Overview

### Inputs

* **Listen Port**: Port where OSC messages will be received.
* **Target IP**: Destination host for forwarded OSC messages.
* **Target Port**: Destination OSC port.

### Fixed Values

* **Listen IP**: Auto-detected host IP — cannot be changed.

### Buttons

* **Start**: Starts the OSC routing server.
* **Stop**: Stops the OSC routing server.

### Log Window

Shows a real-time stream of:

* Incoming OSC
* Outgoing OSC
* Errors and warnings
* Config loading details

## Build Instructions (PyInstaller)

Make sure you have a virtual environment created and activated.

### Install requirements

```
pip install python-osc pyinstaller
```

### Build the executable

```
pyinstaller --onefile --noconsole --icon=favicon.ico --add-data "favicon.ico;." osc_router.py
```

This will generate:

```
dist/osc_router.exe
```

Place `config.json` next to the EXE.

## Running

Simply start the EXE.
Edit `config.json` before launching if you need custom mappings.

## Known Limitations

* The GUI does not dynamically reload the config file; restart the app after changes.
* Incoming OSC matching uses only:

  * The OSC address
  * The **first argument**

If more advanced matching is needed (types, multiple args, regex matching), the system can be extended.

## Roadmap

* Reload config button
* Save log to file
* Multi-argument match conditions
* Named “profiles” for switching mapping sets
* Built-in test sender for debugging OSC networks
