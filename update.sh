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

echo "Restarting piAgent.service..."
systemctl restart piAgent.service

echo ""
systemctl status piAgent.service --no-pager || true
