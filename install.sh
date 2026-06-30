#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo."
    exit 1
fi

INSTALL_DIR="/opt/homeControl"
CONFIG_DIR="/etc/homeControl"
LOG_DIR="/var/log/homeControl"
STATE_DIR="/var/lib/homeControl"
SERVICE_USER="homecontrol"

echo "=== Home Control Pi Agent Installer ==="

# Create system user if missing
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating system user: $SERVICE_USER"
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

# Create directories
echo "Creating directories..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$STATE_DIR"

# Set ownership
chown "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
chown "$SERVICE_USER:$SERVICE_USER" "$STATE_DIR"

# Install system dependencies for IR control
echo "Installing system dependencies..."
apt-get install -y v4l-utils --quiet 2>/dev/null || apt install -y v4l-utils

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --quiet

# Make IR scripts executable
echo "Setting up IR scripts..."
chmod +x "$INSTALL_DIR/scripts/sendIrSignal.sh"
chmod +x "$INSTALL_DIR/scripts/storeIrSignal.sh"
chmod +x "$INSTALL_DIR/scripts/checkIrDevices.sh"

# Create storedSignals directory and blank placeholders
mkdir -p "$INSTALL_DIR/storedSignals"
for irFile in projectorOn.ir projectorOff.ir toggleSoundbar.ir; do
    if [ ! -s "$INSTALL_DIR/storedSignals/$irFile" ]; then
        touch "$INSTALL_DIR/storedSignals/$irFile"
    fi
done

# Copy example settings if real settings don't exist
if [ ! -f "$CONFIG_DIR/settings.json" ]; then
    echo "Copying example settings to $CONFIG_DIR/settings.json"
    cp "$INSTALL_DIR/config/settings.example.json" "$CONFIG_DIR/settings.json"
    chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR/settings.json"
    chmod 600 "$CONFIG_DIR/settings.json"
else
    echo "Settings file already exists, skipping copy."
fi

# Install systemd service
echo "Installing systemd service..."
cp "$INSTALL_DIR/systemd/piAgent.service" /etc/systemd/system/piAgent.service
systemctl daemon-reload
systemctl enable piAgent.service

# Set repo ownership so the service user can read it
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# Start the service
echo "Starting piAgent.service..."
systemctl restart piAgent.service

echo ""
echo "=== Installation complete ==="
echo ""
systemctl status piAgent.service --no-pager || true
echo ""
echo "Next steps:"
echo "  1. Edit settings:  sudo nano $CONFIG_DIR/settings.json"
echo "  2. Restart service: sudo systemctl restart piAgent.service"
echo "  3. Check status:    sudo systemctl status piAgent.service"
echo "  4. View logs:       sudo journalctl -u piAgent.service -f"
echo ""
echo "IR setup (manual):"
echo "  - Edit /boot/firmware/config.txt to add IR overlays and reboot."
echo "  - Record signals with: ./scripts/storeIrSignal.sh storedSignals/<name>.ir"
echo "  - See README.md for wiring and config.txt details."
