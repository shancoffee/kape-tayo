"""
Interactive map for Kape Tayo, using the folium library.

folium writes a web page (HTML) with a real, zoomable map (Esri street
tiles, the Leaflet map library). We save that page and open it in the
default browser. The map shows:
  - a purple "You are here" pin
  - one pin per café, colored by Kape Score (click it for details)
  - the chosen café with a coffee-cup icon and the route line to it
  - a faint circle showing the search radius

The map file is kape_tayo_map.html. .gitignore ignores *.html, so it is
never committed.
"""
import html
import urllib.parse
import webbrowser
from pathlib import Path

import folium
# xyzservices comes with folium. It holds a list of free map styles.
import xyzservices.providers as xyz

from display import format_distance, format_duration

MAP_FILE = "kape_tayo_map.html"

# Background map images ("tiles"). We do NOT use folium's default
# OpenStreetMap tiles: their servers block maps opened from a local file
# (file:///...) and show "403 Access blocked" squares instead. CartoDB tiles
# now want an API key. Esri World Street Map is free, needs no key, and
# works from a local file.
MAP_TILES = xyz.Esri.WorldStreetMap

# folium only supports a fixed set of pin colors, so these are the closest
# match to the table colors in display.py.
PIN_COLORS = {
    "Highly recommended": "green",
    "Good pick": "blue",
    "Okay": "orange",
    "Maybe skip": "gray",
}


# Kape Tayo travel modes and the matching Google Maps travel modes.
GOOGLE_TRAVEL_MODES = {"car": "driving", "bike": "bicycling", "foot": "walking"}


def google_maps_url(start, cafe, vehicle="car"):
    """Return a Google Maps link with directions from start to the café.

    This is Google's public "Maps URLs" format: it needs no API key and
    costs nothing. Opening it shows the route in Google Maps, on a laptop
    or phone, so you can navigate there. Your location is only sent to
    Google when you open the link.
    """
    params = {
        "api": 1,
        "origin": f"{start['lat']},{start['lng']}",
        "destination": f"{cafe['lat']},{cafe['lng']}",
        "travelmode": GOOGLE_TRAVEL_MODES.get(vehicle, "driving"),
    }
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(params)


def _popup_html(cafe, units):
    """Build the small info box shown when a café pin is clicked."""
    # html.escape stops names like "Tom & Jerry's" from breaking the page.
    name = html.escape(cafe["name"])
    lines = [f"<b>{name}</b>"]
    if cafe.get("type"):
        lines.append(f"<i>{html.escape(cafe['type'])}</i>")
    if cafe.get("address"):
        lines.append(html.escape(cafe["address"]))
    if "score" in cafe:
        lines.append(f"Kape Score: <b>{cafe['score']}</b> ({cafe['label']})")
    if "time_ms" in cafe:
        lines.append(f"{format_duration(cafe['time_ms'])}, "
                     f"{format_distance(cafe['distance_m'], units)}")
    wifi = {True: "Yes", False: "No", None: "Unknown"}[cafe.get("wifi")]
    lines.append(f"WiFi: {wifi}")
    if cafe.get("opening_hours"):
        lines.append(f"Hours: {html.escape(cafe['opening_hours'])}")
    return "<br>".join(lines)


def _legend_html():
    """A small color key in the corner of the map, matching PIN_COLORS."""
    rows = "".join(
        f'<div><span style="color:{color};font-size:16px;">&#9679;</span> {label}</div>'
        for label, color in PIN_COLORS.items()
    )
    return (
        '<div style="position:fixed;bottom:20px;left:20px;z-index:9999;'
        'background:white;padding:8px 12px;border-radius:6px;'
        'box-shadow:0 1px 4px rgba(0,0,0,0.3);font:13px sans-serif;">'
        f"<b>Kape Score</b>{rows}</div>"
    )


def build_map(start, cafes, chosen=None, route_points=None, radius_m=None, units="km"):
    """Build the map and return it as a folium.Map (without saving it).

    The terminal app uses show_map() below, which saves and opens it.
    The GUI (kape_tayo_gui.py) shows the returned map inside the page.

    Args:
        start: dict with "lat" and "lng" (the user's location).
        cafes: cafés to pin, ideally from kape_score.rank_cafes() so they
            have a score and label. Cafés without a score get a gray pin.
        chosen: the café the user picked (one of cafes), or None.
        route_points: [[lat, lng], ...] from get_route(..., with_points=True).
        radius_m: search radius in meters, drawn as a faint circle.
        units: "km" or "miles" for the popups.
    """
    start_point = [start["lat"], start["lng"]]
    cafe_map = folium.Map(location=start_point, zoom_start=16, tiles=MAP_TILES)

    # Purple for "you" (the search circle and your pin), brown for the route.
    if radius_m:
        folium.Circle(start_point, radius=radius_m, color="#7B4FA0",
                      weight=2, fill=True, fill_opacity=0.06).add_to(cafe_map)

    folium.Marker(
        start_point,
        tooltip="You are here",
        icon=folium.Icon(color="purple", icon="user", prefix="fa"),
    ).add_to(cafe_map)

    for cafe in cafes:
        color = PIN_COLORS.get(cafe.get("label"), "gray")
        is_chosen = chosen is not None and cafe["id"] == chosen["id"]
        # The chosen café gets a coffee cup so it stands out from the rest.
        icon_name = "coffee" if is_chosen else "circle"
        folium.Marker(
            [cafe["lat"], cafe["lng"]],
            # Café names come from OpenStreetMap, which anyone can edit, so
            # escape them before they go into the page.
            tooltip=html.escape(cafe["name"]),
            popup=folium.Popup(_popup_html(cafe, units), max_width=260),
            icon=folium.Icon(color=color, icon=icon_name, prefix="fa"),
        ).add_to(cafe_map)

    if route_points:
        folium.PolyLine(route_points, color="#6f4e37", weight=5, opacity=0.8,
                        tooltip="Your route").add_to(cafe_map)

    # Zoom so that you, every café, and the whole route are visible.
    all_points = [start_point] + [[c["lat"], c["lng"]] for c in cafes] + (route_points or [])
    if len(all_points) > 1:
        cafe_map.fit_bounds(all_points, padding=(30, 30))
        lats = [point[0] for point in all_points]
        lngs = [point[1] for point in all_points]
        bounds = [[min(lats), min(lngs)], [max(lats), max(lngs)]]
        # When the map sits inside another page (the GUI), its box can still
        # be 0 pixels wide when fit_bounds runs, so it zooms out too far.
        # This small JavaScript fits the pins again once the page has loaded,
        # and again if the window is resized.
        cafe_map.get_root().script.add_child(folium.Element(f"""
            function kapeTayoFit() {{
                {cafe_map.get_name()}.invalidateSize();
                {cafe_map.get_name()}.fitBounds({bounds}, {{padding: [30, 30]}});
            }}
            window.addEventListener("load", function () {{ setTimeout(kapeTayoFit, 200); }});
            window.addEventListener("resize", kapeTayoFit);
        """))

    cafe_map.get_root().html.add_child(folium.Element(_legend_html()))
    return cafe_map


def show_map(start, cafes, chosen=None, route_points=None, radius_m=None,
             units="km", file_path=MAP_FILE, open_browser=True):
    """Build the map, save it as an HTML file, and open it in the browser.

    Takes the same arguments as build_map(), plus:
        file_path: where to save the map.
        open_browser: False to only save the file (used for testing).

    Returns:
        (path, error): the full path of the saved map, or an error message.
    """
    cafe_map = build_map(start, cafes, chosen, route_points, radius_m, units)
    try:
        cafe_map.save(file_path)
    except OSError:
        return None, f"Could not save the map file ({file_path})."

    full_path = Path(file_path).resolve()
    if open_browser:
        # as_uri() turns C:\...\kape_tayo_map.html into file:///C:/... for the browser.
        webbrowser.open(full_path.as_uri())
    return str(full_path), None


if __name__ == "__main__":
    # Real end-to-end test around UST, on foot.
    # Uses about 11 GraphHopper credits: up to 10 travel times + 1 route line.
    # Run with: python map_view.py
    import display
    from cafe_search import find_cafes
    from graphhopper_api import get_route
    from kape_score import add_travel_times, rank_cafes

    ust = {"lat": 14.6097, "lng": 120.9894}
    radius = 500
    display.console.print(f"Searching for cafés within {radius} m of UST...")
    cafes, error = find_cafes(ust["lat"], ust["lng"], radius, limit=10)
    if error:
        display.show_error(error)
    else:
        with display.progress_bar("Getting travel times", len(cafes)) as step:
            routed, skipped = add_travel_times(ust, cafes, "foot", on_progress=step)
        ranked = rank_cafes(routed)
        if not ranked:
            display.show_error("Could not get a route to any café.")
        else:
            top = ranked[0]
            display.console.print(f"Getting the route to the top pick, {top['name']}...")
            route, error = get_route(ust, top, "foot", with_points=True)
            if error:
                display.show_error(error)
                route = {"points": []}
            else:
                # The same route has the turn-by-turn steps, so no extra credit.
                display.show_directions(route, "University of Santo Tomas (test location)",
                                        top["name"], units="km", vehicle="foot")
            path, error = show_map(ust, ranked, chosen=top, route_points=route["points"],
                                   radius_m=radius)
            if error:
                display.show_error(error)
            else:
                display.console.print(f"[green]Map opened in your browser:[/green] {path}")
