"""
Kape Tayo GUI: the same app as kape_tayo.py, as a web page made with Streamlit.

Run it with:   streamlit run kape_tayo_gui.py
It opens in your browser at http://localhost:8501. Press Ctrl+C in the
terminal to stop it.

This file only replaces the screens (kape_tayo.py and display.py). It reuses
every other module unchanged: graphhopper_api, cafe_search, kape_score,
ratings, settings, and map_view. It also shares settings.json and
ratings.json with the terminal app.

How Streamlit works (important for credits):
  Streamlit runs this whole file again, top to bottom, every time you click
  or change anything. So we keep results in st.session_state (memory that
  survives those re-runs), and we only call an API when a button is pressed
  or a café's route is not saved yet. Moving a slider or picking a café from
  the list again never spends credits twice.
"""
import html
import random
import time

import streamlit as st

from cafe_search import find_cafes
from display import TURN_ARROWS, format_distance, format_duration
from graphhopper_api import VEHICLES, geocode, get_route
from kape_score import add_travel_times, rank_cafes
from map_view import build_map
from ratings import MAX_RATING, MIN_RATING, load_ratings, rate_cafe, remove_rating, sorted_ratings
from settings import MAX_RADIUS_M, MIN_RADIUS_M, UNITS, load_settings, save_settings

# Most cafés to route per search (1 credit each), same as the terminal app.
CAFE_LIMIT = 10
# Bahala na only routes the picked café, so it can choose from more.
BAHALA_LIMIT = 30

# Small colored dots for each label, matching the map pin colors.
LABEL_DOTS = {
    "Highly recommended": "🟢",
    "Good pick": "🔵",
    "Okay": "🟠",
    "Maybe skip": "⚪",
}

st.set_page_config(page_title="Kape Tayo", page_icon="☕", layout="wide")

# ---------------------------------------------------------------------------
# Look and feel: coffee browns and purple
# ---------------------------------------------------------------------------
# The basic colors are in .streamlit/config.toml. This CSS adds the extras:
# the gradient banner, the dark sidebar, cards, and rounded boxes.
# Color names: espresso #3B2A20, coffee #6F4E37, latte #C8A27C,
# cream #FBF7F2, purple #7B4FA0, deep purple #5B3A7E, lavender #EDE4F5.
st.markdown("""
<style>
/* Big banner at the top: coffee brown fading into purple. */
.kt-hero {
    background: linear-gradient(120deg, #6F4E37 0%, #8A5A8C 55%, #7B4FA0 100%);
    color: #FFFFFF; padding: 1.4rem 1.8rem; border-radius: 18px;
    margin-bottom: 1.2rem; box-shadow: 0 6px 20px rgba(59, 42, 32, 0.25);
}
.kt-hero h1 { color: #FFFFFF; margin: 0; padding: 0; font-size: 2.3rem; }
.kt-hero p { margin: 0.35rem 0 0; opacity: 0.92; font-size: 1.05rem; }

/* Sidebar: dark espresso fading into deep purple, with cream text. */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #3B2A20 0%, #5B3A7E 100%);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #FBF7F2 !important;
}
/* Keep typed text readable inside the white input box. */
[data-testid="stSidebar"] input { color: #3B2A20 !important; }
/* Sidebar's plain buttons (like Bahala na!): see-through with a cream border,
   so the cream text stays readable on the dark background. */
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondaryFormSubmit"] {
    background: rgba(255, 255, 255, 0.12); border: 1px solid #E7D9CB;
}
[data-testid="stSidebar"] button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    background: rgba(255, 255, 255, 0.22); border-color: #FFFFFF;
}

/* Cards used for the top pick, Bahala na pick, and the start screen. */
.kt-card {
    background: #FFFFFF; border: 1px solid #E7D9CB;
    border-left: 6px solid var(--kt-accent, #7B4FA0);
    border-radius: 14px; padding: 1rem 1.25rem; margin: 0.4rem 0 1rem;
    box-shadow: 0 2px 10px rgba(59, 42, 32, 0.08);
}
.kt-card .kt-title { font-size: 1.3rem; font-weight: 700; color: #3B2A20; }
.kt-card .kt-sub { color: #6F4E37; margin-top: 0.2rem; }
.kt-badge {
    display: inline-block; padding: 0.15rem 0.65rem; border-radius: 999px;
    background: #EDE4F5; color: #5B3A7E; font-weight: 600; font-size: 0.85rem;
    margin: 0.5rem 0.3rem 0 0;
}

/* Stat boxes (metrics) look like little cards. */
[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E7D9CB; border-radius: 14px;
    padding: 0.7rem 1rem; box-shadow: 0 2px 8px rgba(59, 42, 32, 0.06);
}
[data-testid="stMetricValue"] { color: #5B3A7E; }

/* Main buttons (normal and inside forms): the banner's brown-to-purple gradient. */
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
    background: linear-gradient(120deg, #6F4E37, #7B4FA0);
    border: none; color: #FFFFFF;
}
button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background: linear-gradient(120deg, #5A3E2B, #6A3F8F); color: #FFFFFF;
}

/* Rounded corners for tables and the map. */
[data-testid="stDataFrame"], iframe { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)


def card(title, subtitle="", badges=(), accent="#7B4FA0"):
    """Show a white card with a colored left edge, a title, and small badges.

    html.escape() keeps café names like "Tom & Jerry's" from breaking the page.
    """
    badge_html = "".join(f'<span class="kt-badge">{html.escape(b)}</span>' for b in badges)
    sub_html = f'<div class="kt-sub">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div class="kt-card" style="--kt-accent: {accent};">'
        f'<div class="kt-title">{html.escape(title)}</div>{sub_html}<div>{badge_html}</div></div>',
        unsafe_allow_html=True,
    )


# Card edge color for each Kape Score label (green, purple, latte, gray).
LABEL_ACCENTS = {
    "Highly recommended": "#2E7D32",
    "Good pick": "#7B4FA0",
    "Okay": "#C8A27C",
    "Maybe skip": "#9E9E9E",
}

# ---------------------------------------------------------------------------
# Memory that survives Streamlit's re-runs
# ---------------------------------------------------------------------------
state = st.session_state
if "settings" not in state:
    state.settings = load_settings()
    state.ratings = load_ratings()
    state.places = {}     # typed text -> geocoded place, so a place is paid for once
    state.routes = {}     # (start, café id, vehicle) -> route, so a route is paid for once
    state.search = None   # the latest "Find cafés" results
    state.bahala = None   # the latest Bahala na café list and pick
settings = state.settings
ratings = state.ratings

# A message saved before st.rerun() is shown here after the page reloads.
if "flash" in state:
    st.toast(state.pop("flash"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_location(text):
    """Turn the sidebar text into a place. Empty text reuses the last location.

    Returns a place dict, or None (after showing an error).
    """
    text = text.strip()
    if not text:
        if settings["last_location"]:
            return settings["last_location"]
        st.error("Type where you are in the sidebar first.")
        return None

    if text in state.places:
        place = state.places[text]   # Already looked up: no credit used.
    else:
        with st.spinner("Finding your location..."):
            place, error = geocode(text)
        if error:
            st.error(error)
            return None
        state.places[text] = place

    settings["last_location"] = place
    error = save_settings(settings)
    if error:
        st.error(error)
    return place


def get_saved_route(start, cafe, vehicle):
    """Get a route with map points, reusing it if we already paid for it."""
    key = (start["lat"], start["lng"], cafe["id"], vehicle)
    if key not in state.routes:
        with st.spinner(f"Getting directions to {cafe['name']}..."):
            route, error = get_route(start, cafe, vehicle, with_points=True)
        if error:
            return None, error
        state.routes[key] = route
    return state.routes[key], None


def delete_rating_confirm(cafe, form_key):
    """Ask "are you sure?" before deleting a rating, so one click cannot erase it."""
    st.warning(f"Delete your rating for **{cafe['name']}**?")
    yes_box, cancel_box = st.columns(2)
    if yes_box.button("Yes, delete", type="primary", key=f"yes_{form_key}_{cafe['id']}",
                      width="stretch"):
        error = remove_rating(ratings, cafe["id"])
        state.pop("confirm_delete", None)
        if error:
            st.error(error)
        else:
            state.flash = f"Deleted your rating for {cafe['name']}."
            state.clear_rated_pick = True   # It is no longer in My rated cafés.
            st.rerun()
    if cancel_box.button("Cancel", key=f"no_{form_key}_{cafe['id']}", width="stretch"):
        state.pop("confirm_delete", None)
        st.rerun()


def rating_form(cafe, form_key):
    """Show the star rating and favorite box for one café, with Save and Delete."""
    saved = ratings.get(cafe["id"])
    options = ["No rating"] + list(range(MIN_RATING, MAX_RATING + 1))
    current = saved["rating"] if saved and saved["rating"] else "No rating"

    # Waiting for "are you sure?" on this café: show that instead of the form.
    if saved and state.get("confirm_delete") == (form_key, cafe["id"]):
        delete_rating_confirm(cafe, form_key)
        return

    # A form waits for the Save button, so moving the slider does not re-run anything.
    with st.form(f"rate_{form_key}_{cafe['id']}"):
        st.markdown("**Rate this café**")
        rating = st.select_slider(
            "Your rating", options=options, value=current,
            format_func=lambda r: r if r == "No rating" else "★" * r,
        )
        favorite = st.checkbox("Favorite", value=saved["favorite"] if saved else False)
        save_box, delete_box = st.columns(2)
        save_clicked = save_box.form_submit_button("💾 Save rating", type="primary",
                                                   width="stretch")
        # Delete only makes sense for a café you already rated.
        delete_clicked = False
        if saved:
            delete_clicked = delete_box.form_submit_button("🗑 Delete rating", width="stretch")
        if delete_clicked:
            state.confirm_delete = (form_key, cafe["id"])
            st.rerun()   # Show the "are you sure?" question.
        if save_clicked:
            rating = None if rating == "No rating" else rating
            if rating is None and not favorite:
                # Nothing to remember, so remove it if it was saved before.
                error = remove_rating(ratings, cafe["id"]) if saved else None
                state.clear_rated_pick = True   # It may have left My rated cafés.
            else:
                error = rate_cafe(ratings, cafe, rating, favorite)
            if error:
                st.error(error)
            else:
                state.flash = f"Saved your rating for {cafe['name']}."
                st.rerun()   # Reload so the Kape Scores use the new rating.


def show_trip(start, cafe, map_cafes, vehicle, radius, units, key):
    """Show directions, the rating form, and the map for one café."""
    route, error = get_saved_route(start, cafe, vehicle)
    if error:
        st.error(error)
        return

    # Bahala na picks have no travel time yet, so fill it in for the map popup.
    cafe.setdefault("time_ms", route["time_ms"])
    cafe.setdefault("distance_m", route["distance_m"])

    st.subheader(f"Directions to {cafe['name']}")
    st.caption(f"From {start['name']} by {vehicle}")

    # Trip summary and rating on the left, the map on the right.
    left, right = st.columns([2, 3])
    with left:
        distance_box, time_box = st.columns(2)
        distance_box.metric("Distance", format_distance(route["distance_m"], units))
        time_box.metric("Time", format_duration(route["time_ms"]))
        rating_form(cafe, key)

    with right:
        cafe_map = build_map(start, map_cafes, chosen=cafe, route_points=route["points"],
                             radius_m=radius, units=units)
        # Show the same map page the terminal app saves, inside a box on this
        # page. This also shows the map legend. Zooming or clicking the map
        # does not re-run the page, so it never spends credits.
        # Safe to embed: map_view.py escapes every café name from OpenStreetMap.
        st.iframe(cafe_map.get_root().render(), height=480)

    # Turn-by-turn steps across the full width, so no column gets cut off.
    steps = []
    for number, step in enumerate(route["instructions"], start=1):
        is_last = step["sign"] == 4   # "Arrive" has no distance or time.
        steps.append({
            "#": number,
            "Turn": TURN_ARROWS.get(step["sign"], "·"),
            "Instruction": step["text"],
            "Distance": "" if is_last else format_distance(step["distance_m"], units),
            "Time": "" if is_last else format_duration(step["time_ms"]),
        })
    st.markdown("**Turn-by-turn directions**")
    st.dataframe(steps, hide_index=True, width="stretch", column_config={
        "#": st.column_config.NumberColumn(width="small"),
        "Turn": st.column_config.TextColumn(width="small"),
    })


def cafe_table_rows(ranked, units):
    """Turn ranked cafés into rows for the results table."""
    rows = []
    for number, cafe in enumerate(ranked, start=1):
        wifi = {True: "Yes", False: "No", None: "?"}[cafe["wifi"]]
        rows.append({
            "#": number,
            "Café": cafe["name"] + (" ⭐" if cafe["favorite"] else ""),
            "Type": cafe.get("type", ""),
            "Address": cafe["address"],
            "Time": format_duration(cafe["time_ms"]),
            "Distance": format_distance(cafe["distance_m"], units),
            "Score": cafe["score"],
            "Verdict": f"{LABEL_DOTS[cafe['label']]} {cafe['label']}",
            "Your rating": "★" * cafe["rating"] if cafe["rating"] else "",
            "WiFi": wifi,
        })
    return rows


# ---------------------------------------------------------------------------
# Sidebar: location and settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("☕ Kape Tayo")

    # A form waits until you press Enter or a button, so typing a place does
    # not re-run anything. Pressing Enter clicks the first button (Search).
    with st.form("location_form", border=False):
        location_text = st.text_input("Where are you?", placeholder="e.g. UST, Manila")
        search_button, bahala_button = st.columns(2)
        search_clicked = search_button.form_submit_button(
            "🔎 Search", type="primary", width="stretch")
        bahala_clicked = bahala_button.form_submit_button("🎲 Bahala na!", width="stretch")
    if settings["last_location"]:
        st.caption(f"Leave empty to use your last location: **{settings['last_location']['name']}**")

    st.divider()
    st.subheader("Settings")
    units = st.radio("Units", UNITS, index=UNITS.index(settings["units"]), horizontal=True)
    radius = st.slider("Search radius (meters)", MIN_RADIUS_M, MAX_RADIUS_M,
                       settings["radius_m"], step=100)
    vehicle = st.radio("Travel mode", VEHICLES, index=VEHICLES.index(settings["vehicle"]),
                       horizontal=True)

    # Save to settings.json only when something actually changed.
    changed = {"units": units, "radius_m": radius, "vehicle": vehicle}
    if any(settings[name] != value for name, value in changed.items()):
        settings.update(changed)
        error = save_settings(settings)
        if error:
            st.error(error)


st.markdown(
    '<div class="kt-hero"><h1>☕ Kape Tayo</h1>'
    "<p>Find the nearest café, get the best pick, and go.</p></div>",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Actions from the sidebar buttons (they run before the tabs are drawn)
# ---------------------------------------------------------------------------

def run_search(location_text):
    """Search cafés near the typed place and rank them. Uses about 12 credits."""
    start = resolve_location(location_text)
    if not start:
        return
    with st.spinner(f"Searching for coffee places within {radius} m..."):
        cafes, error = find_cafes(start["lat"], start["lng"], radius, limit=CAFE_LIMIT)
    if error:
        st.error(error)
        return

    bar = st.progress(0.0, text=f"Getting {vehicle} travel times...")
    done = [0]   # A list, so the step() function below can change it.

    def step():
        """Move the progress bar after each café (used by add_travel_times)."""
        done[0] += 1
        bar.progress(done[0] / len(cafes),
                     text=f"Getting {vehicle} travel times... {done[0]}/{len(cafes)}")

    routed, skipped = add_travel_times(start, cafes, vehicle, on_progress=step)
    bar.empty()
    if routed:
        state.search = {"start": start, "cafes": routed, "skipped": skipped,
                        "vehicle": vehicle, "radius": radius}
    else:
        st.error("Could not get a route to any café. Try another travel mode.")


def roll_bahala(start=None):
    """Pick a random café. With a new start place or radius, search first.

    Searching costs 0 credits; only the picked café's route uses a credit.
    """
    bahala = state.bahala
    if start and (bahala is None or bahala["start"] != start or bahala["radius"] != radius):
        with st.spinner(f"Searching for coffee places within {radius} m..."):
            cafes, error = find_cafes(start["lat"], start["lng"], radius, limit=BAHALA_LIMIT)
        if error:
            st.error(error)
            return
        bahala = {"start": start, "radius": radius, "cafes": cafes,
                  "not_picked": [c["id"] for c in cafes], "pick": None}
    if bahala is None:
        return

    if not bahala["not_picked"]:
        st.info("That was every café nearby! Starting the roll over.")
        # Never repeat the same café twice in a row (unless it is the only one).
        bahala["not_picked"] = ([c["id"] for c in bahala["cafes"] if c["id"] != bahala["pick"]]
                                or [c["id"] for c in bahala["cafes"]])
    bahala["pick"] = random.choice(bahala["not_picked"])
    bahala["not_picked"].remove(bahala["pick"])
    state.bahala = bahala
    with st.spinner("Bahala na..."):
        time.sleep(1)   # A moment of suspense.


TAB_FIND, TAB_BAHALA, TAB_RATED = "🔎 Find cafés", "🎲 Bahala na!", "⭐ My rated cafés"

if search_clicked:
    run_search(location_text)
    state.main_tab = TAB_FIND      # Show the results tab.
elif bahala_clicked:
    start = resolve_location(location_text)
    if start:
        roll_bahala(start)
        state.main_tab = TAB_BAHALA   # Jump to the Bahala na tab.

# key="main_tab" lets the code above choose which tab is open. on_change="rerun"
# makes Streamlit remember the open tab (switching tabs never uses credits).
tab_find, tab_bahala, tab_rated = st.tabs([TAB_FIND, TAB_BAHALA, TAB_RATED],
                                          key="main_tab", on_change="rerun")

# ---------------------------------------------------------------------------
# Tab 1: Find cafés near me
# ---------------------------------------------------------------------------
with tab_find:
    search = state.search
    if search is None:
        # Friendly start screen: three steps, side by side.
        step_1, step_2, step_3 = st.columns(3)
        with step_1:
            card("1. Where are you?", "Type a place in the sidebar, like UST, Manila.",
                 accent="#6F4E37")
        with step_2:
            card("2. Press Enter", "We find coffee places nearby and rank them with the Kape Score.",
                 accent="#8A5A8C")
        with step_3:
            card("3. Pick and go", "Get directions, see the map, and rate your café.",
                 accent="#7B4FA0")
    else:
        if search["vehicle"] != vehicle or search["radius"] != radius:
            st.warning("Your travel mode or radius changed. Press **🔎 Search** to update.")
        if search["skipped"]:
            st.caption(f"{search['skipped']} café(s) skipped because no route was found.")

        # Re-ranking uses no credits, so new ratings show up right away.
        ranked = rank_cafes(search["cafes"], ratings)

        # Quick stats, then a highlight card for the best café.
        top = ranked[0]
        stat_1, stat_2, stat_3 = st.columns(3)
        stat_1.metric("Cafés found", len(ranked))
        stat_2.metric("Fastest trip", format_duration(min(c["time_ms"] for c in ranked)))
        stat_3.metric("Best Kape Score", top["score"])

        top_badges = [top["label"], top.get("type", "Café"), format_duration(top["time_ms"]),
                      format_distance(top["distance_m"], units)]
        if top["rating"]:
            top_badges.append("★" * top["rating"])
        if top["favorite"]:
            top_badges.append("Favorite")
        card(f"🏆 Top pick: {top['name']}", top["address"], top_badges,
             accent=LABEL_ACCENTS[top["label"]])

        st.subheader(f"All picks near {search['start']['name']} (by {search['vehicle']})")
        st.dataframe(
            cafe_table_rows(ranked, units), hide_index=True, width="stretch",
            column_config={"Score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%d")},
        )

        # Pick by café id (not by row number), because rows can move when
        # a new rating changes the order.
        by_id = {cafe["id"]: cafe for cafe in ranked}
        picked_id = st.selectbox(
            "Pick a café for directions and the map",
            list(by_id), index=None, placeholder="Choose a café", key="find_pick",
            format_func=lambda cafe_id: f"{by_id[cafe_id]['name']} "
                                        f"(Kape Score {by_id[cafe_id]['score']})",
        )
        if picked_id:
            show_trip(search["start"], by_id[picked_id], ranked, search["vehicle"],
                      search["radius"], units, key="find")

# ---------------------------------------------------------------------------
# Tab 2: Bahala na! (random pick)
# ---------------------------------------------------------------------------
with tab_bahala:
    if state.bahala is None:
        card("Can't decide?", "Type where you are in the sidebar, then press 🎲 Bahala na! "
             "and let fate pick a coffee place near you.", accent="#7B4FA0")
    # Roll again from the same list of places (no new search).
    elif st.button("🎲 Roll again", type="primary"):
        roll_bahala()

    bahala = state.bahala
    if bahala and bahala["pick"]:
        cafe = next(c for c in bahala["cafes"] if c["id"] == bahala["pick"])
        wifi = {True: "WiFi: Yes", False: "WiFi: No", None: "WiFi: ?"}[cafe["wifi"]]
        card(f"🎲 Fate says: {cafe['name']}", cafe["address"],
             [cafe.get("type", "Café"),
              f"About {format_distance(cafe['straight_m'], units)} away", wifi],
             accent="#7B4FA0")
        show_trip(bahala["start"], cafe, bahala["cafes"], vehicle, bahala["radius"],
                  units, key="bahala")

# ---------------------------------------------------------------------------
# Tab 3: My rated cafés (0 credits)
# ---------------------------------------------------------------------------
with tab_rated:
    # After a removal, clear the old choice before the list is drawn again.
    if state.pop("clear_rated_pick", False):
        state.pop("rated_pick", None)

    if not ratings:
        card("No ratings yet", "Search for coffee places, pick one, and rate it. "
             "Your ratings show up here and raise the Kape Score of places you like.",
             accent="#C8A27C")
    else:
        rated = sorted_ratings(ratings)
        st.dataframe(
            [{"Café": entry["name"],
              "Address": entry["address"],
              "Rating": "★" * entry["rating"] + "☆" * (MAX_RATING - entry["rating"])
                        if entry["rating"] else "not rated",
              "Favorite": "⭐" if entry["favorite"] else "",
              "Rated on": entry["rated_on"]}
             for _, entry in rated],
            hide_index=True, width="stretch",
        )

        picked_id = st.selectbox(
            "Pick a café to edit", [cafe_id for cafe_id, _ in rated], index=None,
            placeholder="Choose a café", key="rated_pick",
            format_func=lambda cafe_id: ratings[cafe_id]["name"],
        )
        if picked_id:
            # rate_cafe() needs the café id together with its saved details.
            # The form has Save and Delete buttons.
            rating_form(dict(ratings[picked_id], id=picked_id), "rated")
