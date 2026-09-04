"""
Stage 3 - Export curated roster.

Reads data/characters_flagged.csv and writes data/characters_curated.csv.
By default it exports rows where keep=yes. You can optionally filter tiers.
"""

import argparse
import csv
from pathlib import Path


DEFAULT_INPUT = Path("data/characters_flagged.csv")
DEFAULT_OUTPUT = Path("data/characters_curated.csv")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export curated characters from graded CSV."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to graded CSV (default: data/characters_flagged.csv)",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to curated CSV output (default: data/characters_curated.csv)",
    )
    parser.add_argument(
        "--tiers",
        default="",
        help="Optional comma-separated tier filter, e.g. S,A,B",
    )
    parser.add_argument(
        "--keep-value",
        default="yes",
        help="Value in keep column to include (default: yes)",
    )
    return parser.parse_args()


def normalize_tiers(raw_tiers):
    if not raw_tiers:
        return set()
    return {tier.strip().upper() for tier in raw_tiers.split(",") if tier.strip()}


def run():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    keep_value = args.keep_value.strip().lower()
    tier_filter = normalize_tiers(args.tiers)

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    with input_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames:
        raise ValueError("Input CSV has no header row.")

    required_cols = {"name", "keep"}
    missing = required_cols - set(fieldnames)
    if missing:
        raise ValueError(f"Input CSV missing required columns: {sorted(missing)}")

    curated = []
    for row in rows:
        row_keep = (row.get("keep") or "").strip().lower()
        if row_keep != keep_value:
            continue

        if tier_filter:
            row_tier = (row.get("tier") or "").strip().upper()
            if row_tier not in tier_filter:
                continue

        curated.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(curated)

    print(f"Loaded rows:      {len(rows)}")
    print(f"Curated rows:     {len(curated)}")
    print(f"Tier filter:      {','.join(sorted(tier_filter)) if tier_filter else '(none)'}")
    print(f"Keep value:       {keep_value}")
    print(f"Saved output to:  {output_path}")


if __name__ == "__main__":
    run()
