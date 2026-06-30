# Home Control Pi Agent

A Raspberry Pi 4 agent that gets commands from a hosted web app for home control commands to execute them on my local network

Had this running on localhost for a while and decided it was time for an upgrade. Not a fan of having to turn it on on my computer, plus I'd like to be able to check if I left my projector on or my lights on after I leave the house.

## How It Works

1. The agent runs as a systemd service (`piAgent.service`) on the Pi.
2. It polls the hosted web app for pending commands using adaptive polling:
   - **Idle** (15s): No one has the web page open.
   - **Active** (2s): A browser session is detected (lasts 60s).
   - **Burst** (0.25s): A command was just received (lasts 10s for rapid button presses).
3. Commands are validated against a whitelist of allowed device/action combinations.
4. The receiver controller sends Yamaha XML commands over HTTP to the HTR-4065.
5. Results are reported back to the web app.
6. Receiver state (power, volume, mute, input) is pushed to the web app while a browser session is active.
7. If the hosted app is unreachable or disabled, the agent runs in heartbeat-only mode.

## Configuration

Real config lives outside the repo at `/etc/homeControl/settings.json`. The repo only contains an example at `config/settings.example.json`.

Not that I think anyone would, but I'd rather the domain not be public. Zero trust architecture and all that.

To edit settings on the Pi:

```bash
sudo nano /etc/homeControl/settings.json
sudo systemctl restart piAgent.service
```

## Fresh Install

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-venv
sudo git clone https://github.com/Grinetrove/home-control-pi.git /opt/homeControl
cd /opt/homeControl
sudo ./install.sh
```

See [docs/freshPiSetup.md](docs/freshPiSetup.md) for a full step-by-step checklist.

## Check Status

```bash
sudo ./scripts/status.sh
```

## View Logs

```bash
sudo ./scripts/logs.sh
```

## Update from GitHub

```bash
cd /opt/homeControl
sudo ./update.sh
```

## Restart

```bash
sudo ./scripts/restart.sh
```

## Project Structure

```
config/settings.example.json   Example config
src/piAgent.py                 Main service entry point
src/settingsLoader.py          Config loading and validation
src/flaskClient.py             HTTP client for the hosted Flask app
src/commandDispatcher.py       Command validation and routing
src/receiverController.py      Yamaha HTR-4065 XML command handlers
src/irController.py            IR signal send handlers (projector/soundbar)
systemd/piAgent.service        Systemd unit file
install.sh                     First-time install script
update.sh                      Pull and restart script
scripts/                       Helper scripts for status, logs, restart
scripts/sendIrSignal.sh        Send a stored IR signal file via ir-ctl
scripts/storeIrSignal.sh       Record a raw IR signal from a remote
scripts/checkIrDevices.sh      List /dev/lirc* devices and features
storedSignals/                 Stored raw IR signal files (.ir)
docs/                          Setup documentation
commands.txt                   Quick-reference commands (cat this)
```

## Supported Receiver Commands

Power, volume, mute, input selection (HDMI1-4, AirPlay), menu/cursor navigation, and AirPlay playback controls. See `commands.txt` for the full list.



## IR Control Overview

The Flask web page sends IR commands (`projectorOn`, `projectorOff`, `toggleSoundbar`) to the hosted app. The Pi agent polls for those commands and maps them to stored raw `.ir` signal files under `storedSignals/`. The agent calls `scripts/sendIrSignal.sh` with the matching file to transmit the IR signal via `ir-ctl`.

### Commands Added

| Command          | Signal File                       |
|------------------|-----------------------------------|
| `projectorOn`    | `storedSignals/projectorOn.ir`    |
| `projectorOff`   | `storedSignals/projectorOff.ir`   |
| `toggleSoundbar` | `storedSignals/toggleSoundbar.ir` |

### Required Packages

The Pi needs `v4l-utils` for the `ir-ctl` command. The `install.sh` script installs this automatically.

```bash
sudo apt install v4l-utils
```

### Receiver Wiring (Recording Only)

The IR receiver is only needed when recording remote signals. You can unplug it after recording.

Wiring for a VS1838B receiver module:

| VS1838B Pin | Connect To            |
|-------------|-----------------------|
| VCC         | Pi 3.3V               |
| GND         | Pi GND                |
| OUT         | Pi GPIO17 (pin 11)    |

**Warning:** Verify your receiver's pinout before wiring. Bare IR receiver modules can have different pin arrangements.

### Transmitter Wiring (Sending Only)

The IR transmitter LED is only needed when sending signals. The transistor lets the Pi control the LED without powering it directly from a GPIO pin.

| Connection                                           |
|------------------------------------------------------|
| Pi GPIO18 (pin 12) -> 1k resistor -> NPN base        |
| NPN emitter -> Pi GND                                |
| Pi 5V -> 68-100 ohm resistor -> IR LED anode (long)  |
| IR LED cathode (short/flat) -> NPN collector          |

**Warning:** Verify your transistor's pinout (BCE order varies by part) before wiring.

### config.txt - Receiver Mode

For recording remote signals, add the receiver overlay:

```
dtoverlay=gpio-ir,gpio_pin=17,gpio_pull=up
```

The file is usually at `/boot/firmware/config.txt`. On some older installs it may be `/boot/config.txt`. A reboot is required after editing.

### config.txt - Transmitter Mode

For sending IR signals, add the transmitter overlay:

```
dtoverlay=gpio-ir-tx,gpio_pin=18
```

Alternate option (may work better on some setups):

```
dtoverlay=pwm-ir-tx,gpio_pin=18
```

`gpio-ir-tx` is the simpler default. `pwm-ir-tx` may be preferred later if it works more cleanly on your setup. A reboot is required after editing.

### config.txt - Receiver and Transmitter Together

To use both at once:

```
dtoverlay=gpio-ir,gpio_pin=17,gpio_pull=up
dtoverlay=gpio-ir-tx,gpio_pin=18
```

If using PWM transmit instead, replace `gpio-ir-tx` with:

```
dtoverlay=pwm-ir-tx,gpio_pin=18
```

### Checking Devices

```bash
./scripts/checkIrDevices.sh
```

Look for a receive-capable device (for recording) and/or a transmit-capable device (for sending).

### Recording a Signal

```bash
./scripts/storeIrSignal.sh storedSignals/projectorOn.ir
./scripts/storeIrSignal.sh storedSignals/projectorOff.ir
./scripts/storeIrSignal.sh storedSignals/toggleSoundbar.ir
```

Point the remote at the IR receiver, press the button once, then press Ctrl+C after capture.

### Sending a Signal Manually

```bash
./scripts/sendIrSignal.sh storedSignals/projectorOn.ir
./scripts/sendIrSignal.sh storedSignals/projectorOff.ir
./scripts/sendIrSignal.sh storedSignals/toggleSoundbar.ir
```

### Running Through the Flask App

The Flask web page has three buttons that send these commands:
- **Projector On** -> `projectorOn`
- **Projector Off** -> `projectorOff`
- **Toggle Soundbar** -> `toggleSoundbar`

The Pi agent receives those commands and calls `scripts/sendIrSignal.sh` with the matching `.ir` file.

### Install vs Update Notes

- Run `install.sh` on a fresh Pi setup. It installs `v4l-utils`, creates the virtual environment, sets up the systemd service, and creates blank placeholder `.ir` files.
- Run `update.sh` after pulling new code on an already-configured Pi. It preserves existing settings and recorded `.ir` files.
- Editing `config.txt` and rebooting is a manual Pi setup step. Neither `install.sh` nor `update.sh` will modify `config.txt`.
- Existing non-empty `.ir` files are never overwritten during install or update.
- Blank placeholder `.ir` files must be replaced by recording real signals before the Flask buttons can work.

### Troubleshooting

- **No `/dev/lirc*` devices appear:** Check `config.txt` for the correct overlays and reboot.
- **Only receiver appears:** Check that the transmitter overlay (`gpio-ir-tx` or `pwm-ir-tx`) is in `config.txt`.
- **Only transmitter appears:** Check that the receiver overlay (`gpio-ir`) is in `config.txt`.
- **Sending does nothing:** Check IR LED direction/aim, transistor pinout, carrier frequency, and whether the `.ir` file is empty or contains a valid recording.
- **Device order changes between reboots:** Use `IR_RECEIVE_DEVICE` or `IR_TRANSMIT_DEVICE` environment variables to force a specific `/dev/lirc*` device.
