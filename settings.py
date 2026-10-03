"""
Saved settings for Kape Tayo (settings.json).

Stores the user's choices so they are still there the next time the app
opens:
  - units: "km" or "miles"
  - radius_m: café search radius in meters
  - vehicle: "car", "bike", or "foot"
  - last_location: the most recent place searched, so the user can press
    Enter to reuse it (this also saves 1 GraphHopper credit)

If settings.json is missing, broken, or has a bad value, that value falls
back to its default instead of crashing the app.
"""
import json
from pathlib import Path

from graphhopper_api import VEHICLES

# Saved next to this file, so it works no matter which folder you run from.
SETTINGS_FILE = Path(__file__).parent / "settings.json"

UNITS = ["km", "miles"]
MIN_RADIUS_M = 100
MAX_RADIUS_M = 5000

DEFAULTS = {
    "units": "km",
    "radius_m": 1000,
    "vehicle": "foot",
    "last_location": None,  # becomes {"name": ..., "lat": ..., "lng": ...}
}


def _is_valid_location(location):
    """Check that a saved location has a name and numeric lat/lng."""
    return (isinstance(location, dict)
            and isinstance(location.get("name"), str)
            and isinstance(location.get("lat"), (int, float))
            and isinstance(location.get("lng"), (int, float)))


def load_settings():
    """Read settings.json and return a complete, valid settings dict."""
    settings = dict(DEFAULTS)
    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # No file yet (first run) or the file is broken: use the defaults.
        return settings
    if not isinstance(saved, dict):
        return settings

    # Copy each saved value only if it is valid. Bad values keep the default.
    if saved.get("units") in UNITS:
        settings["units"] = saved["units"]
    radius = saved.get("radius_m")
    if isinstance(radius, int) and MIN_RADIUS_M <= radius <= MAX_RADIUS_M:
        settings["radius_m"] = radius
    if saved.get("vehicle") in VEHICLES:
        settings["vehicle"] = saved["vehicle"]
    if _is_valid_location(saved.get("last_location")):
        settings["last_location"] = saved["last_location"]
    return settings


def save_settings(settings):
    """Write settings to settings.json. Returns an error message or None."""
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False),
                                 encoding="utf-8")
    except OSError:
        return "Could not save your settings to settings.json."
    return None
