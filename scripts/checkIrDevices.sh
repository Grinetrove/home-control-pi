#!/bin/bash


if ! command -v ir-ctl &>/dev/null; then
    echo "ERROR: ir-ctl not found. Install v4l-utils:"
    echo "  sudo apt install v4l-utils"
    exit 1
fi

echo "=== IR Device Check ==="
echo ""

# List devices
DEVICES=$(ls /dev/lirc* 2>/dev/null)

if [ -z "$DEVICES" ]; then
    echo "No /dev/lirc* devices detected."
    echo ""
    echo "Possible fixes:"
    echo "  1. Check config.txt for IR overlays (gpio-ir, gpio-ir-tx, pwm-ir-tx)."
    echo "  2. Reboot after editing config.txt."
    echo "  3. Verify wiring connections."
    echo ""
    echo "config.txt is usually at: /boot/firmware/config.txt"
    echo "On older installs it may be: /boot/config.txt"
    exit 0
fi

for dev in $DEVICES; do
    echo "--- $dev ---"
    ir-ctl -d "$dev" --features 2>&1 || echo "  (could not read features)"
    echo ""
done

echo "Done!"
