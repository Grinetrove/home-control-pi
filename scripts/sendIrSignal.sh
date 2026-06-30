#!/bin/bash

set -e

SIGNAL_FILE="$1"
CARRIER="${IR_CARRIER:-38000}"

if [ -z "$SIGNAL_FILE" ]; then
    echo "ERROR: No signal file provided."
    echo "Usage: $0 <path-to-ir-file>"
    exit 1
fi

if [ ! -f "$SIGNAL_FILE" ]; then
    echo "ERROR: Signal file does not exist: $SIGNAL_FILE"
    exit 1
fi

if ! command -v ir-ctl &>/dev/null; then
    echo "ERROR: ir-ctl not found. Install v4l-utils:"
    echo "  sudo apt install v4l-utils"
    exit 1
fi


if [ -n "$IR_TRANSMIT_DEVICE" ]; then
    TX_DEVICE="$IR_TRANSMIT_DEVICE"
    echo "Using override transmit device: $TX_DEVICE"
else
    # Auto-detect a transmit-capable /dev/lirc* device
    TX_DEVICE=""
    for dev in /dev/lirc*; do
        if [ ! -e "$dev" ]; then
            continue
        fi
        features=$(ir-ctl -d "$dev" --features 2>/dev/null || true)
        if echo "$features" | grep -qi "send"; then
            TX_DEVICE="$dev"
            break
        fi
    done

    if [ -z "$TX_DEVICE" ]; then
        # Check if any lirc devices exist at all
        if ! ls /dev/lirc* &>/dev/null; then
            echo "ERROR: No /dev/lirc* devices found."
            echo "Check your config.txt overlays and reboot."
        else
            echo "ERROR: No transmit-capable /dev/lirc* device found."
            echo "Devices detected:"
            ls /dev/lirc* 2>/dev/null
            echo ""
            echo "Run ./scripts/checkIrDevices.sh to see device features."
        fi
        exit 1
    fi

    echo "Auto-detected transmit device: $TX_DEVICE"
fi

# ---- Send the signal ----
echo "Sending: $SIGNAL_FILE (carrier: ${CARRIER}Hz)"
ir-ctl -d "$TX_DEVICE" --carrier="$CARRIER" --send="$SIGNAL_FILE"
RESULT=$?

if [ $RESULT -ne 0 ]; then
    echo "ERROR: ir-ctl exited with code $RESULT"
    exit $RESULT
fi

echo "Signal sent successfully."
