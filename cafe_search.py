"""
Coffee place search for Kape Tayo, using the OpenStreetMap Overpass API.

It finds three kinds of places, so small businesses are included too:
  - "Café":          amenity=cafe (most cafés, big and small)
  - "Coffee shop":   shop=coffee (coffee stalls, roasters, bean sellers)
  - "Serves coffee": any place whose cuisine includes coffee, such as a
                     donut shop or diner tagged cuisine=coffee_shop

We do NOT search by name (like "Kape" or "Cafe" in the name), because that
also finds gaming cafés, internet cafés, and brewery offices.

Overpass is free and needs no API key, so searching costs no GraphHopper
credits. Routing to each café does cost credits, which is why find_cafes()
only returns the closest few cafés (see the limit argument).

Like graphhopper_api.py, the function here never prints or asks for input.
It returns (result, error): error is None on success, otherwise result is
None and error is a short message that is safe to show the user.
"""
import math
import time

import requests

# Main Overpass server first, then a backup if the main one keeps failing.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Overpass asks apps to identify themselves.
HEADERS = {"User-Agent": "KapeTayo-StudentProject"}

# Seconds to wait for each Overpass request before giving up on it.
TIMEOUT = 25

# How many times to try the main server before using the backup,
# and how many seconds to pause between tries.
MAIN_ATTEMPTS = 3
RETRY_PAUSE = 2

# Largest search radius we allow, to keep searches fast and polite.
MAX_RADIUS_M = 5000

# OpenStreetMap "internet_access" values that mean the café has WiFi.
WIFI_YES_VALUES = ["yes", "wlan", "wifi", "free", "customers"]


def distance_m(lat1, lng1, lat2, lng2):
    """Return the straight-line distance in meters between two points.

    Uses the haversine formula, which accounts for the Earth being round.
    This is "as the crow flies", not the road distance. We use it only to
    pick the nearest cafés before asking GraphHopper for real routes.
    """
    earth_radius_m = 6371000
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2)
    return earth_radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _build_query(lat, lng, radius_m):
    """Build the Overpass query that finds coffee places within radius_m of a point.

    Places in OpenStreetMap can be a single pin (node) or a building outline
    (way). "nwr" means node, way, or relation, so each line finds them all.
    The ( ... ); brackets join the three searches into one list, and a
    place that matches more than one line is only listed once.
    ~"coffee",i means "contains coffee", ignoring upper and lower case.
    "out center tags" gives the middle point of buildings plus all their
    tags (name, wifi, opening hours, and so on).
    """
    around = f"(around:{radius_m},{lat},{lng})"
    return (
        "[out:json];"
        "("
        f'nwr["amenity"="cafe"]{around};'
        f'nwr["shop"="coffee"]{around};'
        f'nwr["cuisine"~"coffee",i]{around};'
        ");"
        "out center tags;"
    )


def _place_type(tags):
    """Label what kind of coffee place this is, for the table and map."""
    if tags.get("amenity") == "cafe":
        return "Café"
    if tags.get("shop") == "coffee":
        return "Coffee shop"
    return "Serves coffee"   # Matched only because its cuisine includes coffee.


def _ask_overpass(query):
    """Send the query to Overpass, retrying and using the backup if needed.

    The public Overpass server often answers 504 ("too busy") at random, so
    we try the main server a few times before moving on to the backup.

    Returns (elements, error). elements is the list of raw OpenStreetMap
    results.
    """
    # Main server up to MAIN_ATTEMPTS times, then the backup once.
    attempts = [OVERPASS_URLS[0]] * MAIN_ATTEMPTS + [OVERPASS_URLS[1]]
    for attempt_number, url in enumerate(attempts):
        if attempt_number > 0:
            time.sleep(RETRY_PAUSE)  # Give a busy server a moment to recover.
        try:
            reply = requests.post(url, data={"data": query}, headers=HEADERS, timeout=TIMEOUT)
            # Busy servers answer 429 or 504 with an HTML page, not JSON.
            if reply.status_code == 200:
                return reply.json().get("elements", []), None
        except requests.exceptions.ConnectionError:
            # No internet affects every server, so stop right away.
            return None, "Cannot reach the café search service. Check your internet connection."
        except (requests.exceptions.RequestException, ValueError):
            # Timeout, other network trouble, or a reply that is not JSON.
            pass
        # This attempt failed, so the loop tries again.
    return None, "The café search service is busy right now. Please try again in a minute."


def _make_address(tags):
    """Build a short address like "1234 Dapitan St, Manila" from OSM tags."""
    street = " ".join(part for part in [tags.get("addr:housenumber", ""),
                                        tags.get("addr:street", "")] if part)
    parts = [part for part in [street, tags.get("addr:city", "")] if part]
    return ", ".join(parts)


def _read_wifi(tags):
    """Return True if the café has WiFi, False if it has none, None if unknown."""
    value = tags.get("internet_access", "").lower()
    if value in WIFI_YES_VALUES:
        return True
    if value == "no":
        return False
    return None


def find_cafes(lat, lng, radius_m, limit=10):
    """Find the cafés closest to a point.

    Args:
        lat, lng: the user's location (for example, from geocode()).
        radius_m: how far to search, in meters (1 to MAX_RADIUS_M).
        limit: the most cafés to return. Each one will need 1 GraphHopper
            routing credit later, so keep this small.

    Returns:
        (cafes, error) where cafes is a list sorted nearest first. Each café:
        {
            "id": "node/123456",          # unique OpenStreetMap id
            "name": "Starbucks Dapitan",
            "type": "Café",               # "Café", "Coffee shop", or "Serves coffee"
            "lat": 14.61, "lng": 120.99,
            "straight_m": 230.5,          # straight-line distance in meters
            "wifi": True,                 # True, False, or None (unknown)
            "opening_hours": "Mo-Su 07:00-22:00",   # "" if not listed
            "address": "Dapitan St, Manila",        # "" if not listed
        }
    """
    if not isinstance(radius_m, int) or radius_m < 1 or radius_m > MAX_RADIUS_M:
        return None, f"Search radius must be a whole number from 1 to {MAX_RADIUS_M} meters."

    elements, error = _ask_overpass(_build_query(lat, lng, radius_m))
    if error:
        return None, error

    cafes = []
    for element in elements:
        # Nodes have lat/lon directly. Ways (buildings) have them in "center".
        if "lat" in element:
            cafe_lat, cafe_lng = element["lat"], element["lon"]
        elif "center" in element:
            cafe_lat, cafe_lng = element["center"]["lat"], element["center"]["lon"]
        else:
            continue  # No location given, so we cannot route to it.

        tags = element.get("tags", {})
        cafes.append({
            "id": f"{element['type']}/{element['id']}",
            "name": tags.get("name", "Unnamed café"),
            "type": _place_type(tags),
            "lat": cafe_lat,
            "lng": cafe_lng,
            "straight_m": distance_m(lat, lng, cafe_lat, cafe_lng),
            "wifi": _read_wifi(tags),
            "opening_hours": tags.get("opening_hours", ""),
            "address": _make_address(tags),
        })

    if len(cafes) == 0:
        return None, f"No coffee places found within {radius_m} m. Try a bigger radius."

    cafes.sort(key=lambda cafe: cafe["straight_m"])
    return cafes[:limit], None


if __name__ == "__main__":
    # Quick self-test around UST. Uses 0 GraphHopper credits.
    # Run with: python cafe_search.py
    ust_lat, ust_lng = 14.6097, 120.9894
    print("Searching for cafés within 500 m of UST...")
    cafes, error = find_cafes(ust_lat, ust_lng, 500)
    if error:
        print("Error:", error)
    else:
        print(f"Found {len(cafes)} (closest first):")
        for cafe in cafes:
            wifi = {True: "WiFi", False: "no WiFi", None: "WiFi unknown"}[cafe["wifi"]]
            print(f"  {cafe['name']:<30} {cafe['type']:<14} {cafe['straight_m']:>5.0f} m   {wifi}")

    print("Testing error handling...")
    print("  Bad radius:", find_cafes(ust_lat, ust_lng, 0)[1])
