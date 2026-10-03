"""
Kape Tayo: find the nearest coffee shops, get the best pick, and go.

This is the file you run:  python kape_tayo.py

It connects all the other modules:
  graphhopper_api.py  turns places into coordinates and gets routes
  cafe_search.py      finds cafés near you (OpenStreetMap Overpass)
  kape_score.py       scores and ranks the cafés
  display.py          shows menus, tables, and directions
  map_view.py         opens the interactive map
  settings.py         remembers your settings and last location

Built on Cisco DEVASC Lab 4.9.2 (see original_lab/graphhopper_parse-json_7.py).
"""
import display
from cafe_search import find_cafes
from graphhopper_api import VEHICLES, geocode, get_route
from kape_score import add_travel_times, rank_cafes
from map_view import show_map
from settings import MAX_RADIUS_M, MIN_RADIUS_M, UNITS, load_settings, save_settings

# Most cafés to route per search. Each one costs 1 GraphHopper credit.
CAFE_LIMIT = 10

console = display.console


# ---------------------------------------------------------------------------
# Input helpers: keep asking until the user types something valid.
# ---------------------------------------------------------------------------

def ask_number(prompt, low, high):
    """Ask for a whole number from low to high. Repeats until valid."""
    while True:
        answer = console.input(f"[bold]{prompt}[/bold] ").strip()
        if answer.isdigit() and low <= int(answer) <= high:
            return int(answer)
        display.show_error(f"Please enter a number from {low} to {high}.")


def ask_choice(prompt, choices):
    """Ask the user to type one of the given words (not case-sensitive)."""
    options = "/".join(choices)
    while True:
        answer = console.input(f"[bold]{prompt}[/bold] ({options}): ").strip().lower()
        if answer in choices:
            return answer
        display.show_error(f"Please type one of: {', '.join(choices)}.")


def ask_yes_no(prompt, default=True):
    """Ask a yes/no question. Pressing Enter picks the default."""
    hint = "Y/n" if default else "y/N"
    while True:
        answer = console.input(f"[bold]{prompt}[/bold] ({hint}): ").strip().lower()
        if answer == "":
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        display.show_error("Please type y or n.")


# ---------------------------------------------------------------------------
# Menu option 1: Find cafés near me
# ---------------------------------------------------------------------------

def ask_location(settings):
    """Ask where the user is and geocode it.

    Pressing Enter reuses the last location (no credit used).
    Returns a place dict {"name", "lat", "lng"}, or None to go back.
    """
    last = settings["last_location"]
    while True:
        if last:
            console.print(f"[dim]Press Enter to use your last location: {last['name']}[/dim]")
        answer = console.input("[bold]Where are you?[/bold] (0 to go back): ").strip()

        if answer == "0":
            return None
        if answer == "" and last:
            return last
        if answer == "":
            display.show_error("Please type a place, like \"UST, Manila\" or \"SM North EDSA\".")
            continue

        with console.status("Finding your location..."):
            place, error = geocode(answer)
        if error:
            display.show_error(error)
            continue

        display.show_success(f"Found: {place['name']}")
        # Remember it for next time.
        settings["last_location"] = place
        save_error = save_settings(settings)
        if save_error:
            display.show_error(save_error)
        return place


def show_cafe_details(start, cafe, ranked, settings):
    """Get the route to one café, show directions, and offer the map."""
    with console.status(f"Getting directions to {cafe['name']}..."):
        route, error = get_route(start, cafe, settings["vehicle"], with_points=True)
    if error:
        display.show_error(error)
        return

    display.show_directions(route, start["name"], cafe["name"],
                            settings["units"], settings["vehicle"])

    if ask_yes_no("Open the map in your browser?"):
        path, error = show_map(start, ranked, chosen=cafe, route_points=route["points"],
                               radius_m=settings["radius_m"], units=settings["units"])
        if error:
            display.show_error(error)
        else:
            display.show_success("Map opened in your browser.")
            display.show_info(path)

    # Rating this café comes with ratings.py (next feature).


def find_cafes_near_me(settings):
    """Menu option 1: search, rank, pick a café, get directions and the map."""
    start = ask_location(settings)
    if start is None:
        return

    radius = settings["radius_m"]
    vehicle = settings["vehicle"]
    with console.status(f"Searching for cafés within {radius} m..."):
        cafes, error = find_cafes(start["lat"], start["lng"], radius, limit=CAFE_LIMIT)
    if error:
        display.show_error(error)
        return

    with display.progress_bar(f"Getting {vehicle} travel times", len(cafes)) as step:
        routed, skipped = add_travel_times(start, cafes, vehicle, on_progress=step)
    if skipped:
        display.show_info(f"{skipped} café(s) skipped because no route was found.")
    if not routed:
        display.show_error("Could not get a route to any café. Try another travel mode.")
        return

    ranked = rank_cafes(routed)
    display.show_ranked_table(ranked, settings["units"], vehicle)

    # Let the user look at several cafés from the same list. Only the
    # chosen café's route costs a credit; the list itself is reused.
    while True:
        number = ask_number(f"Pick a café number (1 to {len(ranked)}, 0 to go back):",
                            0, len(ranked))
        if number == 0:
            return
        show_cafe_details(start, ranked[number - 1], ranked, settings)
        if not ask_yes_no("Pick another café from this list?", default=False):
            return
        display.show_ranked_table(ranked, settings["units"], vehicle)


# ---------------------------------------------------------------------------
# Menu option 3: Settings
# ---------------------------------------------------------------------------

def change_settings(settings):
    """Menu option 3: change units, radius, or travel mode. Saved right away."""
    while True:
        display.show_settings(settings)
        choice = ask_number("Choose a setting to change (0 to go back):", 0, 3)
        if choice == 0:
            return
        if choice == 1:
            settings["units"] = ask_choice("Units", UNITS)
        elif choice == 2:
            settings["radius_m"] = ask_number(
                f"Search radius in meters ({MIN_RADIUS_M} to {MAX_RADIUS_M}):",
                MIN_RADIUS_M, MAX_RADIUS_M)
        elif choice == 3:
            settings["vehicle"] = ask_choice("Travel mode", VEHICLES)

        error = save_settings(settings)
        if error:
            display.show_error(error)
        else:
            display.show_success("Settings saved.")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main():
    """Show the main menu until the user quits."""
    display.show_banner()
    settings = load_settings()

    while True:
        display.show_menu()
        choice = ask_number("Choose an option (1 to 5):", 1, 5)
        if choice == 1:
            find_cafes_near_me(settings)
        elif choice == 2:
            display.show_info("My rated cafés is coming in the next update (ratings.py).")
        elif choice == 3:
            change_settings(settings)
        elif choice == 4:
            display.show_info("Bahala na! is coming in a later update.")
        elif choice == 5:
            break

    console.print("[bold #c08552]Salamat! See you next time.[/bold #c08552]")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C (or closing the input) quits politely instead of a traceback.
        console.print("\n[bold #c08552]Salamat! See you next time.[/bold #c08552]")
