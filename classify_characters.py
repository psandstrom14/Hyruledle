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
    """Run all heuristics and return (auto_flag, reasons, keep_suggestion) tuple."""
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
    reasons = "; ".join(flags)

    # --- High-level keep suggestion ---------------------------------------
    #
    # We want to approximate "is this a specific, named narrative character"
    # using objective signals, so you aren't relying on personal memory.
    #
    # Heuristics (ordered from strongest to weakest):
    #
    # - Strong keep:
    #   - Has at least 1 game appearance
    #   - Has a reasonably long description
    #   - Name looks like a proper name
    #   - Not obviously a generic role, enemy, or item
    #
    # - Strong cut:
    #   - No games at all
    #   - Or clearly an item/enemy/generic role
    #
    # - Review:
    #   - Everything in between (borderline / ambiguous)

    desc_len = len(description or "")
    generic_role = matches_patterns(name, GENERIC_ROLE_PATTERNS)
    enemy_like = has_enemy_signal(description)
    item_like = has_item_signal(description)
    proper = is_proper_name(name)

    keep_suggestion = "review"

    # Strong keep
    if (
        game_count >= 1
        and desc_len >= 120
        and proper
        and not generic_role
        and not enemy_like
        and not item_like
    ):
        keep_suggestion = "yes"

    # Strong cut
    if (
        game_count == 0
        or generic_role
        or enemy_like
        or item_like
        or (not proper and desc_len < 200)
    ):
        keep_suggestion = "no"

    return auto_flag, reasons, keep_suggestion


def run():
    print("🔍 Stage 2: Heuristic Classification")
    print("=" * 63)

    with open('data/characters_raw.json') as f:
        characters = json.load(f)

    print(f"   Loaded {len(characters)} entries from characters_raw.json")

    rows = []
    flagged_count = 0

    for char in characters:
        auto_flag, reasons, keep_suggestion = classify(char)
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
            "keep_suggested": keep_suggestion,
            "keep": keep_suggestion,  # Pre-filled for you; override as needed
        })

    # Sort: suggested keeps first, then review, then cuts; within that, by game_count
    sort_key_order = {"yes": 0, "review": 1, "no": 2}
    rows.sort(
        key=lambda r: (
            sort_key_order.get(r["keep_suggested"], 1),
            -r["game_count"],
            r["name"],
        )
    )

    fieldnames = [
        "name", "race", "gender", "first_appearance", "first_appearance_year",
        "game_count", "game_names", "description_preview",
        "auto_flag", "flag_reason", "keep_suggested", "keep",
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
