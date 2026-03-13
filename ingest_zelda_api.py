import requests
import json
import time
import re

API_BASE = "https://zelda.fanapis.com/api"
HEADERS = {'User-Agent': 'Hyruledle-Project/1.0'}
MAX_PAGES = 50


def fetch_all_games():
    """Fetch all games and build a lookup dict keyed by game ID."""
    print("🎮 Step 1: Fetching all games...")
    resp = requests.get(f"{API_BASE}/games", params={'limit': 50}, headers=HEADERS, timeout=10)

    if resp.status_code != 200:
        print(f"   ❌ HTTP {resp.status_code} fetching games. Aborting.")
        return None, []

    games_raw = resp.json().get('data', [])
    games_lookup = {}

    for game in games_raw:
        game_id = game.get('id')
        name = game.get('name', 'Unknown')
        released = game.get('released_date', '').strip()

        year_match = re.search(r'\b(\d{4})\b', released)
        release_year = int(year_match.group(1)) if year_match else None

        games_lookup[game_id] = {
            "name": name,
            "release_year": release_year,
        }

    print(f"   ✅ Loaded {len(games_lookup)} games.")
    return games_lookup, games_raw


def resolve_appearances(appearances, games_lookup):
    """Map appearance URLs to game info using the pre-fetched lookup."""
    resolved = []
    for url in appearances:
        game_id = url.rsplit('/', 1)[-1]
        game_info = games_lookup.get(game_id)
        if game_info:
            resolved.append(game_info)
    resolved.sort(key=lambda g: g["release_year"] or 9999)
    return resolved


def fetch_all_characters(games_lookup):
    """Fetch ALL characters from the API with no filtering or caps."""
    print(f"\n⚔️  Step 2: Fetching all characters (no filtering)...")
    print("---------------------------------------------------------------")

    all_characters = []
    current_page = 0
    seen_names = set()

    while current_page < MAX_PAGES:
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
            print("No more data.")
            break

        print(f"Got {len(batch)} entries.")

        for entry in batch:
            name = entry.get('name', "Unknown")
            char_id = entry.get('id')

            if name in seen_names:
                continue

            try:
                time.sleep(0.1)
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
                first_game = resolved_games[0] if resolved_games else None

                character = {
                    "name": name,
                    "race": deep_data.get('race') or None,
                    "gender": deep_data.get('gender') or None,
                    "first_appearance": first_game["name"] if first_game else None,
                    "first_appearance_year": first_game["release_year"] if first_game else None,
                    "game_count": game_count,
                    "game_names": [g["name"] for g in resolved_games],
                    "description": deep_data.get('description', ""),
                }

                all_characters.append(character)
                seen_names.add(name)
                print(f"   📥 {name} — {game_count} game(s)")

            except Exception as e:
                print(f"   ❌ Error fetching {name}: {e}")
                continue

        current_page += 1
        time.sleep(0.1)

    return all_characters


def run_pipeline():
    print("=" * 63)
    print("  HYRULEDLE RAW DATA INGESTION")
    print("=" * 63)

    # Step 1: Fetch games
    games_lookup, games_raw = fetch_all_games()
    if not games_lookup:
        print("❌ Cannot proceed without games data.")
        return

    with open('data/games.json', 'w') as f:
        json.dump(games_raw, f, indent=4)
    print("   💾 Saved: data/games.json")

    # Step 2: Fetch ALL characters (unfiltered)
    all_characters = fetch_all_characters(games_lookup)

    # Step 3: Save raw output
    print("\n---------------------------------------------------------------")
    print(f"✅ Ingestion complete: {len(all_characters)} total entries fetched.")

    with open('data/characters_raw.json', 'w') as f:
        json.dump(all_characters, f, indent=4)
    print("💾 Saved: data/characters_raw.json")

    # Summary stats
    with_games = sum(1 for c in all_characters if c["game_count"] > 0)
    with_race = sum(1 for c in all_characters if c["race"])
    with_gender = sum(1 for c in all_characters if c["gender"])
    print(f"\n📊 Quick stats:")
    print(f"   Entries with game appearances: {with_games}/{len(all_characters)}")
    print(f"   Entries with race:             {with_race}/{len(all_characters)}")
    print(f"   Entries with gender:           {with_gender}/{len(all_characters)}")


if __name__ == "__main__":
    run_pipeline()
