import json
import os

defaultSettingsPath = "/etc/homeControl/settings.json"

requiredSections = ["agent", "hostedApp", "yamaha", "logging"]


def loadSettings(path=None):
    """Load and validate settings from the config file."""
    settingsPath = path or defaultSettingsPath

    if not os.path.isfile(settingsPath):
        raise FileNotFoundError(f"Settings file not found: {settingsPath}")

    with open(settingsPath, "r") as f:
        settings = json.load(f)

    _validateSections(settings)
    _validateAgent(settings["agent"])
    _validateHostedApp(settings["hostedApp"])
    _validateLogging(settings["logging"])

    return settings


def _validateSections(settings):
    for section in requiredSections:
        if section not in settings:
            raise ValueError(f"Missing required settings section: {section}")


def _validateAgent(agent):
    pollInterval = agent.get("pollIntervalSeconds")
    if not isinstance(pollInterval, (int, float)) or pollInterval <= 0:
        raise ValueError("agent.pollIntervalSeconds must be a positive number")

    statusInterval = agent.get("statusWriteIntervalSeconds")
    if not isinstance(statusInterval, (int, float)) or statusInterval <= 0:
        raise ValueError("agent.statusWriteIntervalSeconds must be a positive number")


def _validateHostedApp(hostedApp):
    baseUrl = hostedApp.get("baseUrl", "")
    if not isinstance(baseUrl, str) or not baseUrl.strip():
        raise ValueError("hostedApp.baseUrl must be a non-empty string")

    if hostedApp.get("enabled", False):
        token = hostedApp.get("agentToken", "")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("hostedApp.agentToken is required when hostedApp.enabled is true")
        if token == "REPLACE_WITH_AGENT_TOKEN":
            raise ValueError("hostedApp.agentToken still has the placeholder value")


def _validateLogging(logging):
    validLevels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    level = logging.get("logLevel", "INFO")
    if level not in validLevels:
        raise ValueError(f"logging.logLevel must be one of {validLevels}")
