# Fresh Raspberry Pi Setup

Start here after installing Raspberry Pi OS Lite 64-bit and connecting via SSH.

## 1. Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

## 2. Install required packages

```bash
sudo apt install -y git python3 python3-venv
```

## 3. Clone the repository

```bash
sudo git clone https://github.com/Grinetrove/home-control-pi.git /opt/homeControl
```

## 4. Run the installer

```bash
cd /opt/homeControl
sudo ./install.sh
```

This creates the 'homecontrol' system user, directories, virtual environment, and starts the service.

## 5. Edit settings

```bash
sudo nano /etc/homeControl/settings.json
```

At minimum:
- Set 'hostedApp.enabled' to 'true' when the site is up.
- Replace 'REPLACE_WITH_AGENT_TOKEN/ with the domain.
- Replace 'REPLACE_WITH_AGENT_TOKEN/ with the agent token set on the page.
- Confirm `yamaha.receiverIp` matches your receiver's IP.

## 6. Restart the service

```bash
sudo systemctl restart piAgent.service
```

## 7. Verify the service is running

```bash
sudo systemctl status piAgent.service
cat /var/lib/homeControl/status.json
```

## 8. Reboot and confirm auto-start

```bash
sudo reboot
```

After reboot, SSH back in and check:

```bash
sudo systemctl status piAgent.service
```

The service should be active and running.

## Useful Commands

| Task | Command |
|------|---------|
| View live logs | `sudo journalctl -u piAgent.service -f` |
| Check status | `sudo ./scripts/status.sh` |
| Restart | `sudo systemctl restart piAgent.service` |
| Update from GitHub | `cd /opt/homeControl && sudo ./update.sh` |
| Edit settings | `sudo nano /etc/homeControl/settings.json` |
