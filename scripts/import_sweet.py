"""Bulk-import Henry Sweet's *A Student's Dictionary of Anglo-Saxon* (1896)
into data/sweet-dictionary.csv, from Mike Pope's HTML edition:
https://mikepope.com/sweet/sweet-dictionary-entries.html
(CC BY-NC-SA 4.0 - keep attribution, non-commercial, share-alike)

Usage: python scripts/import_sweet.py

This is a separate CSV (not vocabulary.md) because the dictionary has
~25,000 entries -- too many to hand-edit as Markdown. build_db.py loads
it into its own `vocabulary_sweet` table, and the app shows it alongside
your hand-curated vocabulary.md entries without mixing the two files.
"""

import csv
import html
import re
import urllib.request
from pathlib import Path

URL = "https://mikepope.com/sweet/sweet-dictionary-entries.html"
SOURCE_LABEL = (
    "Sweet, A Student's Dictionary of Anglo-Saxon (1896) -- "
    "HTML ed. mikepope.com, CC BY-NC-SA 4.0"
)

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "sweet-dictionary.csv"
CACHE_PATH = ROOT / "data" / "_sweet-source-cache.html"

ENTRY_RE = re.compile(r'<p id="([^"]+)" class="entry">(.*?)</p>', re.DOTALL)
STRIP_LINK_RE = re.compile(r'<a class="entry-link".*?</a>', re.DOTALL)
STRIP_FT_RE = re.compile(r'<span class="ft">.*?</span>', re.DOTALL)
STRIP_TAGS_RE = re.compile(r'<[^>]+>')
WHITESPACE_RE = re.compile(r'\s+')
TRAILING_DIGITS_RE = re.compile(r'\d+$')


def fetch_html() -> str:
    if CACHE_PATH.exists():
        return CACHE_PATH.read_text(encoding="utf-8")
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8")
    CACHE_PATH.parent.mkdir(exist_ok=True)
    CACHE_PATH.write_text(data, encoding="utf-8")
    return data


def clean_text(fragment: str) -> str:
    fragment = STRIP_LINK_RE.sub("", fragment)
    fragment = STRIP_FT_RE.sub("", fragment)
    fragment = STRIP_TAGS_RE.sub(" ", fragment)
    fragment = html.unescape(fragment)
    fragment = WHITESPACE_RE.sub(" ", fragment).strip()
    return fragment


def parse_entries(raw_html: str) -> list[dict]:
    rows = []
    for entry_id, body in ENTRY_RE.findall(raw_html):
        word = html.unescape(TRAILING_DIGITS_RE.sub("", entry_id))
        gloss = clean_text(body)
        if not word or not gloss:
            continue
        rows.append(
            {
                "word": word,
                "gloss": gloss,
                "pos": "",
                "example": "",
                "source": SOURCE_LABEL,
            }
        )
    return rows


def main() -> None:
    raw_html = fetch_html()
    rows = parse_entries(raw_html)

    OUT_PATH.parent.mkdir(exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["word", "gloss", "pos", "example", "source"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Parsed {len(rows)} entries -> {OUT_PATH}")


if __name__ == "__main__":
    main()
