import requests
import json
import time

def run_pipeline():
    # 1. CONFIGURATION
    base_url = "https://zelda.fanapis.com/api/characters"
    final_roster = []
    TARGET_ROSTER_SIZE = 100 # Higher target to get a rich dataset
    MAX_PAGES_TO_CHECK = 50 
    
    headers = {'User-Agent': 'Hyruledle-Project/1.0'}
    
    print(f"⚔️  Starting Narrative-Weight Scan...")
    print(f"Target: {TARGET_ROSTER_SIZE} characters.")
    print("---------------------------------------------------------------")

    current_page = 0 
    seen_names = set()

    while current_page < MAX_PAGES_TO_CHECK and len(final_roster) < TARGET_ROSTER_SIZE:
        print(f"\n📄 [PAGE {current_page}] Requesting batch...", end=" ")
        
        try:
            params = {'limit': 20, 'page': current_page}
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
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

            # Skip exact duplicates we've already saved
            if name in seen_names:
                continue
            
            # --- DEEP FETCH ---
            try:
                deep_url = f"{base_url}/{char_id}"
                deep_resp = requests.get(deep_url, headers=headers, timeout=5)
                deep_data = deep_resp.json().get('data', {})
                
                games_list = deep_data.get('games', [])
                game_count = len(games_list)
                description = deep_data.get('description', "")

                # --- THE THREE GATES FILTERING ---
                
                # Gate 1: The Legends (Manual Overrides for Single-Game Icons)
                legends = ["midna", "linebeck", "fi", "ghirahim", "zant", "groose", "sidon", "tulin", "rauru", "mineru", "tingle"]
                is_legend = any(l in name.lower() for l in legends)

                # Gate 2: The Recurring (Quantity)
                is_recurring = game_count >= 2

                # Gate 3: The Narrative (Quality)
                # If description > 250 chars, they are likely a major plot character
                is_major_role = len(description) > 250

                # Final Decision
                if (is_legend or is_recurring or is_major_role) and len(description) > 10:
                    
                    first_game = games_list[0].get('name') if games_list else "Unknown"
                    
                    clean_char = {
                        "name": name,
                        "race": deep_data.get('race', 'Unknown'),
                        "gender": deep_data.get('gender', 'Unknown'),
                        "first_appearance": first_game,
                        "game_count": game_count,
                        "description": description[:250] + "..." # Keep more for hints
                    }
                    
                    final_roster.append(clean_char)
                    seen_names.add(name)
                    
                    # Log the "Gate" that let them in
                    gate = "LEGEND" if is_legend else ("RECURRING" if is_recurring else "NARRATIVE")
                    print(f"   ✅ ADDED: {name} [{gate}]")
                
                else:
                    # Optional: print(f"   ❌ Skipped: {name}")
                    pass

            except Exception as e:
                continue
            
            if len(final_roster) >= TARGET_ROSTER_SIZE:
                break

        current_page += 1
        time.sleep(0.1) # Be polite

    # 4. SAVE
    print("---------------------------------------------------------------")
    print(f"✅ Pipeline complete: {len(final_roster)} characters saved.")
    
    with open('zelda_data_deep.json', 'w') as f:
        json.dump(final_roster, f, indent=4)
    print("💾 File saved: zelda_data_deep.json")

if __name__ == "__main__":
    run_pipeline()