# Hyruledle

A Legend of Zelda-themed daily guessing game, inspired by [Cosmeredle](https://cosmeredle.net/).

Players guess a mystery Zelda character each day. Each guess reveals trait-based feedback (match / higher / lower) that narrows down the answer.

---

## Project Goals

- Practice **full-stack development** with Django, PostgreSQL, and Django Templates.
- Practice **data engineering**: API ingestion, data joins, null handling, human-in-the-loop curation.
- Build a **resume-worthy personal project** that demonstrates backend design, relational modeling, and a complete vertical slice from raw API data to playable UI.

---

## Architecture Overview

```
Zelda Fan API
     |
     v
Python ingestion scripts          <-- Automated (resume: data engineering)
     |
     v
characters_raw.json + games.json  <-- Raw joined data
     |
     v
Manual curation (CSV)             <-- Human-in-the-loop (domain modeling)
     |
     v
zelda_characters_final.json       <-- Clean, validated, ready to load
     |
     v
Django management command          <-- Loads into Postgres
     |
     v
PostgreSQL                         <-- Authoritative data store
     |
     v
Django views + templates           <-- Game logic + server-rendered UI
```

---

## Tech Stack

| Layer             | Technology                |
|-------------------|---------------------------|
| Language          | Python 3.12               |
| Web Framework     | Django                    |
| Database          | PostgreSQL                |
| Frontend          | Django Templates (server-rendered) |
| Data Source       | [Zelda Fan API](https://zelda.fanapis.com) ([docs](https://docs.zelda.fanapis.com/docs/)) |

**Not using**: Angular, React, or any JS framework. Frontend is Django templates only.

---

## Game Design Decisions

### Mode
- **Characters only** for v1.
- Future modes (items, enemies, bosses, dungeons) can be added later using the same API.

### Target Audience
- **Franchise veterans** who know characters across multiple Zelda titles.
- If a player doesn't recognize a character, they can research based on green/yellow feedback and keep guessing.

### Roster Size
- Target: **~50-150 curated characters**.
- Enough variety to be challenging, not so many that it's frustrating.

### Guess Input
- Searchable, filterable dropdown (type to filter, like Cosmeredle).
- Start with HTML5 `<datalist>` for v1; can enhance with JS later.

---

## Trait Columns (5 Columns)

Each guess shows feedback across these traits:

| Column             | Cell Shows                        | Feedback Type              | On Click/Hover               |
|--------------------|-----------------------------------|----------------------------|------------------------------|
| **Race**           | "Goron"                           | Green (match) / Red (miss) | —                            |
| **Gender**         | "Male"                            | Green / Red                | —                            |
| **First Appearance** | "Ocarina of Time (1998)"        | Green / Higher / Lower (by release year) | —               |
| **Game Count**     | "4"                               | Green / Higher / Lower     | Expands to show full game list |
| **Role**           | "Villain"                         | Green / Red                | —                            |

### Feedback Colors
- **Green**: exact match.
- **Red + arrow** (for higher/lower columns): wrong direction indicated.
- **Yellow** (optional, future): "close" match (e.g., same era for First Appearance).

---

## Data Model (Relational)

### Tables

**games**
| Column       | Type    | Notes                     |
|--------------|---------|---------------------------|
| id           | serial  | PK                        |
| api_id       | text    | Original Zelda API ID     |
| name         | text    | e.g., "Ocarina of Time"   |
| release_year | integer | e.g., 1998                |

**characters**
| Column                | Type    | Notes                              |
|-----------------------|---------|------------------------------------|
| id                    | serial  | PK                                 |
| name                  | text    | e.g., "Midna"                      |
| race                  | text    | e.g., "Twili"                      |
| gender                | text    | e.g., "Female"                     |
| role                  | text    | e.g., "Ally" (manually curated)    |
| first_appearance_year | integer | Denormalized for fast queries      |
| game_count            | integer | Denormalized for fast queries      |

**character_games** (join table)
| Column       | Type    | Notes |
|--------------|---------|-------|
| character_id | FK      |       |
| game_id      | FK      |       |

**daily_targets**
| Column       | Type    | Notes              |
|--------------|---------|--------------------|
| date         | date PK | One target per day |
| character_id | FK      |                    |

### Denormalization Note
`first_appearance_year` and `game_count` are intentionally stored on the characters table (not just derived from joins). This is correct for a read-heavy, rarely-updated game dataset.

---

## Data Pipeline (Current Phase)

### Step 1: Raw Ingest — `ingest_zelda_api.py` (automated)
- Fetches all 32 games from `/api/games`, builds a lookup table `{game_api_id: {name, release_year}}`.
- Paginates through `/api/characters`, deep-fetches each entry, resolves `appearances` URLs against the games lookup.
- **No filtering or caps** — collects everything the API returns.
- Output: `data/games.json`, `data/characters_raw.json`.

### Step 2: Heuristic Classification — `classify_characters.py` (automated)
- Reads `data/characters_raw.json` and runs cheap signal checks on each entry.
- Flags entries that look like generic roles, items, enemies, or concepts — does **not** remove anything.
- Heuristics include: proper noun check, generic role pattern matching, enemy/item keyword detection, missing race/gender.
- Output: `data/characters_flagged.csv` with `auto_flag`, `flag_reason`, and a blank `keep` column for human review.

### Step 3: Manual Curation (human-in-the-loop)
- Open `data/characters_flagged.csv` in a spreadsheet.
- Review flagged entries, fill in the `keep` column (`yes`/`no`).
- **Fill** null `race` and `gender` values.
- **Add** `role` field (Hero / Villain / Ally / NPC — does not exist in API).
- **Select** final ~80-100 roster.
- Output: `data/characters_curated.csv`.

### Step 4: Validate & Merge (automated)
- Python script reads `data/characters_curated.csv` + `data/characters_raw.json`.
- Validates no nulls in required fields, enum values are valid.
- Output: `data/zelda_characters_final.json`.

### Step 5: Load into Database (Django management command)
- Reads `data/zelda_characters_final.json`.
- Upserts games, inserts characters, inserts character_games join rows.
- Computes and stores derived fields.
- Repeatable and idempotent — can wipe and reload anytime.

### Key Principle
> All manual curation happens in files (version-controlled), never directly in the database.
> The database is an immutable, validated data store — not an editing environment.

---

## API Observations (Zelda Fan API)

Endpoint: `https://zelda.fanapis.com/api/characters`

### What the API provides
- `name` — reliable
- `description` — usually present, often detailed
- `gender` — exists but frequently `null`
- `race` — exists but frequently `null`
- `appearances` — list of **game API URLs** (not game names)

### What the API does NOT provide
- `role` (hero/villain/ally) — 100% manual
- `first_appearance_year` — must be derived by resolving game URLs and sorting by release date
- Clean roster — the endpoint mixes real characters with objects ("Ancient Oven"), groups ("Animal Companion"), and bosses

### Available Endpoints (for future modes)
| Endpoint       | Potential Game Mode    |
|----------------|------------------------|
| `/characters`  | Guess the Character    |
| `/monsters`    | Guess the Enemy        |
| `/bosses`      | Guess the Boss         |
| `/items`       | Guess the Item         |
| `/games`       | Guess the Game         |
| `/dungeons`    | Guess the Dungeon      |

---

## Game Loop (Django Templates)

### Request Cycle

1. **GET `/hyruledle/`** — Django fetches today's target, loads character list for autocomplete, renders template with empty guess table.
2. **POST `/hyruledle/guess/`** — Player submits a character name. Django loads the guess, compares traits against target, stores guess in session, re-renders page with feedback row added.

### Trait Comparison Logic (lives in Python, not templates)

```python
def compare_characters(guess, target):
    return {
        "race": guess.race == target.race,
        "gender": guess.gender == target.gender,
        "role": guess.role == target.role,
        "first_appearance": (
            "higher" if guess.first_appearance_year > target.first_appearance_year
            else "lower" if guess.first_appearance_year < target.first_appearance_year
            else "match"
        ),
        "game_count": (
            "higher" if guess.game_count > target.game_count
            else "lower" if guess.game_count < target.game_count
            else "match"
        ),
    }
```

Templates just render the comparison result with colors/arrows.

---

## Open Decisions (TODO)

- [ ] **Race / Gender / Role**: free-text fields or strict enums / lookup tables?
- [ ] **Guess persistence**: session-only (v1) or persistent `guesses` table (for analytics)?
- [ ] **Yellow feedback**: add a "close but not exact" tier for First Appearance (same era)?
- [ ] **Supplemental API**: is the Zelda Fan API rich enough, or supplement with another source?

---

## Project Structure (Planned)

```
Hyruledle/
├── README.md
├── ingest_zelda_api.py          # Stage 1: Raw API ingestion (no filtering)
├── classify_characters.py       # Stage 2: Heuristic auto-classification
├── data/
│   ├── games.json               # Raw games from API
│   ├── characters_raw.json      # Raw characters with resolved games
│   ├── characters_flagged.csv   # Auto-classified, ready for human review
│   ├── characters_curated.csv   # Manual curation file (keep/cut decisions)
│   └── zelda_characters_final.json  # Clean, validated, ready to load
├── hyruledle/                   # Django project (future)
│   ├── manage.py
│   ├── hyruledle/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── ...
│   └── game/                    # Django app
│       ├── models.py
│       ├── views.py
│       ├── templates/
│       └── management/
│           └── commands/
│               └── load_characters.py
├── venv/
└── requirements.txt
```

---

## Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests

# Stage 1: Fetch raw data from Zelda Fan API
python3 ingest_zelda_api.py

# Stage 2: Run heuristic classifier
python3 classify_characters.py

# Stage 3: Open data/characters_flagged.csv and curate manually
```

---

## Current Status

- [x] Virtual environment setup
- [x] Raw ingestion script (`ingest_zelda_api.py`) — games fetch + full character fetch + appearance resolution
- [x] Heuristic classifier (`classify_characters.py`) — auto-flags generic roles, items, enemies, concepts
- [ ] Run full pipeline and generate `characters_flagged.csv`
- [ ] Manual curation pass (spreadsheet review of flagged CSV)
- [ ] Validation/merge script
- [ ] Django project scaffolding
- [ ] Database schema + management command
- [ ] Game views + templates
- [ ] Daily target selection logic
- [ ] UI polish
