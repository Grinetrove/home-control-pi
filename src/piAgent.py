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
    }
    writeStatus(status)

    pollInterval = settings["agent"]["pollIntervalSeconds"]
    statusWriteInterval = settings["agent"]["statusWriteIntervalSeconds"]
    lastStatusWrite = time.time()

    hostedAppEnabled = settings["hostedApp"].get("enabled", False)
    if hostedAppEnabled:
        status["agentState"] = "polling"
        logger.info("Hosted app enabled, entering polling mode")
    else:
        status["agentState"] = "heartbeat"
        logger.info("Hosted app disabled, entering heartbeat-only mode")

    while running:
        try:
            if hostedAppEnabled:
                _pollAndDispatch(settings, status, logger)

            now = time.time()
            if now - lastStatusWrite >= statusWriteInterval:
                status["lastUpdated"] = nowIso()
                writeStatus(status)
                lastStatusWrite = now

            _interruptibleSleep(pollInterval)

        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            status["lastError"] = {"error": str(e), "time": nowIso()}
            status["lastUpdated"] = nowIso()
            writeStatus(status)
            _interruptibleSleep(pollInterval)

    status["agentState"] = "stopped"
    status["lastUpdated"] = nowIso()
    writeStatus(status)
    logger.info("piAgent stopped")


def _pollAndDispatch(settings, status, logger):
    command = flaskClient.getNextCommand(settings, logger)
    status["lastPollTime"] = nowIso()

    if command is None:
        return

    commandId = command.get("commandId", "unknown")
    logger.info(f"Received command: {commandId} device={command.get('device')} action={command.get('action')}")
    status["lastCommand"] = {"commandId": commandId, "time": nowIso()}

    success, message = dispatchCommand(command, settings, logger)
    status["lastResult"] = {"commandId": commandId, "success": success, "message": message, "time": nowIso()}

    if not success:
        status["lastError"] = {"commandId": commandId, "error": message, "time": nowIso()}

    flaskClient.reportCommandResult(settings, commandId, success, message, logger)


def _interruptibleSleep(seconds):
    """Sleep in small increments so signal handlers can interrupt promptly."""
    end = time.time() + seconds
    while running and time.time() < end:
        time.sleep(min(0.5, end - time.time()))


if __name__ == "__main__":
    main()
