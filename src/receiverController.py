"""
Yamaha HTR-4065 receiver controller.
Sends XML commands over HTTP to the receiver's YamahaRemoteControl endpoint.
"""

from xml.etree import ElementTree as ET

import requests

# ---------------------------------------------------------------------------
# Config defaults (overridden by settings.json at runtime)
# ---------------------------------------------------------------------------
VOLUME_STEP_DB = 0.5
VOLUME_MIN_DB = -80.0
VOLUME_MAX_DB = -20.0


# ---------------------------------------------------------------------------
# XML helpers (ported from LocalRecieverTesting/yamahaRemote.py)
# ---------------------------------------------------------------------------
def _receiverUrl(settings):
    ip = settings["yamaha"]["receiverIp"]
    port = settings["yamaha"].get("receiverPort", 80)
    return f"http://{ip}:{port}/YamahaRemoteControl/ctrl"


def _timeout(settings):
    return settings["yamaha"].get("requestTimeoutSeconds", 3)


def _postXml(settings, xmlStr):
    resp = requests.post(
        _receiverUrl(settings),
        data=xmlStr.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=_timeout(settings),
    )
    resp.raise_for_status()
    return resp.text


def _buildPut(pathParts, value):
    inner = f"<{pathParts[-1]}>{value}</{pathParts[-1]}>"
    for tag in reversed(pathParts[:-1]):
        inner = f"<{tag}>{inner}</{tag}>"
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<YAMAHA_AV cmd="PUT">{inner}</YAMAHA_AV>'
    )


def _buildGet(pathParts):
    inner = f"<{pathParts[-1]}>GetParam</{pathParts[-1]}>"
    for tag in reversed(pathParts[:-1]):
        inner = f"<{tag}>{inner}</{tag}>"
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<YAMAHA_AV cmd="GET">{inner}</YAMAHA_AV>'
    )


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------
def _getVolumeDb(settings):
    xml = _postXml(settings, _buildGet(["Main_Zone", "Volume", "Lvl"]))
    root = ET.fromstring(xml)
    val = int(root.findtext(".//Val"))
    exp = int(root.findtext(".//Exp") or "1")
    return val / (10 ** exp)


def _setVolumeDb(settings, newDb):
    newDb = max(VOLUME_MIN_DB, min(VOLUME_MAX_DB, float(newDb)))
    val = int(round(newDb * 10))
    body = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<YAMAHA_AV cmd="PUT"><Main_Zone>'
        '<Volume><Lvl>'
        f'<Val>{val}</Val><Exp>1</Exp><Unit>dB</Unit>'
        '</Lvl></Volume>'
        '</Main_Zone></YAMAHA_AV>'
    )
    _postXml(settings, body)


def _getMuteState(settings):
    xml = _postXml(settings, _buildGet(["Main_Zone", "Volume", "Mute"]))
    root = ET.fromstring(xml)
    return root.findtext(".//Mute") or "unknown"


def getBasicStatus(settings, logger):
    """Read power, input, volume, and mute from the receiver.
    Returns a dict with the state or None on failure.
    """
    try:
        xml = _postXml(settings, _buildGet(["Main_Zone", "Basic_Status"]))
        root = ET.fromstring(xml)
        power = root.findtext(".//Power_Control/Power") or "unknown"
        inputSel = root.findtext(".//Input/Input_Sel") or "unknown"
        volVal = root.findtext(".//Volume/Lvl/Val")
        volExp = root.findtext(".//Volume/Lvl/Exp") or "1"
        mute = root.findtext(".//Volume/Mute") or "unknown"

        volume = None
        if volVal is not None:
            volume = int(volVal) / (10 ** int(volExp))

        return {
            "power": power,
            "input": inputSel,
            "volume": volume,
            "mute": mute,
        }
    except Exception as e:
        logger.warning(f"Failed to read receiver status: {e}")
        return None


# ---------------------------------------------------------------------------
# Action handlers -- each returns (success: bool, message: str)
# ---------------------------------------------------------------------------
def powerOn(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "Power_Control", "Power"], "On"))
    logger.info("Receiver: powerOn sent")
    return True, "powerOn sent"


def powerOff(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "Power_Control", "Power"], "Standby"))
    logger.info("Receiver: powerOff (standby) sent")
    return True, "powerOff sent"


def volumeUp(settings, logger):
    cur = _getVolumeDb(settings)
    _setVolumeDb(settings, cur + VOLUME_STEP_DB)
    newVol = _getVolumeDb(settings)
    logger.info(f"Receiver: volumeUp {cur} -> {newVol} dB")
    return True, f"volume {newVol} dB"


def volumeDown(settings, logger):
    cur = _getVolumeDb(settings)
    _setVolumeDb(settings, cur - VOLUME_STEP_DB)
    newVol = _getVolumeDb(settings)
    logger.info(f"Receiver: volumeDown {cur} -> {newVol} dB")
    return True, f"volume {newVol} dB"


def muteToggle(settings, logger):
    current = _getMuteState(settings)
    newState = "Off" if current.strip() == "On" else "On"
    _postXml(settings, _buildPut(["Main_Zone", "Volume", "Mute"], newState))
    logger.info(f"Receiver: mute toggled to {newState}")
    return True, f"mute {newState}"


def hdmi1(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "Input", "Input_Sel"], "HDMI1"))
    logger.info("Receiver: input HDMI1")
    return True, "input HDMI1"


def hdmi2(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "Input", "Input_Sel"], "HDMI2"))
    logger.info("Receiver: input HDMI2")
    return True, "input HDMI2"


def hdmi3(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "Input", "Input_Sel"], "HDMI3"))
    logger.info("Receiver: input HDMI3")
    return True, "input HDMI3"


def hdmi4(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "Input", "Input_Sel"], "HDMI4"))
    logger.info("Receiver: input HDMI4")
    return True, "input HDMI4"


def airplay(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "Input", "Input_Sel"], "AirPlay"))
    logger.info("Receiver: input AirPlay")
    return True, "input AirPlay"


# -- Menu / Cursor --

def cursorUp(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "List_Control", "Cursor"], "Up"))
    return True, "cursor Up"


def cursorDown(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "List_Control", "Cursor"], "Down"))
    return True, "cursor Down"


def cursorLeft(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "List_Control", "Cursor"], "Left"))
    return True, "cursor Left"


def cursorRight(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "List_Control", "Cursor"], "Right"))
    return True, "cursor Right"


def cursorSelect(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "List_Control", "Cursor"], "Sel"))
    return True, "cursor Select"


def cursorReturn(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "List_Control", "Cursor"], "Return"))
    return True, "cursor Return"


def menuOnScreen(settings, logger):
    _postXml(settings, _buildPut(["Main_Zone", "List_Control", "Menu_Control"], "On Screen"))
    return True, "menu On Screen"


# -- AirPlay playback --

def airplayPlay(settings, logger):
    _postXml(settings, _buildPut(["AirPlay", "Play_Control", "Playback"], "Play"))
    return True, "airplay Play"


def airplayPause(settings, logger):
    _postXml(settings, _buildPut(["AirPlay", "Play_Control", "Playback"], "Pause"))
    return True, "airplay Pause"


def airplaySkipFwd(settings, logger):
    _postXml(settings, _buildPut(["AirPlay", "Play_Control", "Playback"], "Skip Fwd"))
    return True, "airplay Skip Fwd"


def airplaySkipRev(settings, logger):
    _postXml(settings, _buildPut(["AirPlay", "Play_Control", "Playback"], "Skip Rev"))
    return True, "airplay Skip Rev"


# -- Status query --

def getStatus(settings, logger):
    state = getBasicStatus(settings, logger)
    if state is None:
        return False, "Failed to read receiver status"
    import json
    return True, json.dumps(state)


# ---------------------------------------------------------------------------
# Maps action names to handler functions
# ---------------------------------------------------------------------------
actionMap = {
    "powerOn": powerOn,
    "powerOff": powerOff,
    "volumeUp": volumeUp,
    "volumeDown": volumeDown,
    "muteToggle": muteToggle,
    "hdmi1": hdmi1,
    "hdmi2": hdmi2,
    "hdmi3": hdmi3,
    "hdmi4": hdmi4,
    "airplay": airplay,
    "cursorUp": cursorUp,
    "cursorDown": cursorDown,
    "cursorLeft": cursorLeft,
    "cursorRight": cursorRight,
    "cursorSelect": cursorSelect,
    "cursorReturn": cursorReturn,
    "menuOnScreen": menuOnScreen,
    "airplayPlay": airplayPlay,
    "airplayPause": airplayPause,
    "airplaySkipFwd": airplaySkipFwd,
    "airplaySkipRev": airplaySkipRev,
    "getStatus": getStatus,
}
