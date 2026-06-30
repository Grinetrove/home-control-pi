#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run with sudo."
    exit 1
fi

INSTALL_DIR="/opt/homeControl"

echo "=== Updating Home Control Pi Agent ==="

echo "Pulling latest changes..."
cd "$INSTALL_DIR"
git pull

echo "Installing dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --quiet

# Ensure IR scripts are executable
chmod +x "$INSTALL_DIR/scripts/sendIrSignal.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/storeIrSignal.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/checkIrDevices.sh" 2>/dev/null || true

# Create storedSignals directory and blank placeholders (do not overwrite existing recordings)
mkdir -p "$INSTALL_DIR/storedSignals"
for irFile in projectorOn.ir projectorOff.ir toggleSoundbar.ir; do
    if [ ! -s "$INSTALL_DIR/storedSignals/$irFile" ]; then
        touch "$INSTALL_DIR/storedSignals/$irFile"
    fi
done

echo "Restarting piAgent.service..."
systemctl restart piAgent.service

echo ""
systemctl status piAgent.service --no-pager || true
