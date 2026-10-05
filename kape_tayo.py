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
  ratings.py          remembers your café ratings and favorites

Built on Cisco DEVASC Lab 4.9.2 (see original_lab/graphhopper_parse-json_7.py).
"""
import random
import time
import webbrowser

import display
from cafe_search import find_cafes
from graphhopper_api import VEHICLES, geocode, get_route
from kape_score import add_travel_times, rank_cafes
from map_view import google_maps_url, show_map
from ratings import MAX_RATING, MIN_RATING, load_ratings, rate_cafe, remove_rating, sorted_ratings
from settings import (MAX_RADIUS_M, MIN_RADIUS_M, UNITS, load_settings, remember_location,
                      save_settings)

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


def ask_rating(current=None):
    """Ask for a 1 to 5 rating. Pressing Enter keeps the current one (or skips)."""
    keep = f"Enter to keep {current}" if current else "Enter to skip"
    while True:
        answer = console.input(
            f"[bold]Rate this café[/bold] ({MIN_RATING} to {MAX_RATING}, {keep}): ").strip()
        if answer == "":
            return current
        if answer.isdigit() and MIN_RATING <= int(answer) <= MAX_RATING:
            return int(answer)
        display.show_error(f"Please enter a number from {MIN_RATING} to {MAX_RATING}, "
                           "or press Enter.")


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

def use_location(settings, place):
    """Remember place as the last and most recent location, and save."""
    remember_location(settings, place)
    save_error = save_settings(settings)
    if save_error:
        display.show_error(save_error)
    return place


def ask_location(settings):
    """Ask where the user is and geocode it.

    The user can type a new place, type the number of a recent place, or
    press Enter for the last location. Reusing a place uses no credit.
    Returns a place dict {"name", "lat", "lng"}, or None to go back.
    """
    last = settings["last_location"]
    recent = settings["recent_locations"]
    while True:
        if recent:
            display.show_recent_locations(recent)
        answer = console.input("[bold]Where are you?[/bold] (0 to go back): ").strip()

        if answer == "0":
            return None
        if answer == "" and last:
            return use_location(settings, last)
        if answer == "":
            display.show_error("Please type a place, like \"UST, Manila\" or \"SM North EDSA\".")
            continue
        # A number picks one of the recent places (no credit used). A plain
        # number is never a real place, so a wrong one is an error, not a search.
        if answer.isdigit():
            if 1 <= int(answer) <= len(recent):
                return use_location(settings, recent[int(answer) - 1])
            if recent:
                display.show_error(f"Pick a recent place from 1 to {len(recent)}, or type a place.")
            else:
                display.show_error("Please type a place name, like \"UST, Manila\".")
            continue

        with console.status("Finding your location..."):
            # Prefer matches near the last location (or Manila), so a short
            # name like "ust" finds UST and not Ustaritz, France.
            place, error = geocode(answer, near=last)
        if error:
            display.show_error(error)
            continue

        display.show_success(f"Found: {place['name']}")
        return use_location(settings, place)


def ask_to_rate(cafe, ratings):
    """Ask the user to rate a café and mark it as a favorite, then save."""
    saved = ratings.get(cafe["id"])
    if saved:
        console.print(f"Your current rating: {display.format_stars(saved['rating'])}"
                      f"{'  [yellow]* favorite[/yellow]' if saved['favorite'] else ''}")
    rating = ask_rating(saved["rating"] if saved else None)
    favorite = ask_yes_no("Mark as favorite?", default=saved["favorite"] if saved else False)

    if rating is None and not favorite:
        # Nothing to remember. If it was saved before (as a favorite only),
        # un-favoriting it removes it from the list.
        if saved:
            error = remove_rating(ratings, cafe["id"])
            if error:
                display.show_error(error)
            else:
                display.show_success("Removed from your ratings.")
        return

    error = rate_cafe(ratings, cafe, rating, favorite)
    if error:
        display.show_error(error)
    else:
        display.show_success("Saved to My rated cafés.")


def show_cafe_details(start, cafe, ranked, settings, ratings):
    """Get the route to one café, show directions, offer the map, then ask for a rating."""
    with console.status(f"Getting directions to {cafe['name']}..."):
        route, error = get_route(start, cafe, settings["vehicle"], with_points=True)
    if error:
        display.show_error(error)
        return

    # Bahala na picks have no travel time yet, so fill it in from this
    # route (no extra credit). The map popup then shows it.
    cafe.setdefault("time_ms", route["time_ms"])
    cafe.setdefault("distance_m", route["distance_m"])

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

    # The same trip in Google Maps, for real navigation (free, no API key).
    if ask_yes_no("Open in Google Maps for navigation?", default=False):
        url = google_maps_url(start, cafe, settings["vehicle"])
        webbrowser.open(url)
        display.show_success("Opened in Google Maps.")
        display.show_info(url)

    ask_to_rate(cafe, ratings)


def find_cafes_near_me(settings, ratings):
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

    # Your saved ratings and favorites are part of the Kape Score.
    ranked = rank_cafes(routed, ratings)
    display.show_ranked_table(ranked, settings["units"], vehicle)

    # Let the user look at several cafés from the same list. Only the
    # chosen café's route costs a credit; the list itself is reused.
    while True:
        number = ask_number(f"Pick a café number (1 to {len(ranked)}, 0 to go back):",
                            0, len(ranked))
        if number == 0:
            return
        show_cafe_details(start, ranked[number - 1], ranked, settings, ratings)
        if not ask_yes_no("Pick another café from this list?", default=False):
            return
        # Re-score with any new rating. This uses no credits, because the
        # travel times are already known.
        ranked = rank_cafes(routed, ratings)
        display.show_ranked_table(ranked, settings["units"], vehicle)


# ---------------------------------------------------------------------------
# Menu option 2: My rated cafés
# ---------------------------------------------------------------------------

def edit_rated_cafe(cafe_id, ratings):
    """Change, favorite, or remove one rated café. Returns when done."""
    while cafe_id in ratings:
        entry = ratings[cafe_id]
        display.show_rating_options(entry)
        choice = ask_number("Choose an option (0 to go back):", 0, 3)
        # rate_cafe() needs the café id together with its saved details.
        cafe = dict(entry, id=cafe_id)

        if choice == 0:
            return
        if choice == 1:
            new_rating = ask_number(f"New rating ({MIN_RATING} to {MAX_RATING}):",
                                    MIN_RATING, MAX_RATING)
            error = rate_cafe(ratings, cafe, new_rating, entry["favorite"])
        elif choice == 2:
            if entry["favorite"] and entry["rating"] is None:
                # A favorite with no rating has nothing left once un-favorited.
                error = remove_rating(ratings, cafe_id)
            else:
                error = rate_cafe(ratings, cafe, entry["rating"], not entry["favorite"])
        else:
            if not ask_yes_no(f"Remove {entry['name']} from your ratings?", default=False):
                continue
            error = remove_rating(ratings, cafe_id)

        if error:
            display.show_error(error)
        else:
            display.show_success("Saved.")


def my_rated_cafes(ratings):
    """Menu option 2: list your rated cafés and let you edit them. Uses 0 credits."""
    while True:
        if not ratings:
            display.show_info("You have not rated any cafés yet. "
                              "Use option 1 to find one and rate it.")
            return
        rated = sorted_ratings(ratings)
        display.show_rated_table(rated)
        number = ask_number(f"Pick a café to edit (1 to {len(rated)}, 0 to go back):",
                            0, len(rated))
        if number == 0:
            return
        cafe_id = rated[number - 1][0]
        edit_rated_cafe(cafe_id, ratings)


# ---------------------------------------------------------------------------
# Menu option 4: Bahala na! (random pick)
# ---------------------------------------------------------------------------

def roll_for_cafe(cafes):
    """Pick a random café with a short "spinning" animation for suspense."""
    with console.status("Bahala na...") as status:
        for _ in range(12):
            # Flash random names, like a slot machine, before the real pick.
            status.update(f"Bahala na... {random.choice(cafes)['name']}")
            time.sleep(0.12)
    return random.choice(cafes)


def bahala_na(settings, ratings):
    """Menu option 4: let fate pick a café nearby.

    Skips the ranking step, so it only routes to the café that was picked.
    That costs about 1 or 2 credits instead of about 12 for option 1.
    """
    start = ask_location(settings)
    if start is None:
        return

    radius = settings["radius_m"]
    with console.status(f"Searching for cafés within {radius} m..."):
        # A bigger limit gives fate more choices. Searching costs 0 credits.
        cafes, error = find_cafes(start["lat"], start["lng"], radius, limit=30)
    if error:
        display.show_error(error)
        return

    not_picked_yet = list(cafes)
    while True:
        cafe = roll_for_cafe(not_picked_yet)
        not_picked_yet.remove(cafe)
        display.show_bahala_pick(cafe, settings["units"])
        show_cafe_details(start, cafe, cafes, settings, ratings)

        if not ask_yes_no("Not feeling it? Roll again?", default=False):
            return
        if not not_picked_yet:
            display.show_info("That was every café nearby! Starting the roll over.")
            # Start over, but never show the same café twice in a row
            # (unless it is the only café nearby).
            not_picked_yet = [c for c in cafes if c is not cafe] or list(cafes)


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
    ratings = load_ratings()

    while True:
        display.show_menu()
        choice = ask_number("Choose an option (1 to 5):", 1, 5)
        if choice == 1:
            find_cafes_near_me(settings, ratings)
        elif choice == 2:
            my_rated_cafes(ratings)
        elif choice == 3:
            change_settings(settings)
        elif choice == 4:
            bahala_na(settings, ratings)
        elif choice == 5:
            break

    console.print("[bold #c08552]Salamat! See you next time.[/bold #c08552]")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C (or closing the input) quits politely instead of a traceback.
        console.print("\n[bold #c08552]Salamat! See you next time.[/bold #c08552]")
