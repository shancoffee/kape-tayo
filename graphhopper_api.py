"""
GraphHopper API helpers for Kape Tayo.

This module talks to two GraphHopper APIs:
  - Geocoding: turns a place name into latitude and longitude
  - Routing: gets distance, travel time, and turn-by-turn directions

It is based on the geocoding and routing logic in
original_lab/graphhopper_parse-json_7.py, rewritten as reusable functions.

Design notes for whoever continues this project:
  - These functions never print and never ask for input. They only return
    data, so a terminal menu or a future GUI can both use them.
  - Every function returns a pair: (result, error).
    On success, error is None. On failure, result is None and error is a
    short message that is safe to show the user.
  - The API key is read from .env (GRAPHHOPPER_KEY) and is never printed.
  - Each call sends exactly one request (1 GraphHopper credit).
    The free plan allows 500 credits per day.
"""
import os

import requests
from dotenv import load_dotenv

GEOCODE_URL = "https://graphhopper.com/api/1/geocode"
ROUTE_URL = "https://graphhopper.com/api/1/route"

# Travel modes supported on the GraphHopper free plan (same as the lab).
VEHICLES = ["car", "bike", "foot"]

# Seconds to wait for GraphHopper before giving up, so the app never freezes.
TIMEOUT = 15

load_dotenv()


def _get_key():
    """Return the GraphHopper API key from .env, or None if it is missing."""
    return os.getenv("GRAPHHOPPER_KEY")


def _send_request(url, params):
    """Send one GET request to GraphHopper and return (json_data, error).

    Handles the problems the lab code did not: no internet, a slow server,
    and replies that are not valid JSON. The key travels inside params, so
    it never appears in any message we return.
    """
    try:
        reply = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        return None, "GraphHopper took too long to answer. Please try again."
    except requests.exceptions.ConnectionError:
        return None, "Cannot reach GraphHopper. Check your internet connection."
    except requests.exceptions.RequestException:
        return None, "Something went wrong while contacting GraphHopper."

    try:
        json_data = reply.json()
    except ValueError:
        return None, f"GraphHopper sent an unreadable reply (status {reply.status_code})."

    if reply.status_code == 200:
        return json_data, None

    # Friendlier messages for the errors we are most likely to see.
    if reply.status_code == 401:
        return None, "The GraphHopper API key is wrong. Check GRAPHHOPPER_KEY in .env."
    if reply.status_code == 429:
        return None, "Daily GraphHopper credits are used up. Try again tomorrow."
    # Same idea as the lab: show GraphHopper's own error message.
    message = json_data.get("message", "Unknown error")
    return None, f"GraphHopper error {reply.status_code}: {message}"


def geocode(location):
    """Find the coordinates of a place name.

    Args:
        location: what the user typed, for example "UST, Manila".

    Returns:
        (place, error) where place is a dict like
        {"lat": 14.6097, "lng": 120.9894, "name": "University of Santo Tomas, Manila, Philippines"}
    """
    key = _get_key()
    if not key:
        return None, "No API key found. Add GRAPHHOPPER_KEY to your .env file."

    location = location.strip()
    if location == "":
        return None, "Please type a location."

    params = {"q": location, "limit": 1, "key": key}
    json_data, error = _send_request(GEOCODE_URL, params)
    if error:
        return None, error

    # Like the lab: status 200 with an empty "hits" list means "not found".
    if len(json_data.get("hits", [])) == 0:
        return None, f'Could not find "{location}". Try adding the city, like "Espana, Manila".'

    hit = json_data["hits"][0]
    # Build a readable name from whichever parts exist. This also fixes the
    # lab's state/country quirk by simply skipping empty parts.
    parts = [hit.get("name", ""), hit.get("city", ""), hit.get("state", ""), hit.get("country", "")]
    unique_parts = []
    for part in parts:
        if part and part not in unique_parts:
            unique_parts.append(part)

    place = {
        "lat": hit["point"]["lat"],
        "lng": hit["point"]["lng"],
        "name": ", ".join(unique_parts) or location,
    }
    return place, None


def get_route(start, end, vehicle="car", with_points=False):
    """Get a route between two places.

    Args:
        start, end: dicts with "lat" and "lng" (for example, from geocode()).
        vehicle: "car", "bike", or "foot". Anything else falls back to "car",
            the same rule the lab uses.
        with_points: True to also get the route's coordinates for drawing it
            on the map. Uses points_encoded=false so they come back as plain
            numbers instead of an encoded string.

    Returns:
        (route, error) where route is a dict:
        {
            "distance_m": 1234.5,          # meters
            "time_ms": 456789,             # milliseconds
            "instructions": [              # turn-by-turn steps
                {"text": "Turn left onto Espana Boulevard", "distance_m": 120.0,
                 "time_ms": 30000, "sign": -2},
                ...
            ],
            "points": [[lat, lng], ...],   # only filled when with_points=True
        }
    """
    key = _get_key()
    if not key:
        return None, "No API key found. Add GRAPHHOPPER_KEY to your .env file."

    if vehicle not in VEHICLES:
        vehicle = "car"

    params = {
        "key": key,
        "vehicle": vehicle,
        # A list makes requests send point=... twice, once per place,
        # just like the lab's op and dp strings.
        "point": [f"{start['lat']},{start['lng']}", f"{end['lat']},{end['lng']}"],
    }
    if with_points:
        params["points_encoded"] = "false"

    json_data, error = _send_request(ROUTE_URL, params)
    if error:
        return None, error

    if len(json_data.get("paths", [])) == 0:
        return None, "GraphHopper could not find a route between these places."

    path = json_data["paths"][0]
    instructions = []
    for step in path.get("instructions", []):
        instructions.append({
            "text": step["text"],
            "distance_m": step["distance"],
            "time_ms": step["time"],
            # The kind of turn, e.g. -2 left, 0 straight, 2 right, 4 arrive.
            # display.py turns it into an arrow.
            "sign": step.get("sign", 0),
        })

    points = []
    if with_points:
        # GraphHopper sends [lng, lat] (GeoJSON order). Folium wants [lat, lng],
        # so we swap them here once, and the map code does not have to.
        for lng, lat, *_ in path["points"]["coordinates"]:
            points.append([lat, lng])

    route = {
        "distance_m": path["distance"],
        "time_ms": path["time"],
        "instructions": instructions,
        "points": points,
    }
    return route, None


if __name__ == "__main__":
    # Quick self-test. Uses 2 credits: 1 geocode + 1 route.
    # Run with: python graphhopper_api.py
    print("Testing geocode()...")
    ust, error = geocode("University of Santo Tomas, Manila")
    if error:
        print("Error:", error)
    else:
        print(f"  Found: {ust['name']} at {ust['lat']}, {ust['lng']}")

        # A spot a few hundred meters from UST, so the walk is short.
        nearby = {"lat": 14.6045, "lng": 120.9880}
        print("Testing get_route() on foot, with map points...")
        route, error = get_route(ust, nearby, "foot", with_points=True)
        if error:
            print("Error:", error)
        else:
            print(f"  Distance: {route['distance_m'] / 1000:.2f} km")
            print(f"  Time: {route['time_ms'] / 1000 / 60:.1f} minutes")
            print(f"  Steps: {len(route['instructions'])}, map points: {len(route['points'])}")
            for step in route["instructions"][:3]:
                print(f"    {step['text']} ({step['distance_m']:.0f} m)")

    print("Testing error handling (no credits used)...")
    print("  Blank input:", geocode("   ")[1])
