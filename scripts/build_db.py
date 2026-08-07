"""Compile vocabulary.md, phrases.md, and grammar.md into old_english.db.

Usage: python scripts/build_db.py

Reads the three Markdown pipe-tables in the repo root and rebuilds a
SQLite database with one table per file, so the data can be queried or
used for random-entry quizzing. Also loads data/sweet-dictionary.csv
(bulk import, see scripts/import_sweet.py) into vocabulary_sweet, kept
separate from the hand-curated vocabulary table. Stdlib only, no
dependencies.
"""

import csv
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "old_english.db"
SWEET_CSV = ROOT / "data" / "sweet-dictionary.csv"

SOURCES = {
    "vocabulary": {
        "file": ROOT / "vocabulary.md",
        "columns": ["word", "gloss", "pos", "example", "source"],
    },
    "phrases": {
        "file": ROOT / "phrases.md",
        "columns": ["phrase", "gloss", "text_source", "notes"],
    },
    "grammar": {
        "file": ROOT / "grammar.md",
        "columns": ["topic", "rule", "example", "source", "notes"],
    },
    "sentences": {
        "file": ROOT / "sentences.md",
        "columns": ["old_english", "gloss", "source"],
    },
}

SEPARATOR_ROW = re.compile(r"^\|[\s:|-]+\|$")


def parse_table(path: Path, expected_cols: int) -> list[list[str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if SEPARATOR_ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells and cells[0].lower() in {"old english", "topic", "old english phrase"}:
            continue  # header row
        if len(cells) != expected_cols:
            continue
        rows.append(cells)
    return rows


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for table_name, spec in SOURCES.items():
        cols = spec["columns"]
        cur.execute(f"DROP TABLE IF EXISTS {table_name}")
        col_defs = ", ".join(f"{c} TEXT" for c in cols)
        cur.execute(f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, {col_defs})")

        rows = parse_table(spec["file"], len(cols))
        placeholders = ", ".join("?" for _ in cols)
        cur.executemany(
            f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})",
            rows,
        )
        print(f"{table_name}: {len(rows)} rows")

    if SWEET_CSV.exists():
        cur.execute("DROP TABLE IF EXISTS vocabulary_sweet")
        cur.execute(
            "CREATE TABLE vocabulary_sweet "
            "(id INTEGER PRIMARY KEY, word TEXT, gloss TEXT, pos TEXT, example TEXT, source TEXT)"
        )
        with SWEET_CSV.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [(r["word"], r["gloss"], r["pos"], r["example"], r["source"]) for r in reader]
        cur.executemany(
            "INSERT INTO vocabulary_sweet (word, gloss, pos, example, source) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        print(f"vocabulary_sweet: {len(rows)} rows")

    conn.commit()
    conn.close()
    print(f"Wrote {DB_PATH}")


if __name__ == "__main__":
    main()
