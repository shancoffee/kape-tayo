"""
Everything Kape Tayo shows on screen, using the rich library.

Keeping all printing in this one file means the other modules (API calls,
café search, scoring) only deal with data. If someone later builds a GUI,
this is the main file they would replace.
"""
from contextlib import contextmanager

from rich import box
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# Colors for each Kape Score label (see kape_score.score_label).
LABEL_COLORS = {
    "Highly recommended": "bold green",
    "Good pick": "cyan",
    "Okay": "yellow",
    "Maybe skip": "red",
}

# Same conversion the lab uses: 1 mile = 1.61 km.
KM_PER_MILE = 1.61


def format_distance(meters, units="km"):
    """Turn meters into a short string like "1.2 km" or "0.7 mi"."""
    km = meters / 1000
    if units == "miles":
        return f"{km / KM_PER_MILE:.1f} mi"
    return f"{km:.1f} km"


def format_duration(time_ms):
    """Turn milliseconds into a short string like "8 min" or "1 h 05 min"."""
    total_minutes = round(time_ms / 1000 / 60)
    if total_minutes < 1:
        return "<1 min"
    if total_minutes < 60:
        return f"{total_minutes} min"
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours} h {minutes:02d} min"


def _format_wifi(wifi):
    """Show True / False / None (unknown) from cafe_search as Yes / No / ?."""
    if wifi is True:
        return "[green]Yes[/green]"
    if wifi is False:
        return "[red]No[/red]"
    return "[dim]?[/dim]"


def show_ranked_table(cafes, units="km", vehicle="car"):
    """Print the ranked café table.

    Args:
        cafes: list from kape_score.rank_cafes(), already sorted best first.
        units: "km" or "miles" for the distance column.
        vehicle: travel mode, shown in the table title.
    """
    # SIMPLE_HEAD draws only a line under the header (no side borders),
    # which saves space so the table fits an 80-character terminal.
    table = Table(title=f"Kape Tayo picks (by {vehicle})", header_style="bold magenta",
                  box=box.SIMPLE_HEAD)
    # no_wrap keeps short columns on one line. Only the Café column wraps,
    # because names and addresses are the longest text.
    table.add_column("#", justify="right", no_wrap=True)
    table.add_column("Café / Address", ratio=1)
    table.add_column("Time", justify="right", no_wrap=True)
    table.add_column("Distance", justify="right", no_wrap=True)
    table.add_column("Score", justify="right", no_wrap=True)
    table.add_column("Verdict", no_wrap=True)
    table.add_column("WiFi", justify="center", no_wrap=True)

    for rank, cafe in enumerate(cafes, start=1):
        color = LABEL_COLORS[cafe["label"]]
        # Bold name, with a star for favorites, and the address in grey below.
        name = f"[bold]{cafe['name']}[/bold]"
        if cafe.get("favorite"):
            name += " [yellow]*[/yellow]"
        if cafe["address"]:
            name += f"\n[dim]{cafe['address']}[/dim]"
        table.add_row(
            str(rank),
            name,
            format_duration(cafe["time_ms"]),
            format_distance(cafe["distance_m"], units),
            f"[{color}]{cafe['score']}[/{color}]",
            f"[{color}]{cafe['label']}[/{color}]",
            _format_wifi(cafe["wifi"]),
        )
    console.print(table)


def show_error(message):
    """Print an error message in red."""
    console.print(f"[bold red]Error:[/bold red] {message}")


@contextmanager
def progress_bar(description, total):
    """Show a progress bar while slow work runs.

    Use it like this:
        with progress_bar("Getting travel times", 10) as step:
            for ...:
                do_work()
                step()   # moves the bar forward by one
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
        transient=True,  # The bar disappears when finished, keeping the screen tidy.
    ) as progress:
        task = progress.add_task(description, total=total)
        yield lambda: progress.advance(task)


if __name__ == "__main__":
    # Preview the table with made-up cafés. Uses 0 credits.
    # Run with: python display.py
    from kape_score import rank_cafes

    sample = [
        {"id": "node/1", "name": "Starbucks Dapitan", "address": "Dapitan St, Manila",
         "wifi": True, "time_ms": 4 * 60000, "distance_m": 320},
        {"id": "node/2", "name": "Cafe Khivan", "address": "",
         "wifi": None, "time_ms": 6 * 60000, "distance_m": 480},
        {"id": "node/3", "name": "ZUS Coffee", "address": "Espana Blvd, Manila",
         "wifi": None, "time_ms": 9 * 60000, "distance_m": 710},
        {"id": "node/4", "name": "Boulangerie 22", "address": "",
         "wifi": False, "time_ms": 25 * 60000, "distance_m": 2100},
    ]
    # Pretend ratings so every color shows up in the preview.
    # Expected scores: node/1 = 100, node/2 = 65, node/3 = 42, node/4 = 16.
    sample_ratings = {
        "node/1": {"rating": 5, "favorite": True},
        "node/2": {"rating": 4, "favorite": False},
        "node/4": {"rating": 1, "favorite": False},
    }
    ranked = rank_cafes(sample, sample_ratings)
    show_ranked_table(ranked, units="km", vehicle="foot")
    console.print("Same table in miles:")
    show_ranked_table(ranked, units="miles", vehicle="foot")
    show_error("This is what an error message looks like.")
