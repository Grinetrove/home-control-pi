import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.settingsLoader import loadSettings
from src import flaskClient
from src.commandDispatcher import dispatchCommand

logDir = "/var/log/homeControl"
statusFilePath = "/var/lib/homeControl/status.json"

running = True


def handleShutdown(signum, frame):
    global running
    running = False


def setupLogging(settings):
    logConfig = settings.get("logging", {})
    levelName = logConfig.get("logLevel", "INFO")
    maxBytes = logConfig.get("maxLogSizeMb", 5) * 1024 * 1024
    backupCount = logConfig.get("backupCount", 3)

    logger = logging.getLogger("piAgent")
    logger.setLevel(getattr(logging, levelName, logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    agentHandler = RotatingFileHandler(
        os.path.join(logDir, "agent.log"),
        maxBytes=maxBytes,
        backupCount=backupCount
    )
    agentHandler.setLevel(logging.DEBUG)
    agentHandler.setFormatter(formatter)
    logger.addHandler(agentHandler)

    errorHandler = RotatingFileHandler(
        os.path.join(logDir, "error.log"),
        maxBytes=maxBytes,
        backupCount=backupCount
    )
    errorHandler.setLevel(logging.ERROR)
    errorHandler.setFormatter(formatter)
    logger.addHandler(errorHandler)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(logging.DEBUG)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    return logger


def writeStatus(status):
    try:
        statusDir = os.path.dirname(statusFilePath)
        os.makedirs(statusDir, exist_ok=True)
        tmpPath = statusFilePath + ".tmp"
        with open(tmpPath, "w") as f:
            json.dump(status, f, indent=2)
        os.replace(tmpPath, statusFilePath)
    except Exception:
        pass


def nowIso():
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Adaptive polling intervals (seconds)
# ---------------------------------------------------------------------------
IDLE_INTERVAL = 15.0       # No one on the page
ACTIVE_INTERVAL = 2.0      # Someone opened / returned to the page
BURST_INTERVAL = 0.25      # A command was just received (rapid-fire buttons)
ACTIVE_DURATION = 60.0     # How long to stay in active mode after session ping
BURST_DURATION = 10.0      # How long to stay in burst mode after a command


def _currentInterval(activeUntil, burstUntil):
    """Return the appropriate poll interval based on current timers."""
    now = time.time()
    if now < burstUntil:
        return BURST_INTERVAL
    if now < activeUntil:
        return ACTIVE_INTERVAL
    return IDLE_INTERVAL


def main():
    global running

    signal.signal(signal.SIGTERM, handleShutdown)
    signal.signal(signal.SIGINT, handleShutdown)

    os.makedirs(logDir, exist_ok=True)

    try:
        settings = loadSettings()
    except Exception as e:
        print(f"FATAL: Failed to load settings: {e}", file=sys.stderr)
        sys.exit(1)

    logger = setupLogging(settings)
    logger.info("piAgent starting")

    status = {
        "agentState": "starting",
        "agentName": settings["agent"].get("agentName", "unknown"),
        "startedAt": nowIso(),
        "lastUpdated": nowIso(),
        "hostedAppEnabled": settings["hostedApp"].get("enabled", False),
        "lastPollTime": None,
        "lastCommand": None,
        "lastResult": None,
        "lastError": None,
        "pollMode": "idle",
    }
    writeStatus(status)

    statusWriteInterval = settings["agent"]["statusWriteIntervalSeconds"]
    lastStatusWrite = time.time()

    # Adaptive polling timers (epoch timestamps for when each mode expires)
    activeUntil = 0.0
    burstUntil = 0.0

    hostedAppEnabled = settings["hostedApp"].get("enabled", False)
    if hostedAppEnabled:
        status["agentState"] = "polling"
        logger.info("Hosted app enabled, entering adaptive polling mode")
    else:
        status["agentState"] = "heartbeat"
        logger.info("Hosted app disabled, entering heartbeat-only mode")

    prevMode = None

    while running:
        try:
            if hostedAppEnabled:
                command, urgent = _pollAndDispatch(settings, status, logger)

                now = time.time()

                # If the server says a browser session is active, enter active mode
                if urgent and now >= activeUntil:
                    activeUntil = now + ACTIVE_DURATION
                    logger.info("Session active, switching to 2s polling for 60s")

                # If we received a command, enter burst mode
                if command is not None:
                    burstUntil = now + BURST_DURATION
                    # Also extend active mode so we don't drop to idle right after burst
                    if activeUntil < burstUntil:
                        activeUntil = burstUntil
                    logger.info("Command received, switching to 0.25s polling for 10s")

            interval = _currentInterval(activeUntil, burstUntil)

            # Log mode transitions
            currentMode = "burst" if time.time() < burstUntil else ("active" if time.time() < activeUntil else "idle")
            if currentMode != prevMode:
                if prevMode is not None:
                    logger.info(f"Poll mode: {prevMode} -> {currentMode} (interval={interval}s)")
                status["pollMode"] = currentMode
                prevMode = currentMode

            now = time.time()
            if now - lastStatusWrite >= statusWriteInterval:
                status["lastUpdated"] = nowIso()
                writeStatus(status)
                lastStatusWrite = now

            _interruptibleSleep(interval)

        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            status["lastError"] = {"error": str(e), "time": nowIso()}
            status["lastUpdated"] = nowIso()
            writeStatus(status)
            _interruptibleSleep(IDLE_INTERVAL)

    status["agentState"] = "stopped"
    status["lastUpdated"] = nowIso()
    writeStatus(status)
    logger.info("piAgent stopped")


def _pollAndDispatch(settings, status, logger):
    """Poll for the next command and dispatch it.

    Returns a tuple (command, urgent) so the main loop can adjust polling.
    """
    command, urgent = flaskClient.getNextCommand(settings, logger)
    status["lastPollTime"] = nowIso()

    if command is None:
        return None, urgent

    commandId = command.get("commandId", "unknown")
    logger.info(f"Received command: {commandId} device={command.get('device')} action={command.get('action')}")
    status["lastCommand"] = {"commandId": commandId, "time": nowIso()}

    success, message = dispatchCommand(command, settings, logger)
    status["lastResult"] = {"commandId": commandId, "success": success, "message": message, "time": nowIso()}

    if not success:
        status["lastError"] = {"commandId": commandId, "error": message, "time": nowIso()}

    flaskClient.reportCommandResult(settings, commandId, success, message, logger)
    return command, urgent


def _interruptibleSleep(seconds):
    """Sleep in small increments so signal handlers can interrupt promptly."""
    end = time.time() + seconds
    while running and time.time() < end:
        time.sleep(min(0.1, end - time.time()))


if __name__ == "__main__":
    main()
