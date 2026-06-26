#!/bin/bash
set -e

echo "=== piAgent.service status ==="
systemctl status piAgent.service --no-pager || true

echo ""
echo "=== /var/lib/homeControl/status.json ==="
if [ -f /var/lib/homeControl/status.json ]; then
    cat /var/lib/homeControl/status.json
else
    echo "(status file does not exist yet)"
fi
