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
zelda_characters_final.json       <-- Clean, validated, ready to load (planned)
     |
     v
Django management command          <-- e.g. load_characters (planned; idempotent upsert)
     |
     v
SQLite (local dev) / PostgreSQL (production)   <-- ORM models in game app
     |
     v
Django views + templates           <-- Game logic + server-rendered UI (vertical slice live)
```

---

## Tech Stack

| Layer             | Technology                |
|-------------------|---------------------------|
| Language          | Python 3.12               |
| Web Framework     | Django 6.x                |
| Database          | **SQLite** (local dev, zero config) · **PostgreSQL** (production target) |
| Frontend          | Django Templates (server-rendered) |
| Data Source       | [Zelda Fan API](https://zelda.fanapis.com) ([docs](https://docs.zelda.fanapis.com/docs/)) |

**Not using**: Angular, React, or a separate SPA. UI is Django templates first; **HTMX** (optional later) still fits a server-rendered architecture if you want snappier guesses without React.

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
| race                  | text (nullable) | API often null; ORM allows blank |
| gender                | text (nullable) | API often null; ORM allows blank |
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
- Output: `data/characters_flagged.csv` with `auto_flag`, `flag_reason`, `keep_suggested`, and columns for human review.

### Step 3: Manual Curation (human-in-the-loop) — **complete for v1 roster grading**
- File: `data/characters_flagged.csv` (spreadsheet-friendly).
- Every row has **`keep_suggested`**, final **`keep`** (`yes`/`no`), and **`tier`** (`S` / `A` / `B` / `X`).
- **Tier rubric (summary):** `S` = franchise pillars; `A` = strong side/story; `B` = depth/niche; `X` = exclude from the guessing pool.
- Policy examples: CDI-only games (*Link: The Faces of Evil*, *Zelda: The Wand of Gamelon*) excluded; aggregated **Link** split into separate titled rows (e.g. Hero of Time, Hero of the Wild).
- **Still to do in data:** fill null `race`/`gender` where needed for gameplay, add **`role`** (Hero / Villain / Ally / NPC — not in API), then export **`keep=yes`** to `data/characters_curated.csv` for the load pipeline.

### Step 4: Validate & Merge (automated)
- Python script reads `data/characters_curated.csv` + `data/characters_raw.json`.
- Validates no nulls in required fields, enum values are valid.
- Output: `data/zelda_characters_final.json`.

### Step 5: Load into Database (Django management command) — **not implemented yet**
- **Target input:** `data/zelda_characters_final.json` (produced after Step 4 merge script exists).
- **Command location (Django convention):** `game/management/commands/<name>.py` (e.g. `load_characters.py`), with `management/` and `commands/` packages each containing an `__init__.py`.
- **Behavior:** idempotent upserts (e.g. `update_or_create` on a stable key such as API id or slug—not name alone if collisions exist); create **`Game`** rows and wire **`Character.games`** M2M from resolved appearances.
- **Do not** anchor the loader to legacy `zelda_data_deep.json` unless you explicitly revive that file; canonical pipeline is **raw JSON → CSV curation → final JSON → DB**.
- Local DB file **`db.sqlite3`** is gitignored; run `migrate` after clone.

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

1. **GET `/`** — Django fetches today's target, loads character list for autocomplete, renders template (today: static vertical slice at project root URL).
2. **POST `/guess/`** (planned) — Player submits a character name. Django loads the guess, compares traits against target, stores guess in session, re-renders page with feedback row added.

### Trait Comparison Logic (lives in Python, not templates)

```python
# String feedback for templates: "higher" / "lower" mean the **correct answer** is
# greater or less than the guess (guess is too low → "higher"), matching the current index view.
def compare_traits(guess, target):
    def cmp_int(g, t):
        if g is None or t is None:
            return "miss"  # or handle unknowns explicitly
        if g == t:
            return "match"
        return "higher" if g < t else "lower"

    return {
        "race": "match" if guess.race == target.race else "miss",
        "gender": "match" if guess.gender == target.gender else "miss",
        "role": "match" if guess.role == target.role else "miss",
        "first_appearance": cmp_int(guess.first_appearance_year, target.first_appearance_year),
        "game_count": cmp_int(guess.game_count, target.game_count),
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

## Project structure (current)

```
Hyruledle/
├── README.md
├── manage.py                    # Django entrypoint
├── requirements.txt             # pip freeze (Django, requests, …)
├── ingest_zelda_api.py          # Stage 1: raw API → data/*.json
├── classify_characters.py       # Stage 2: raw → characters_flagged.csv
├── data/
│   ├── games.json               # Raw games (regenerate with ingest)
│   ├── characters_raw.json      # Raw characters (regenerate with ingest)
│   └── characters_flagged.csv   # Graded roster (keep / tier); export curated subset next
├── hyruledle/                   # Django **project** package
│   ├── settings.py              # SQLite default; INSTALLED_APPS includes game
│   ├── urls.py                  # '' → game.views.index
│   └── wsgi.py / asgi.py
├── game/                        # Django **app**
│   ├── models.py                # Game, Character (+ M2M games)
│   ├── views.py                 # Trait board (hardcoded slice until DB wired)
│   ├── admin.py
│   ├── templates/game/index.html
│   └── migrations/
│       └── 0001_initial.py
├── venv/                        # Not committed
└── db.sqlite3                   # Local DB after migrate (gitignored)
```

**Planned additions:** `data/characters_curated.csv`, `data/zelda_characters_final.json`, `game/management/commands/load_characters.py`, `daily_targets` model (or equivalent).

---

## Setup

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (web app + ingestion)
pip install -r requirements.txt

# Stage 1: Fetch raw data from Zelda Fan API
python3 ingest_zelda_api.py

# Stage 2: Run heuristic classifier
python3 classify_characters.py

# Stage 3: Export graded keep=yes rows into curated roster
python3 export_curated.py
# Optional tighter pool by tier:
python3 export_curated.py --tiers S,A

# Django: apply migrations and run dev server
python manage.py migrate
python manage.py runserver
# → http://127.0.0.1:8000/  (trait board)  ·  http://127.0.0.1:8000/admin/  (after createsuperuser)
```

---

## Current Status

**Data (as of last README update)**  
- `data/characters_flagged.csv`: **1009** character rows, all graded — **`keep`** + **`tier`** on every row.
- **285** rows with **`keep=yes`** (candidate guessing-pool entries); **724** excluded (**`keep=no`**, **`tier=X`**). The game design target is still **~50–150** names — narrow this subset by tier and/or manual pass when exporting to `characters_curated.csv`.
- **Tier distribution (all rows):** S 26 · A 73 · B 186 · X 724.

**Done**
- [x] Virtual environment setup
- [x] Raw ingestion (`ingest_zelda_api.py`) — games + characters + appearance resolution → `data/games.json`, `data/characters_raw.json`
- [x] Heuristic classifier (`classify_characters.py`) → `data/characters_flagged.csv`
- [x] Manual curation pass — **`keep`**, **`tier`**, and review of `keep_suggested` complete on the flagged CSV

**Next (implementation order)**
- [ ] Export `data/characters_curated.csv` from **`characters_flagged.csv`** (`keep=yes`, optional **tier** filter toward ~50–150 names)
- [ ] Validation / merge script → **`data/zelda_characters_final.json`** (stable ids, resolved years, **role** filled where required)
- [x] Django project — `manage.py`, **`hyruledle/`** settings/urls, **`game`** app, **SQLite** dev DB
- [x] ORM models — **`Game`**, **`Character`** (nullable **`race`** / **`gender`**), **`Character.games`** M2M; **`game`** registered in admin
- [x] First UI — **`/`** hardcoded Link vs Midna trait board (`game/templates/game/index.html`)
- [ ] **`game/management/commands/load_characters.py`** — read final JSON, upsert **games + characters + M2M** (idempotent)
- [ ] **POST** guess endpoint, session or DB guesses, **daily target** model
- [ ] Search / autocomplete (datalist or server partials); optional **HTMX** after plain form POST works
- [ ] Production: **PostgreSQL**, static files, `DEBUG=False` checklist

**Run locally:** `source venv/bin/activate` → `python manage.py runserver` → [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
