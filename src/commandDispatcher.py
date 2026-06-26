from src import receiverController

# Whitelisted devices and their allowed actions
allowedDevices = {
    "receiver": list(receiverController.actionMap.keys()),
}

requiredFields = ["commandId", "device", "action", "value"]


def dispatchCommand(command, settings, logger):
    """Validate and dispatch a command. Returns (success: bool, message: str)."""
    if not isinstance(command, dict):
        return False, "Command is not a dictionary"

    for field in requiredFields:
        if field not in command:
            return False, f"Missing required field: {field}"

    if command["value"] is not None:
        return False, "Non-null value is not supported in v1"

    device = command["device"]
    action = command["action"]

    if device not in allowedDevices:
        return False, f"Unknown device: {device}"

    if action not in allowedDevices[device]:
        return False, f"Unknown action '{action}' for device '{device}'"

    logger.info(f"Dispatching: device={device} action={action}")

    try:
        if device == "receiver":
            handler = receiverController.actionMap[action]
            success, message = handler(settings, logger)
            return success, message
    except Exception as e:
        logger.error(f"Error dispatching {device}/{action}: {e}")
        return False, f"Dispatch error: {e}"

    return False, f"No handler implemented for device: {device}"
