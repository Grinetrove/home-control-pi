from src import receiverController
from src import irController

# Whitelisted devices and their allowed actions
allowedDevices = {
    "receiver": list(receiverController.actionMap.keys()),
    "ir": list(irController.actionMap.keys()),
}

# Actions that accept a value parameter
valuedActions = {"volumeSet"}

requiredFields = ["commandId", "device", "action"]


def dispatchCommand(command, settings, logger):
    """Validate and dispatch a command. Returns (success: bool, message: str)."""
    if not isinstance(command, dict):
        return False, "Command is not a dictionary"

    for field in requiredFields:
        if field not in command:
            return False, f"Missing required field: {field}"

    device = command["device"]
    action = command["action"]
    value = command.get("value")

    if device not in allowedDevices:
        return False, f"Unknown device: {device}"

    if action not in allowedDevices[device]:
        return False, f"Unknown action '{action}' for device '{device}'"

    # Reject unexpected values on non-valued actions
    if value is not None and action not in valuedActions:
        return False, f"Action '{action}' does not accept a value"

    logger.info(f"Dispatching: device={device} action={action} value={value}")

    try:
        if device == "receiver":
            handler = receiverController.actionMap[action]
            if action in valuedActions:
                success, message = handler(settings, logger, value=value)
            else:
                success, message = handler(settings, logger)
            return success, message
        if device == "ir":
            handler = irController.actionMap[action]
            success, message = handler(settings, logger)
            return success, message
    except Exception as e:
        logger.error(f"Error dispatching {device}/{action}: {e}")
        return False, f"Dispatch error: {e}"

    return False, f"No handler implemented for device: {device}"
