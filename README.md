# Kape Tayo

**Find the nearest coffee shops, get the best pick, and go.**

Kape Tayo is a Python app with two ways to use it: a colorful **terminal app**
and a **web GUI** in your browser. You type where you are, and it finds the
coffee places around you, ranks them with a **Kape Score**, gives you
turn-by-turn directions, and shows an interactive map. You can rate cafés and
mark favorites, and your ratings make future recommendations better.

This project is a feature enhancement of the Cisco DevNet Associate (DEVASC)
**Lab 4.9.2: Integrate a REST API in a Python Application**
(`graphhopper_parse-json_7.py`). The original lab code is kept in
[`original_lab/`](original_lab/) for comparison.

---

## Features

- **Coffee place search by radius:** finds cafés, small coffee shops, and places that serve coffee, from 100 m to 5 km around any place you type
- **Ranking by real travel time:** uses actual road or walking routes, not straight lines
- **Travel modes:** car, bike, or foot
- **Kape Score (0 to 100):** combines travel time, your rating, and favorites into one recommendation
- **Turn-by-turn directions:** numbered steps with arrows, in km or miles
- **Interactive map:** your location, café pins colored by score, and the route line, opened in your browser
- **Colored tables:** clean, readable results using the `rich` library
- **Personal ratings and favorites:** rate cafés from 1 to 5 stars, saved between runs
- **Saved settings:** units, radius, travel mode, and your last location are remembered
- **Bahala na!:** can't decide? Let the app pick a random café for you
- **Input validation and error handling:** bad input, no internet, busy servers, and API errors never crash the app
- **Web GUI (bonus):** the same app as a web page, in coffee browns and purple, with the map built into the page

---

## Lab 4.9.2 vs. Kape Tayo

| | Original Lab 4.9.2 | Kape Tayo |
|---|---|---|
| **Goal** | Directions between two places you type | Find, rank, and get directions to the best café near you |
| **Interface** | Terminal only | Terminal app, plus a web GUI (Streamlit) |
| **Destinations** | You type one destination | Coffee places are found automatically (OpenStreetMap Overpass API) |
| **Routes per search** | 1 | Up to 10 (one per café), then 1 more for the café you pick |
| **Recommendation** | None | Kape Score from travel time, your rating, and favorites |
| **Output** | Plain `print()` lines | Colored tables, arrows, progress bars (`rich`) |
| **Map** | None | Interactive map with pins and route line (`folium`) |
| **Distance** | Miles and km together | Your choice of km or miles; short steps in m or ft |
| **Duration** | `hh:mm:ss` | Friendly text like `8 min` or `1 h 05 min` |
| **Travel mode** | Asked every loop | Saved in Settings |
| **API key** | Typed into the code | Loaded from a `.env` file, never printed |
| **Printed URLs** | Full URL including the key | No URLs or keys are printed |
| **API calls** | Each request sent twice | Each request sent once (saves credits) |
| **Errors handled** | Blank input, wrong key, unknown place, no route | All of those, plus no internet, timeouts, busy servers, used-up credits, and every kind of bad menu input |
| **Memory** | Nothing is saved | Settings, last location, ratings, and favorites are saved |

The lab's logic is reused in Kape Tayo:
- **`geocoding()`** became `geocode()` in `graphhopper_api.py`
- **The routing request** became `get_route()`, and it can also return the route line for the map
- **The instructions loop** became `show_directions()` in `display.py`
- **The meters and milliseconds math** became `format_distance()` and `format_duration()`

---

## Setup

### 1. Requirements

- Python 3 (tested with Python 3.14)
- A free GraphHopper API key
- An internet connection

### 2. Get the code and install the libraries

```bash
git clone https://github.com/shancoffee/kape-tayo.git
cd kape-tayo
pip install -r requirements.txt
```

This installs `requests`, `python-dotenv`, `rich`, `folium`, and `streamlit`
(for the web GUI). Streamlit is the biggest one, so on a slow connection the
install can take a while.

### 3. Add your GraphHopper API key

1. Sign up for free at [graphhopper.com](https://www.graphhopper.com/) and create an API key in the dashboard.
2. In the `kape-tayo` folder, create a file named `.env` with this one line:

   ```
   GRAPHHOPPER_KEY=your_key_here
   ```

   Replace `your_key_here` with your own key.

`.env` is listed in `.gitignore`, so your key is never uploaded to GitHub.
No API key is needed for the café search (OpenStreetMap Overpass).

### 4. Check that everything works

```bash
python check_setup.py
```

You should see green messages saying GraphHopper and the café search work.

---

## How to use

```bash
python kape_tayo.py
```

On Mac or Linux, use `python3` instead of `python`.

### Main menu

| Option | What it does | GraphHopper credits |
|---|---|---|
| **1. Find cafés near me** | Type your location (or press Enter to reuse your last one), see the ranked table, pick a café for directions and the map, then rate it | About 12 per search |
| **2. My rated cafés** | See your ratings and favorites; change a rating, toggle a favorite, or remove a café | 0 |
| **3. Settings** | Units (km or miles), search radius (100 to 5000 m), travel mode (car, bike, foot). Saved automatically | 0 |
| **4. Bahala na!** | A random café near you, with directions and the map. Roll again if you don't like it | About 1 per roll |
| **5. Quit** | Exit. You can also press Ctrl+C at any time | 0 |

### Example session

```
Where are you? (0 to go back): UST, Manila
Found: University of Santo Tomas, Manila, Philippines

                        Kape Tayo picks (by foot)

  #   Café / Address    Time   Distance   Score   Verdict              WiFi
 ─────────────────────────────────────────────────────────────────────────
  1   Starbucks * ★5   3 min      220 m     100   Highly recommended    ?
  2   Cafe Khivan      4 min      260 m      58   Okay                  ?
  3   ZUS Coffee ★3    5 min      310 m      54   Okay                  ?

Pick a café number (1 to 3, 0 to go back): 1

  #       Instruction                              Distance    Time
 ──────────────────────────────────────────────────────────────────
  1   ↑   Continue                                     70 m   1 min
  2   ↑   Continue onto L. Maria Guerrero Drive       130 m   2 min
  3   →   Turn right onto Ruaño Drive                  30 m  <1 min
  4   ●   Arrive at destination

Open the map in your browser? (Y/n):
```

In the table, `*` marks a favorite and `★5` is your rating.

### Web GUI (bonus)

```bash
python -m streamlit run kape_tayo_gui.py
```

It opens in your browser at `http://localhost:8501`. Press **Ctrl+C** in the
terminal to stop it. The first time, Streamlit may ask for an email; just
press Enter to skip.

- **Sidebar:** type where you are, then press **Enter** (or **🔎 Search**) or
  **🎲 Bahala na!**. Units, radius, and travel mode are below.
- **🔎 Find cafés:** stat cards, the top pick, the ranked table with Kape Score
  bars, then pick a café for directions, the map, and a rating.
- **🎲 Bahala na!:** a random pick with directions and the map. Press
  **Roll again** for another one.
- **⭐ My rated cafés:** your ratings; change them or delete them (it asks first).

The GUI and the terminal app share the same `settings.json` and
`ratings.json`, so a café you rate in one shows up in the other. The GUI only
accepts connections from your own computer (see `.streamlit/config.toml`).

---

## Kape Score

Every café gets a score from 0 to 100:

| Part | Points | How it is calculated |
|---|---|---|
| Travel time | up to 50 | 50 × (fastest café's time ÷ this café's time) |
| Your rating | up to 40 | (rating ÷ 5) × 40. Unrated cafés get 20 |
| Favorite | +10 | If you marked the café as a favorite |

| Score | Label |
|---|---|
| 80 to 100 | Highly recommended |
| 60 to 79 | Good pick |
| 40 to 59 | Okay |
| 0 to 39 | Maybe skip |

**Worked example:** the fastest café is 4 minutes away. This café is
6 minutes away, you rated it 4 stars, and it is not a favorite.

- Travel: 50 × (4 ÷ 6) = 33.3
- Rating: (4 ÷ 5) × 40 = 32
- Favorite: 0
- **Kape Score: 65, "Good pick"**

An unrated café can reach at most 50 + 20 = 70, so a café needs a good
rating or a favorite mark to become "Highly recommended".

---

## How it works

1. **Location:** GraphHopper **Geocoding API** turns the place you type into latitude and longitude.
2. **Coffee place search:** OpenStreetMap **Overpass API** finds every place within your radius that is tagged `amenity=cafe` (shown as "Café"), `shop=coffee` ("Coffee shop"), or has a `cuisine` that includes coffee ("Serves coffee", like a donut shop that sells coffee). The 10 closest (in a straight line) are kept.
3. **Travel times:** GraphHopper **Routing API** gets the real travel time to each café.
4. **Ranking:** each café gets a Kape Score and the table is sorted best first.
5. **Directions:** the route to your chosen café is requested with `points_encoded=false`, so the same reply gives both the turn-by-turn steps and the route line for the map.
6. **Map:** `folium` builds a web page with the map. The terminal app opens it in your browser; the GUI shows it inside its own page.
7. **Rating:** your rating and favorite are saved in `ratings.json` and used in future Kape Scores.

### APIs used

| API | Used for | Key needed |
|---|---|---|
| [GraphHopper Geocoding](https://docs.graphhopper.com/) | Place name to coordinates | Yes (free) |
| [GraphHopper Routing](https://docs.graphhopper.com/) | Travel time, distance, directions, route line | Yes (free) |
| [OpenStreetMap Overpass](https://wiki.openstreetmap.org/wiki/Overpass_API) | Finding cafés | No |
| Esri World Street Map | Background map tiles | No |

---

## File structure

```
kape-tayo/
├── kape_tayo.py         Main file you run: menus and the app flow
├── kape_tayo_gui.py     The web GUI version (Streamlit)
├── graphhopper_api.py   GraphHopper Geocoding and Routing (based on the lab code)
├── cafe_search.py       Coffee place search with the Overpass API
├── kape_score.py        Kape Score, travel times, and ranking
├── display.py           Everything shown on screen (tables, directions, menus)
├── map_view.py          Interactive map with folium
├── ratings.py           Saves and loads your ratings and favorites
├── settings.py          Saves and loads your settings and last location
├── check_setup.py       Checks your key, libraries, and APIs
├── requirements.txt     Libraries to install
├── .streamlit/          GUI colors and settings (config.toml)
├── original_lab/        Lab 4.9.2 PDF and the final lab code
├── .env                 Your API key (you create it; never uploaded)
├── ratings.json         Your ratings (created automatically; never uploaded)
├── settings.json        Your settings (created automatically; never uploaded)
└── kape_tayo_map.html   The latest map (created automatically; never uploaded)
```

**Design note for other teams:** only `display.py` and `kape_tayo.py` print
or ask for input. The other modules only return data, as a pair
`(result, error)`. This keeps each part easy to test, and it is why the GUI
was possible as one new file: `kape_tayo_gui.py` replaces only the screens and
reuses every other module (`map_view.py` got one small split, `build_map()`,
so the GUI can show the map inside its page).
`graphhopper_api.py`, `cafe_search.py`, `kape_score.py`, `display.py`, and
`map_view.py` each have a small self-test you can run directly, for example
`python cafe_search.py`.

---

## Limits and notes

- **GraphHopper free plan: 500 credits per day.** Each geocode or route uses 1 credit. A full search (option 1) uses about 12, so you can do roughly 40 searches a day. Reusing your last location saves 1 credit.
- **Overpass can be busy.** The free public server sometimes answers "too busy" (error 504). The app tries the main server up to 3 times, then a backup server, so a busy moment can make a search take 30 seconds or more.
- **WiFi and opening hours are often missing.** These come from OpenStreetMap volunteers, so many cafés show WiFi as `?` (unknown).
- **Only mapped places appear.** The app shows what OpenStreetMap volunteers have added, so some small coffee sellers may be missing, and some places tagged as cafés are really tea or dessert shops. Unnamed ones show as "Unnamed café". The app does not search by name, because names with "Cafe" also match gaming and internet cafés.
- **GUI memory:** the GUI remembers searches and routes while the page is open, so clicking around never spends credits twice. Refreshing the browser page starts fresh, so the next search uses credits again.
- **Map tiles:** the default OpenStreetMap tiles block maps opened from a local file (you would see "403 Access blocked"), so the map uses Esri World Street Map tiles instead.

---

## Credits

- Based on **Cisco DEVASC Lab 4.9.2: Integrate a REST API in a Python Application**
- Routing and geocoding by [GraphHopper](https://www.graphhopper.com/)
- Café data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, via the Overpass API
- Map tiles by Esri
- Built with [rich](https://github.com/Textualize/rich), [folium](https://python-visualization.github.io/folium/), and [Streamlit](https://streamlit.io/)

Made by **Shancoffee** for DEVASC Project Activity 3, University of Santo Tomas.
