import requests


def _buildUrl(settings, pathKey):
    baseUrl = settings["hostedApp"]["baseUrl"].rstrip("/")
    path = settings["hostedApp"][pathKey]
    return baseUrl + path


def _authHeaders(settings):
    return {"X-Agent-Token": settings["hostedApp"]["agentToken"]}


def getNextCommand(settings, logger):
    """Poll the hosted Flask app for the next pending command.

    Returns a tuple (command, urgent) where command is the command dict
    or None, and urgent is a bool indicating if a browser session is active.
    """
    url = _buildUrl(settings, "nextCommandPath")
    timeout = settings["hostedApp"].get("requestTimeoutSeconds", 10)

    try:
        resp = requests.get(url, headers=_authHeaders(settings), timeout=timeout)
        resp.raise_for_status()
    except requests.ConnectionError as e:
        logger.warning(f"Connection error polling for commands: {e}")
        return None, False
    except requests.Timeout:
        logger.warning("Timeout polling for commands")
        return None, False
    except requests.HTTPError as e:
        logger.warning(f"HTTP error polling for commands: {e}")
        return None, False

    try:
        body = resp.json()
    except ValueError:
        logger.error("Malformed JSON response from next-command endpoint")
        return None, False

    if not body.get("ok"):
        logger.warning(f"Server returned ok=false: {body}")
        return None, False

    return body.get("command"), body.get("urgent", False)


def reportCommandResult(settings, commandId, success, message, logger):
    """Report a command result back to the hosted Flask app. Returns True on success."""
    url = _buildUrl(settings, "commandResultPath")
    timeout = settings["hostedApp"].get("requestTimeoutSeconds", 10)
    payload = {
        "commandId": commandId,
        "success": success,
        "message": message
    }

    try:
        resp = requests.post(url, json=payload, headers=_authHeaders(settings), timeout=timeout)
        resp.raise_for_status()
        logger.info(f"Reported result for command {commandId}: success={success}")
        return True
    except requests.ConnectionError as e:
        logger.warning(f"Connection error reporting result for {commandId}: {e}")
        return False
    except requests.Timeout:
        logger.warning(f"Timeout reporting result for {commandId}")
        return False
    except requests.HTTPError as e:
        logger.warning(f"HTTP error reporting result for {commandId}: {e}")
        return False


def pushReceiverState(settings, state, logger):
    """Push the current receiver state to the hosted Flask app."""
    baseUrl = settings["hostedApp"]["baseUrl"].rstrip("/")
    url = baseUrl + "/api/agent/receiver-state"
    timeout = settings["hostedApp"].get("requestTimeoutSeconds", 10)

    try:
        resp = requests.post(url, json=state, headers=_authHeaders(settings), timeout=timeout)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"Failed to push receiver state: {e}")
        return False
