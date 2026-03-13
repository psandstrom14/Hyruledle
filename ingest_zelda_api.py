import requests
import json
import time
import re

API_BASE = "https://zelda.fanapis.com/api"
HEADERS = {'User-Agent': 'Hyruledle-Project/1.0'}
TARGET_ROSTER_SIZE = 100
MAX_PAGES_TO_CHECK = 50


def fetch_all_games():
    """Step 1: Fetch all games and build a lookup dict keyed by game ID."""
    print("🎮 Step 1: Fetching all games...")
    resp = requests.get(f"{API_BASE}/games", params={'limit': 50}, headers=HEADERS, timeout=10)

    if resp.status_code != 200:
        print(f"   ❌ HTTP {resp.status_code} fetching games. Aborting.")
        return {}

    games_raw = resp.json().get('data', [])
    games_lookup = {}

    for game in games_raw:
        game_id = game.get('id')
        name = game.get('name', 'Unknown')
        released = game.get('released_date', '').strip()

        # Extract the year from the release date string (e.g. "March 3, 2017" -> 2017)
        year_match = re.search(r'\b(\d{4})\b', released)
        release_year = int(year_match.group(1)) if year_match else None

        games_lookup[game_id] = {
            "name": name,
            "release_year": release_year,
        }

    print(f"   ✅ Loaded {len(games_lookup)} games.")

    # Save games.json for the pipeline
    with open('games.json', 'w') as f:
        json.dump(games_raw, f, indent=4)
    print("   💾 Saved: games.json")

    return games_lookup


def resolve_appearances(appearances, games_lookup):
    """Map appearance URLs to game info using the pre-fetched lookup."""
    resolved = []
    for url in appearances:
        # Extract game ID from URL: .../api/games/5f6ce9d805615a85623ec2c5
        game_id = url.rsplit('/', 1)[-1]
        game_info = games_lookup.get(game_id)
        if game_info:
            resolved.append(game_info)
    # Sort by release year so first_appearance is the earliest game
    resolved.sort(key=lambda g: g["release_year"] or 9999)
    return resolved


def is_legend(name):
    """Gate 1: Check if the character is in the manual legends list (exact word match)."""
    legends = [
        "midna", "linebeck", "fi", "ghirahim", "zant",
        "groose", "sidon", "tulin", "rauru", "mineru", "tingle",
    ]
    # Split name into lowercase words and check for exact matches
    name_words = set(re.findall(r'[a-z]+', name.lower()))
    return bool(name_words & set(legends))


def fetch_characters(games_lookup):
    """Step 2: Fetch all characters, apply Three Gates filtering."""
    print(f"\n⚔️  Step 2: Fetching characters...")
    print(f"   Target: {TARGET_ROSTER_SIZE} characters.")
    print("---------------------------------------------------------------")

    final_roster = []
    current_page = 0
    seen_names = set()

    while current_page < MAX_PAGES_TO_CHECK and len(final_roster) < TARGET_ROSTER_SIZE:
        print(f"\n📄 [PAGE {current_page}] Requesting batch...", end=" ")

        try:
            params = {'limit': 20, 'page': current_page}
            response = requests.get(
                f"{API_BASE}/characters", params=params, headers=HEADERS, timeout=10
            )

            if response.status_code != 200:
                print(f"\n⚠️  HTTP {response.status_code} on page {current_page}. Stopping.")
                break

            data = response.json()
        except Exception as e:
            print(f"\n❌ Error on page {current_page}: {e}")
            break

        batch = data.get('data', [])
        if not batch:
            print("\n🏁 No more data found.")
            break

        print(f"Checking {len(batch)} candidates.")

        for summary_char in batch:
            name = summary_char.get('name', "Unknown")
            char_id = summary_char.get('id')

            if name in seen_names:
                continue

            # --- DEEP FETCH ---
            try:
                time.sleep(0.1)  # Be polite: delay between individual character fetches
                deep_resp = requests.get(
                    f"{API_BASE}/characters/{char_id}", headers=HEADERS, timeout=5
                )

                if deep_resp.status_code != 200:
                    print(f"   ⚠️  HTTP {deep_resp.status_code} for {name}, skipping.")
                    continue

                deep_data = deep_resp.json().get('data', {})

                appearances = deep_data.get('appearances', [])
                resolved_games = resolve_appearances(appearances, games_lookup)
                game_count = len(resolved_games)
                description = deep_data.get('description', "")

                # --- THE THREE GATES FILTERING ---

                # Gate 1: The Legends (Manual Overrides for Single-Game Icons)
                legend = is_legend(name)

                # Gate 2: The Recurring (Quantity — appears in 2+ games)
                recurring = game_count >= 2

                # Gate 3: The Narrative (Quality — long description = major character)
                major_role = len(description) > 250

                # Final Decision: pass at least one gate, and have some description
                if (legend or recurring or major_role) and len(description) > 10:

                    first_game = resolved_games[0] if resolved_games else None

                    clean_char = {
                        "name": name,
                        "race": deep_data.get('race', 'Unknown'),
                        "gender": deep_data.get('gender', 'Unknown'),
                        "first_appearance": first_game["name"] if first_game else "Unknown",
                        "first_appearance_year": first_game["release_year"] if first_game else None,
                        "game_count": game_count,
                        "description": description[:250] + "..." if len(description) > 250 else description,
                    }

                    final_roster.append(clean_char)
                    seen_names.add(name)

                    gate = "LEGEND" if legend else ("RECURRING" if recurring else "NARRATIVE")
                    print(f"   ✅ ADDED: {name} [{gate}] — {game_count} game(s)")

            except Exception as e:
                print(f"   ❌ Error fetching {name}: {e}")
                continue

            if len(final_roster) >= TARGET_ROSTER_SIZE:
                break

        current_page += 1
        time.sleep(0.1)  # Be polite: delay between pages

    return final_roster


def run_pipeline():
    print("=" * 63)
    print("  HYRULEDLE DATA PIPELINE")
    print("=" * 63)

    # Step 1: Fetch games
    games_lookup = fetch_all_games()
    if not games_lookup:
        print("❌ Cannot proceed without games data.")
        return

    # Step 2: Fetch and filter characters
    final_roster = fetch_characters(games_lookup)

    # Step 3: Save results
    print("---------------------------------------------------------------")
    print(f"✅ Pipeline complete: {len(final_roster)} characters saved.")

    with open('zelda_data_deep.json', 'w') as f:
        json.dump(final_roster, f, indent=4)
    print("💾 Saved: zelda_data_deep.json")


if __name__ == "__main__":
    run_pipeline()
