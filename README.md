# Home Control Pi Agent

A Raspberry Pi 4 agent that gets commands from a hosted web app for home control commands to execute them on my local network

Had this running on localhost for a while and decided it was time for an upgrade. Not a fan of having to turn it on on my computer, plus I'd like to be able to check if I left my projector on or my lights on after I leave the house.

## How It Works

1. The agent runs as a systemd service (`piAgent.service`) on the Pi.
2. It polls the hosted web app for pending commands.
3. Commands are validated against a whitelist of allowed device/action combinations.
4. Results are reported back to the web app.
5. If the hosted app is unreachable or disabled, the agent runs in heartbeat-only mode.

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
src/receiverController.py      Yamaha receiver placeholder handlers
systemd/piAgent.service        Systemd unit file
install.sh                     First-time install script
update.sh                      Pull and restart script
scripts/                       Helper scripts for status, logs, restart
docs/                          Setup documentation
```
