"""
Personal café ratings and favorites for Kape Tayo (ratings.json).

Each café is saved under its unique OpenStreetMap id (like "node/123456"),
so two branches with the same name, such as two Starbucks, never mix up.
We also save the name, address, and location, so "My rated cafés" can be
shown without calling any API.

ratings.json looks like this:
{
  "node/123456": {
    "name": "Starbucks", "address": "Dapitan St, Manila",
    "lat": 14.61, "lng": 120.99,
    "rating": 4, "favorite": true, "rated_on": "2026-10-03"
  }
}

The ratings dict also plugs straight into kape_score.rank_cafes(), which
reads "rating" and "favorite" for each café id.
"""
import json
from datetime import date
from pathlib import Path

# Saved next to this file, so it works no matter which folder you run from.
RATINGS_FILE = Path(__file__).parent / "ratings.json"

MIN_RATING = 1
MAX_RATING = 5


def _is_valid_entry(entry):
    """Check that one saved rating has everything we need, with sane values."""
    return (isinstance(entry, dict)
            and isinstance(entry.get("name"), str)
            and isinstance(entry.get("lat"), (int, float))
            and isinstance(entry.get("lng"), (int, float))
            and isinstance(entry.get("favorite"), bool)
            # A café can be a favorite without a rating, so None is allowed.
            and (entry.get("rating") is None
                 or (isinstance(entry.get("rating"), int)
                     and MIN_RATING <= entry["rating"] <= MAX_RATING)))


def load_ratings():
    """Read ratings.json and return a dict of valid ratings, keyed by café id.

    A missing or broken file gives an empty dict. A single bad entry is
    skipped, so one mistake does not erase all the other ratings.
    """
    try:
        saved = json.loads(RATINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(saved, dict):
        return {}

    ratings = {}
    for cafe_id, entry in saved.items():
        if _is_valid_entry(entry):
            entry.setdefault("address", "")
            entry.setdefault("rated_on", "")
            ratings[cafe_id] = entry
    return ratings


def save_ratings(ratings):
    """Write all ratings to ratings.json. Returns an error message or None."""
    try:
        RATINGS_FILE.write_text(json.dumps(ratings, indent=2, ensure_ascii=False),
                                encoding="utf-8")
    except OSError:
        return "Could not save your ratings to ratings.json."
    return None


def rate_cafe(ratings, cafe, rating, favorite):
    """Add or update one café's rating and favorite mark, then save.

    Args:
        ratings: the dict from load_ratings() (changed in place).
        cafe: a café dict with "id", "name", "lat", "lng" (and "address").
        rating: 1 to 5, or None for no rating.
        favorite: True or False.

    Returns:
        An error message, or None if it saved.
    """
    ratings[cafe["id"]] = {
        "name": cafe["name"],
        "address": cafe.get("address", ""),
        "lat": cafe["lat"],
        "lng": cafe["lng"],
        "rating": rating,
        "favorite": favorite,
        "rated_on": date.today().isoformat(),  # e.g. "2026-10-03"
    }
    return save_ratings(ratings)


def remove_rating(ratings, cafe_id):
    """Delete one café from your ratings, then save.

    Returns an error message, or None if it saved.
    """
    ratings.pop(cafe_id, None)
    return save_ratings(ratings)


def sorted_ratings(ratings):
    """Return a list of (cafe_id, entry), favorites first, then best rated.

    Unrated favorites go after rated ones; ties are sorted by name.
    """
    return sorted(
        ratings.items(),
        key=lambda item: (not item[1]["favorite"],
                          -(item[1]["rating"] or 0),
                          item[1]["name"].lower()),
    )
