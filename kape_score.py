"""
Kape Score: rates each café from 0 to 100 so Kape Tayo can recommend one.

How the score is built:
  - Travel time: up to 50 points. 50 x (fastest café's time / this café's time),
    so the fastest café gets the full 50 and slower ones get less.
  - Rating: up to 40 points. (your rating / 5) x 40. Unrated cafés get 20,
    a neutral middle value, so they are not punished for being new to you.
  - Favorite: +10 points.

Labels: 80+ Highly recommended, 60 to 79 Good pick, 40 to 59 Okay,
below 40 Maybe skip.

Note: an unrated, non-favorite café can reach at most 50 + 20 = 70 points
("Good pick"). To be "Highly recommended", a café needs a good rating or a
favorite mark.

This module does not print anything. display.py handles the screen.
"""
from graphhopper_api import get_route

TRAVEL_POINTS = 50
RATING_POINTS = 40
UNRATED_POINTS = 20
FAVORITE_BONUS = 10


def score_cafe(time_ms, fastest_ms, rating=None, favorite=False):
    """Return the Kape Score (a whole number from 0 to 100) for one café.

    Args:
        time_ms: travel time to this café in milliseconds.
        fastest_ms: travel time to the fastest café in the list.
        rating: your rating from 1 to 5, or None if not rated yet.
        favorite: True if you marked this café as a favorite.
    """
    # max(..., 1) avoids dividing by zero if a café is 0 ms away
    # (for example, when you are already standing at it).
    travel = TRAVEL_POINTS * max(fastest_ms, 1) / max(time_ms, 1)

    if rating is None:
        rating_points = UNRATED_POINTS
    else:
        rating_points = (rating / 5) * RATING_POINTS

    bonus = FAVORITE_BONUS if favorite else 0
    return min(100, round(travel + rating_points + bonus))


def score_label(score):
    """Return the recommendation label for a Kape Score."""
    if score >= 80:
        return "Highly recommended"
    if score >= 60:
        return "Good pick"
    if score >= 40:
        return "Okay"
    return "Maybe skip"


def add_travel_times(start, cafes, vehicle="car", on_progress=None):
    """Ask GraphHopper for the real travel time to each café.

    Uses 1 GraphHopper credit per café.

    Args:
        start: dict with "lat" and "lng" (the user's location).
        cafes: list from cafe_search.find_cafes().
        vehicle: "car", "bike", or "foot".
        on_progress: optional function called after each café, so the
            screen can show a progress bar (see display.progress_bar).

    Returns:
        (routed_cafes, skipped) where routed_cafes is a new list of cafés
        with "time_ms" and "distance_m" added, and skipped is how many cafés
        had no route (they are left out instead of stopping the search).
    """
    routed_cafes = []
    skipped = 0
    for cafe in cafes:
        route, error = get_route(start, cafe, vehicle)
        if error:
            skipped += 1
        else:
            # Copy the café so the original list is not changed.
            routed = dict(cafe)
            routed["time_ms"] = route["time_ms"]
            routed["distance_m"] = route["distance_m"]
            routed_cafes.append(routed)
        if on_progress:
            on_progress()
    return routed_cafes, skipped


def rank_cafes(cafes, ratings=None):
    """Score every café and sort them from best to worst.

    Args:
        cafes: cafés that already have "time_ms" (from add_travel_times()).
        ratings: optional dict of your saved ratings, keyed by café id:
            {"node/123": {"rating": 4, "favorite": True}, ...}
            ratings.py will provide this. Until then, everyone is unrated.

    Returns:
        A new list of cafés with "rating", "favorite", "score", and "label"
        added, best score first. Ties go to the faster café.
    """
    if not cafes:
        return []
    if ratings is None:
        ratings = {}

    fastest_ms = min(cafe["time_ms"] for cafe in cafes)
    ranked = []
    for cafe in cafes:
        saved = ratings.get(cafe["id"], {})
        scored = dict(cafe)
        scored["rating"] = saved.get("rating")
        scored["favorite"] = saved.get("favorite", False)
        scored["score"] = score_cafe(cafe["time_ms"], fastest_ms,
                                     scored["rating"], scored["favorite"])
        scored["label"] = score_label(scored["score"])
        ranked.append(scored)

    # Highest score first. For equal scores, the shorter trip comes first.
    ranked.sort(key=lambda cafe: (-cafe["score"], cafe["time_ms"]))
    return ranked


if __name__ == "__main__":
    # Real end-to-end test around UST, on foot.
    # Uses about 10 GraphHopper credits (1 per café found, up to 10).
    # Run with: python kape_score.py
    from cafe_search import find_cafes
    import display

    ust = {"lat": 14.6097, "lng": 120.9894}
    display.console.print("Searching for cafés within 500 m of UST...")
    cafes, error = find_cafes(ust["lat"], ust["lng"], 500, limit=10)
    if error:
        display.show_error(error)
    else:
        with display.progress_bar("Getting travel times", len(cafes)) as step:
            routed, skipped = add_travel_times(ust, cafes, "foot", on_progress=step)
        if skipped:
            display.console.print(f"[dim]{skipped} café(s) skipped because no route was found.[/dim]")
        if routed:
            display.show_ranked_table(rank_cafes(routed), units="km", vehicle="foot")
        else:
            display.show_error("Could not get a route to any café.")
