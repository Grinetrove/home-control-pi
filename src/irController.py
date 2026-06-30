"""
IR controller - sends stored IR signal files via scripts/sendIrSignal.sh.
"""

import os
import subprocess

# Path to the send script, relative to the repo root
SEND_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "sendIrSignal.sh")

# Command name -> stored signal file (relative to repo root)
IR_COMMAND_MAP = {
    "projectorOn": os.path.join(os.path.dirname(__file__), "..", "storedSignals", "projectorOn.ir"),
    "projectorOff": os.path.join(os.path.dirname(__file__), "..", "storedSignals", "projectorOff.ir"),
    "toggleSoundbar": os.path.join(os.path.dirname(__file__), "..", "storedSignals", "toggleSoundbar.ir"),
}


def _sendIr(action, settings, logger):
    """Run sendIrSignal.sh with the matching stored signal file."""
    signalFile = IR_COMMAND_MAP.get(action)
    if signalFile is None:
        return False, f"No IR signal file mapped for action: {action}"

    signalFile = os.path.abspath(signalFile)
    sendScript = os.path.abspath(SEND_SCRIPT)

    if not os.path.isfile(sendScript):
        return False, f"Send script not found: {sendScript}"

    logger.info(f"IR: sending {action} via {signalFile}")

    try:
        result = subprocess.run(
            [sendScript, signalFile],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        logger.error(f"IR: sendIrSignal.sh timed out for {action}")
        return False, f"IR send timed out for {action}"
    except Exception as e:
        logger.error(f"IR: failed to run sendIrSignal.sh: {e}")
        return False, f"IR send error: {e}"

    if result.stdout.strip():
        logger.info(f"IR stdout: {result.stdout.strip()}")
    if result.stderr.strip():
        logger.warning(f"IR stderr: {result.stderr.strip()}")

    if result.returncode != 0:
        errMsg = result.stderr.strip() or result.stdout.strip() or "unknown error"
        return False, f"IR send failed for {action}: {errMsg}"

    return True, f"{action} sent"


def projectorOn(settings, logger):
    return _sendIr("projectorOn", settings, logger)


def projectorOff(settings, logger):
    return _sendIr("projectorOff", settings, logger)


def toggleSoundbar(settings, logger):
    return _sendIr("toggleSoundbar", settings, logger)


actionMap = {
    "projectorOn": projectorOn,
    "projectorOff": projectorOff,
    "toggleSoundbar": toggleSoundbar,
}
