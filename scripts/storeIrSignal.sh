#!/bin/bash
# storeIrSignal.sh - Record/store a raw IR signal from a remote into a file.
#
# Usage: ./scripts/storeIrSignal.sh storedSignals/projectorOn.ir
#
# Environment overrides:
#   IR_RECEIVE_DEVICE  - Force a specific /dev/lirc* device for receiving.

set -e

DEST_FILE="$1"

# ---- Validate arguments ----
if [ -z "$DEST_FILE" ]; then
    echo "ERROR: No destination file provided."
    echo "Usage: $0 <path-to-save-ir-file>"
    exit 1
fi

# ---- Check for ir-ctl ----
if ! command -v ir-ctl &>/dev/null; then
    echo "ERROR: ir-ctl not found. Install v4l-utils:"
    echo "  sudo apt install v4l-utils"
    exit 1
fi

# ---- Find receive device ----
if [ -n "$IR_RECEIVE_DEVICE" ]; then
    RX_DEVICE="$IR_RECEIVE_DEVICE"
    echo "Using override receive device: $RX_DEVICE"
else
    # Auto-detect a receive-capable /dev/lirc* device
    RX_DEVICE=""
    for dev in /dev/lirc*; do
        if [ ! -e "$dev" ]; then
            continue
        fi
        features=$(ir-ctl -d "$dev" --features 2>/dev/null || true)
        if echo "$features" | grep -qi "receive"; then
            RX_DEVICE="$dev"
            break
        fi
    done

    if [ -z "$RX_DEVICE" ]; then
        if ! ls /dev/lirc* &>/dev/null; then
            echo "ERROR: No /dev/lirc* devices found."
            echo "Check your config.txt overlays and reboot."
        else
            echo "ERROR: No receive-capable /dev/lirc* device found."
            echo "Devices detected:"
            ls /dev/lirc* 2>/dev/null
            echo ""
            echo "Run ./scripts/checkIrDevices.sh to see device features."
        fi
        exit 1
    fi

    echo "Auto-detected receive device: $RX_DEVICE"
fi

# ---- Create parent directory if needed ----
DEST_DIR=$(dirname "$DEST_FILE")
if [ ! -d "$DEST_DIR" ]; then
    echo "Creating directory: $DEST_DIR"
    mkdir -p "$DEST_DIR"
fi

# ---- Record ----
echo ""
echo "=== IR Signal Recording ==="
echo "Device: $RX_DEVICE"
echo "Output: $DEST_FILE"
echo ""
echo "Instructions:"
echo "  1. Point your remote at the IR receiver."
echo "  2. Press the button you want to record ONCE."
echo "  3. Wait a moment, then press Ctrl+C to stop recording."
echo ""
echo "Recording now..."
echo ""

ir-ctl -d "$RX_DEVICE" --receive="$DEST_FILE"

echo ""
if [ -s "$DEST_FILE" ]; then
    echo "Signal saved to: $DEST_FILE"
else
    echo "WARNING: File is empty. No signal was captured."
    echo "Check receiver wiring and try again."
fi
