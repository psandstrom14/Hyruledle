"""
Stage 2 — Heuristic Classification

Reads data/characters_raw.json and adds auto-classification flags.
Outputs data/characters_flagged.csv for human review.

This does NOT remove anything — it labels entries so the manual
curation pass (Stage 3) is faster and more structured.
"""

import json
import csv
import re

GENERIC_ROLE_PATTERNS = [
    r"^soldier$", r"^guard$", r"^shopkeeper$", r"^receptionist$",
    r"^old (wo)?man$", r"^granny$", r"^maiden$", r"^knight$",
    r"^player$", r"^hero$", r"^fairy$", r"^sage$", r"^champion$",
    r"^postmistress$", r"^smelter$", r"^engineer$",
]

ENEMY_KEYWORDS = [
    "enemy", "enemies", "boss", "mini-boss", "miniboss",
    "monster", "creature", "species", "defeated by",
]

ITEM_KEYWORDS = [
    "item", "weapon", "sword", "shield", "artifact",
    "equipment", "tool", "collectible", "pickup",
    "can be found", "can be obtained", "can be purchased",
]

KNOWN_ZELDA_RACES = {
    "hylian", "human", "zora", "goron", "gerudo", "rito",
    "kokiri", "sheikah", "twili", "minish", "deku", "korok",
    "lokomo", "fairy", "demon", "mogma", "kikwi", "parella",
    "robot", "subrosian", "pirate", "watarara", "oocca",
    "great fairy", "deity",
}


def is_proper_name(name):
    """Heuristic: proper nouns tend to be names, common nouns tend to be generic."""
    words = name.split()
    if len(words) == 1:
        # Single common English words are suspect
        common_nouns = {
            "letter", "sign", "soldier", "skeleton", "eagle", "lion",
            "monkey", "phantom", "player", "fighter", "champion",
            "maiden", "sage", "granny", "keaton", "piratian",
        }
        return words[0].lower() not in common_nouns
    return True


def matches_patterns(name, patterns):
    name_lower = name.lower().strip()
    return any(re.match(p, name_lower) for p in patterns)


def has_enemy_signal(description):
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in ENEMY_KEYWORDS)


def has_item_signal(description):
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in ITEM_KEYWORDS)


def classify(character):
    """Run all heuristics and return (auto_flag, reasons) tuple."""
    name = character["name"]
    race = (character.get("race") or "").lower().strip()
    gender = character.get("gender")
    description = character.get("description", "")
    game_count = character.get("game_count", 0)

    flags = []

    if not is_proper_name(name):
        flags.append("generic_name")

    if matches_patterns(name, GENERIC_ROLE_PATTERNS):
        flags.append("generic_role")

    if game_count == 0:
        flags.append("no_games")

    if not race or race in ("none", "unknown", "null"):
        if game_count >= 3:
            flags.append("no_race_but_recurring")
        else:
            flags.append("no_race")

    if has_enemy_signal(description) and not gender:
        flags.append("likely_enemy")

    if has_item_signal(description) and not race:
        flags.append("likely_item")

    if len(description) < 50:
        flags.append("minimal_description")

    auto_flag = len(flags) > 0
    return auto_flag, "; ".join(flags)


def run():
    print("🔍 Stage 2: Heuristic Classification")
    print("=" * 63)

    with open('data/characters_raw.json') as f:
        characters = json.load(f)

    print(f"   Loaded {len(characters)} entries from characters_raw.json")

    rows = []
    flagged_count = 0

    for char in characters:
        auto_flag, reasons = classify(char)
        if auto_flag:
            flagged_count += 1

        rows.append({
            "name": char["name"],
            "race": char.get("race") or "",
            "gender": char.get("gender") or "",
            "first_appearance": char.get("first_appearance") or "",
            "first_appearance_year": char.get("first_appearance_year") or "",
            "game_count": char.get("game_count", 0),
            "game_names": "; ".join(char.get("game_names", [])),
            "description_preview": (char.get("description", ""))[:150],
            "auto_flag": auto_flag,
            "flag_reason": reasons,
            "keep": "",  # Left blank for human curation
        })

    # Sort: unflagged first (likely good candidates), then flagged
    rows.sort(key=lambda r: (r["auto_flag"], -r["game_count"], r["name"]))

    fieldnames = [
        "name", "race", "gender", "first_appearance", "first_appearance_year",
        "game_count", "game_names", "description_preview",
        "auto_flag", "flag_reason", "keep",
    ]

    with open('data/characters_flagged.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n📊 Classification results:")
    print(f"   Total entries:    {len(rows)}")
    print(f"   Clean (no flags): {len(rows) - flagged_count}")
    print(f"   Flagged:          {flagged_count}")
    print(f"\n💾 Saved: data/characters_flagged.csv")
    print(f"\n👉 Next step: open the CSV, review flagged entries, fill in the 'keep' column.")


if __name__ == "__main__":
    run()
