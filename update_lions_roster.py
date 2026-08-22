import re
from pathlib import Path
from datetime import date, datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIG
# ============================================================

ROSTER_URL = "https://www.detroitlions.com/team/players-roster/"

DATA_DIR = Path("lions_roster_data")
HEADSHOT_DIR = DATA_DIR / "headshots"

ACTIVE_ROSTER_FILE = DATA_DIR / "active_roster.csv"
DAILY_LOG_FILE = DATA_DIR / "roster_daily_log.csv"
CHANGES_FILE = DATA_DIR / "roster_changes.csv"

DATA_DIR.mkdir(exist_ok=True)
HEADSHOT_DIR.mkdir(exist_ok=True)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}

session = requests.Session()
session.headers.update(HEADERS)

def clean_filename(name):
    """
    Convert player name into a safe filename.
    """
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def get_headshot_url(row):
    """
    Extract the clean 2x roster headshot URL from a roster row.
    """

    source = row.find(
        "source",
        attrs={"media": "(min-width:1024px)"}
    )

    if source is None:
        return None

    srcset = source.get("srcset")

    if not srcset:
        return None

    candidates = [
        item.strip().split()[0]
        for item in srcset.split(",")
        if item.strip()
    ]

    # Explicitly use the 2x image
    for url in candidates:
        if "t_thumb_squared_2x" in url:

            # Remove NFL lazy-loading transformation if present
            url = url.replace("/t_lazy/", "/")

            return url

    return None


def download_headshot(player_name, headshot_url):
    """
    Download a headshot only if it doesn't already exist.
    """

    if not headshot_url:
        return None

    filename = f"{clean_filename(player_name)}.jpg"
    filepath = HEADSHOT_DIR / filename

    # Do not redownload an existing photo
    if filepath.exists():
        return str(filepath)

    response = session.get(
        headshot_url,
        timeout=30
    )

    response.raise_for_status()

    filepath.write_bytes(response.content)

    print(f"Downloaded headshot: {player_name}")

    return str(filepath)

def scrape_current_roster():

    response = session.get(
        ROSTER_URL,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    players = []

    for row in soup.select("table tbody tr"):

        cells = row.find_all("td")

        if len(cells) < 8:
            continue

        player_link = cells[0].find("a")

        if player_link is None:
            continue

        # Player name is stored in title
        player_name = player_link.get("title")

        if not player_name:
            continue

        profile_url = urljoin(
            ROSTER_URL,
            player_link.get("href")
        )

        headshot_url = get_headshot_url(row)

        players.append({
            "player": player_name,
            "number": cells[1].get_text(" ", strip=True),
            "position": cells[2].get_text(" ", strip=True),
            "height": cells[3].get_text(" ", strip=True),
            "weight": cells[4].get_text(" ", strip=True),
            "age": cells[5].get_text(" ", strip=True),
            "experience": cells[6].get_text(" ", strip=True),
            "college": cells[7].get_text(" ", strip=True),
            "profile_url": profile_url,
            "headshot_url": headshot_url,
        })

    roster_df = pd.DataFrame(players)

    # Safety against duplicate rows
    roster_df = (
        roster_df
        .drop_duplicates(
            subset="profile_url",
            keep="first"
        )
        .reset_index(drop=True)
    )

    return roster_df

def update_roster():

    run_date = date.today().isoformat()
    run_timestamp = datetime.now().isoformat(timespec="seconds")

    print(f"Updating Lions roster: {run_date}")
    print("-" * 50)

    # --------------------------------------------------------
    # Scrape today's roster
    # --------------------------------------------------------

    current_df = scrape_current_roster()

    print(f"Players on website: {len(current_df)}")


    # --------------------------------------------------------
    # Load previous active roster
    # --------------------------------------------------------

    if ACTIVE_ROSTER_FILE.exists():

        previous_df = pd.read_csv(
            ACTIVE_ROSTER_FILE,
            dtype=str
        ).fillna("")

    else:

        previous_df = pd.DataFrame()


    # --------------------------------------------------------
    # Determine added / removed / unchanged players
    # --------------------------------------------------------

    current_ids = set(
        current_df["profile_url"]
    )

    if not previous_df.empty:

        previous_ids = set(
            previous_df["profile_url"]
        )

    else:

        previous_ids = set()


    added_ids = current_ids - previous_ids
    removed_ids = previous_ids - current_ids
    unchanged_ids = current_ids & previous_ids


    added_df = current_df[
        current_df["profile_url"].isin(added_ids)
    ].copy()


    if not previous_df.empty:

        removed_df = previous_df[
            previous_df["profile_url"].isin(removed_ids)
        ].copy()

    else:

        removed_df = pd.DataFrame()


    print(f"Added:     {len(added_ids)}")
    print(f"Removed:   {len(removed_ids)}")
    print(f"Unchanged: {len(unchanged_ids)}")


    # --------------------------------------------------------
    # Preserve existing local headshot paths
    # --------------------------------------------------------

    current_df["headshot_file"] = ""

    if not previous_df.empty and "headshot_file" in previous_df.columns:

        old_headshots = dict(
            zip(
                previous_df["profile_url"],
                previous_df["headshot_file"]
            )
        )

        for idx, row in current_df.iterrows():

            profile_url = row["profile_url"]

            if profile_url in unchanged_ids:

                current_df.at[
                    idx,
                    "headshot_file"
                ] = old_headshots.get(
                    profile_url,
                    ""
                )


    # --------------------------------------------------------
    # Download headshots for NEW players only
    #
    # Existing players are left untouched unless their
    # file has somehow disappeared.
    # --------------------------------------------------------

    for idx, row in current_df.iterrows():

        profile_url = row["profile_url"]

        existing_file = row["headshot_file"]

        needs_download = False

        # Brand new player
        if profile_url in added_ids:
            needs_download = True

        # Existing player but image is missing locally
        elif not existing_file:
            needs_download = True

        elif not Path(existing_file).exists():
            needs_download = True


        if needs_download:

            try:

                filepath = download_headshot(
                    row["player"],
                    row["headshot_url"]
                )

                current_df.at[
                    idx,
                    "headshot_file"
                ] = filepath or ""

            except Exception as e:

                print(
                    f"Headshot error for "
                    f"{row['player']}: {e}"
                )


    # --------------------------------------------------------
    # Save current active roster
    # --------------------------------------------------------

    current_df["last_checked"] = run_timestamp

    current_df.to_csv(
        ACTIVE_ROSTER_FILE,
        index=False
    )


    # --------------------------------------------------------
    # Append DAILY SNAPSHOT
    # --------------------------------------------------------

    daily_df = current_df.copy()

    daily_df.insert(
        0,
        "snapshot_date",
        run_date
    )

    # Prevent duplicate snapshot if script runs twice in one day
    if DAILY_LOG_FILE.exists():

        existing_log = pd.read_csv(
            DAILY_LOG_FILE,
            dtype=str
        ).fillna("")

        # Remove today's snapshot if one already exists
        existing_log = existing_log[
            existing_log["snapshot_date"] != run_date
        ]

        daily_log = pd.concat(
            [
                existing_log,
                daily_df
            ],
            ignore_index=True
        )

    else:

        daily_log = daily_df


    daily_log.to_csv(
        DAILY_LOG_FILE,
        index=False
    )


    # --------------------------------------------------------
    # Record additions / removals
    # --------------------------------------------------------

    changes = []


    for _, row in added_df.iterrows():

        changes.append({
            "timestamp": run_timestamp,
            "date": run_date,
            "change": "ADDED",
            "player": row["player"],
            "number": row["number"],
            "position": row["position"],
            "profile_url": row["profile_url"],
        })


    if not removed_df.empty:

        for _, row in removed_df.iterrows():

            changes.append({
                "timestamp": run_timestamp,
                "date": run_date,
                "change": "REMOVED",
                "player": row["player"],
                "number": row["number"],
                "position": row["position"],
                "profile_url": row["profile_url"],
            })


    if changes:

        changes_df = pd.DataFrame(changes)

        if CHANGES_FILE.exists():

            old_changes = pd.read_csv(
                CHANGES_FILE,
                dtype=str
            ).fillna("")

            changes_df = pd.concat(
                [
                    old_changes,
                    changes_df
                ],
                ignore_index=True
            )


        changes_df.to_csv(
            CHANGES_FILE,
            index=False
        )


    # --------------------------------------------------------
    # Print changes
    # --------------------------------------------------------

    if len(added_df):

        print("\nADDED:")

        for player in added_df["player"]:
            print(f"  + {player}")


    if not removed_df.empty:

        print("\nREMOVED:")

        for player in removed_df["player"]:
            print(f"  - {player}")


    if not added_ids and not removed_ids:

        print("\nNo roster changes.")


    print("\nUpdate complete.")

    return current_df

if __name__ == "__main__":
    roster_df = update_roster()