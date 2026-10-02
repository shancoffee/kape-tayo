"""
Lab 4.9.2: Integrate a REST API in a Python Application (final version).

This is the graphhopper_parse-json_7.py script from the Cisco DEVASC lab.
It asks for a vehicle profile, a starting location, and a destination, then:
  1. Uses the GraphHopper Geocoding API to turn each place name into lat/lng
  2. Uses the GraphHopper Routing API to get a route between the two points
  3. Prints the distance, trip duration, and turn-by-turn directions

Changes from the PDF version (each one is marked with "CHANGE" below):
  - The API key is loaded from the .env file instead of being hardcoded
  - Printed URLs show key=HIDDEN so the API key never appears on screen
  - Each API request is sent once instead of twice, to save API credits

Run it with:  python graphhopper_parse-json_7.py
Type q or quit at any prompt to exit.
"""
import os
import sys
import urllib.parse

import requests
from dotenv import load_dotenv

# CHANGE: load the key from .env (GRAPHHOPPER_KEY) instead of hardcoding it.
load_dotenv()
key = os.getenv("GRAPHHOPPER_KEY")
if not key:
    print("No API key found. Add GRAPHHOPPER_KEY to your .env file.")
    sys.exit(1)

route_url = "https://graphhopper.com/api/1/route?"


def hide_key(url):
    """Return the URL with the API key replaced by HIDDEN, safe to print.

    CHANGE: the lab prints full URLs, which would show the API key.
    """
    return url.replace(key, "HIDDEN")


def geocoding(location, key):
    """Look up a place name with the GraphHopper Geocoding API.

    Returns a tuple: (status_code, latitude, longitude, readable_name).
    If the lookup fails, latitude and longitude are the string "null".
    """
    # Keep asking until the user types something (blank input is not allowed).
    while location == "":
        location = input("Enter the location again: ")
    geocode_url = "https://graphhopper.com/api/1/geocode?"
    # urlencode turns spaces and commas into URL-safe characters (+ and %2C).
    url = geocode_url + urllib.parse.urlencode({"q": location, "limit": "1", "key": key})

    replydata = requests.get(url)
    json_data = replydata.json()
    json_status = replydata.status_code

    # Success means status 200 AND at least one result in "hits".
    # An unknown place like "slkdjf" returns 200 with an empty hits list.
    if json_status == 200 and len(json_data["hits"]) != 0:
        # CHANGE: the lab calls requests.get(url) a second time here.
        # We reuse json_data from above so only one credit is used.
        lat = json_data["hits"][0]["point"]["lat"]
        lng = json_data["hits"][0]["point"]["lng"]
        name = json_data["hits"][0]["name"]
        value = json_data["hits"][0]["osm_value"]

        # Not every place has a country or state (e.g. Beijing has no state).
        if "country" in json_data["hits"][0]:
            country = json_data["hits"][0]["country"]
        else:
            country = ""

        if "state" in json_data["hits"][0]:
            state = json_data["hits"][0]["state"]
        else:
            state = ""

        # Build a readable name like "Baltimore, Maryland, United States".
        if len(state) != 0 and len(country) != 0:
            new_loc = name + ", " + state + ", " + country
        elif len(state) != 0:
            # Note: kept exactly as in the lab PDF. This branch runs when there
            # is a state but no country, yet it adds the (empty) country.
            new_loc = name + ", " + country
        else:
            new_loc = name

        print("Geocoding API URL for " + new_loc + " (Location Type: " + value + ")\n"
              + hide_key(url))
    else:
        lat = "null"
        lng = "null"
        new_loc = location
        # Only API errors (like a wrong key, status 401) include a "message".
        if json_status != 200:
            print("Geocode API status: " + str(json_status) + "\nError message: "
                  + json_data["message"])
    return json_status, lat, lng, new_loc


while True:
    # Ask for the mode of travel. Anything not in the list falls back to car.
    print("\n+++++++++++++++++++++++++++++++++++++++++++++")
    print("Vehicle profiles available on Graphhopper:")
    print("+++++++++++++++++++++++++++++++++++++++++++++")
    print("car, bike, foot")
    print("+++++++++++++++++++++++++++++++++++++++++++++")
    profile = ["car", "bike", "foot"]
    vehicle = input("Enter a vehicle profile from the list above: ")
    if vehicle == "quit" or vehicle == "q":
        break
    elif vehicle in profile:
        vehicle = vehicle
    else:
        vehicle = "car"
        print("No valid vehicle profile was entered. Using the car profile.")

    loc1 = input("Starting Location: ")
    if loc1 == "quit" or loc1 == "q":
        break
    orig = geocoding(loc1, key)

    loc2 = input("Destination: ")
    if loc2 == "quit" or loc2 == "q":
        break
    dest = geocoding(loc2, key)

    print("=================================================")
    # orig and dest are tuples: [0] status, [1] lat, [2] lng, [3] name.
    if orig[0] == 200 and dest[0] == 200:
        # Each point is "lat,lng" with the comma encoded as %2C.
        op = "&point=" + str(orig[1]) + "%2C" + str(orig[2])
        dp = "&point=" + str(dest[1]) + "%2C" + str(dest[2])
        paths_url = route_url + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + op + dp
        # CHANGE: the lab sends this request twice (once for the status,
        # once for the JSON). One request gives us both.
        paths_reply = requests.get(paths_url)
        paths_status = paths_reply.status_code
        paths_data = paths_reply.json()
        print("Routing API Status: " + str(paths_status) + "\nRouting API URL:\n"
              + hide_key(paths_url))

        print("=================================================")
        print("Directions from " + orig[3] + " to " + dest[3] + " by " + vehicle)
        print("=================================================")
        if paths_status == 200:
            # GraphHopper gives distance in meters and time in milliseconds.
            miles = (paths_data["paths"][0]["distance"]) / 1000 / 1.61
            km = (paths_data["paths"][0]["distance"]) / 1000
            sec = int(paths_data["paths"][0]["time"] / 1000 % 60)
            min = int(paths_data["paths"][0]["time"] / 1000 / 60 % 60)
            hr = int(paths_data["paths"][0]["time"] / 1000 / 60 / 60)
            print("Distance Traveled: {0:.1f} miles / {1:.1f} km".format(miles, km))
            print("Trip Duration: {0:02d}:{1:02d}:{2:02d}".format(hr, min, sec))
            print("=================================================")
            # Print each turn-by-turn instruction with its distance.
            for each in range(len(paths_data["paths"][0]["instructions"])):
                path = paths_data["paths"][0]["instructions"][each]["text"]
                distance = paths_data["paths"][0]["instructions"][each]["distance"]
                print("{0} ( {1:.1f} km / {2:.1f} miles )".format(path, distance / 1000,
                                                                  distance / 1000 / 1.61))
            print("=================================================")
        else:
            # For example, status 400 when no road route exists (Beijing to Washington).
            print("Error message: " + paths_data["message"])
            print("*************************************************")
