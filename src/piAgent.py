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
from src.receiverController import getBasicStatus

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
ACTIVE_INTERVAL = 0.5      # Someone has the page open
ACTIVE_DURATION = 35.0     # How long to stay active after a session ping
STATE_PUSH_INTERVAL = 5.0  # How often to push receiver state when active (seconds)


def _currentInterval(activeUntil):
    """Return the appropriate poll interval based on current timers."""
    now = time.time()
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

    # Adaptive polling timer (epoch timestamp for when active mode expires)
    activeUntil = 0.0
    lastStatePush = 0.0

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

                # If the server says a browser session is active, reset active timer
                if urgent:
                    activeUntil = now + ACTIVE_DURATION
                    logger.debug("Session ping received, active for 35s")

                # Push receiver state periodically while someone is watching
                if now < activeUntil and (now - lastStatePush) >= STATE_PUSH_INTERVAL:
                    yamahaEnabled = settings["yamaha"].get("enabled", False)
                    if yamahaEnabled:
                        state = getBasicStatus(settings, logger)
                        if state is not None:
                            flaskClient.pushReceiverState(settings, state, logger)
                            lastStatePush = now

            interval = _currentInterval(activeUntil)

            # Log mode transitions
            currentMode = "active" if time.time() < activeUntil else "idle"
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
