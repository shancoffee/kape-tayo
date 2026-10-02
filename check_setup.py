"""Quick check that the API key, libraries, and APIs all work."""
import os
import requests
import folium
from dotenv import load_dotenv
from rich.console import Console

console = Console()
load_dotenv()
key = os.getenv("GRAPHHOPPER_KEY")

if not key:
    console.print("[red]No API key found. Check your .env file.[/red]")
else:
    # Test 1: GraphHopper Geocoding
    reply = requests.get(
        "https://graphhopper.com/api/1/geocode",
        params={"q": "University of Santo Tomas, Manila", "limit": 1, "key": key},
        timeout=30,
    )
    data = reply.json()
    if reply.status_code == 200 and data["hits"]:
        point = data["hits"][0]["point"]
        console.print(f"[green]GraphHopper works![/green] Found UST at {point['lat']}, {point['lng']}")

        # Test 2: OpenStreetMap café search near that point
        query = f'[out:json];node["amenity"="cafe"](around:500,{point["lat"]},{point["lng"]});out 5;'
        cafes = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={"User-Agent": "KapeTayo-StudentProject"},
            timeout=60,
        ).json()
        names = [c["tags"].get("name", "Unnamed café") for c in cafes["elements"]]
        console.print(f"[green]Café search works![/green] Found: {', '.join(names) or 'none nearby'}")
    else:
        console.print(f"[red]GraphHopper error {reply.status_code}:[/red] {data.get('message')}")

console.print("[green]All libraries loaded.[/green]")