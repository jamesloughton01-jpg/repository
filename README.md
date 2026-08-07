# Old English Repository

A personal reference of Old English (Anglo-Saxon) vocabulary, phrases,
grammar rules, and full parallel-translation texts, built up incrementally
for private language-learning use. Browsed and quizzed via a Streamlit app.

## Project status (last updated 2026-08-07)

- **Vocabulary**: [`vocabulary.md`](vocabulary.md) — 508 hand-curated
  entries, cross-referenced against every text in `texts/` so common words
  appearing in the texts are covered.
- **Texts**: [`texts/`](texts/) — 20 full parallel-translation (Old
  English / Modern English) works: Beowulf (partial — see note below),
  The Battle of Maldon, The Wanderer, The Seafarer, The Dream of the Rood,
  Cædmon's Hymn, The Ruin, Bede's Death Song, The Battle of Brunanburh,
  The Finnsburh Fragment, The Descent into Hell, Maxims I, The Rune Poem,
  Ælfric's Life of St Edmund, a curated Exeter Book Riddles selection,
  Durham, a selection of Metrical Charms, The Wife's Lament, The
  Husband's Message, and a short excerpt of The Proverbs of Alfred. All
  Modern English translations are my own original composition (see
  Sourcing below). **Beowulf is deliberately frozen** at lines 1–257
  (Prelude + Fitts I–III) and is not being extended further — see the
  note at the top of `texts/beowulf.md` for why. **The Proverbs of
  Alfred is Early Middle English, not Old English** (c. 1150-1180) —
  included for context/comparison, flagged clearly in its own header,
  and kept to a 16-line excerpt because the source is a complex
  four-manuscript critical edition (see note at the top of
  `texts/the-proverbs-of-alfred.md`).
- **Phrases**: [`phrases.md`](phrases.md) — 30 notable lines with citations.
- **Grammar**: [`grammar.md`](grammar.md) — 11 topics (cases, gender, verb
  classes, adjective declension, word order, dual pronouns, negation,
  prepositions, the "sceal" construction, relative clauses, kennings).
- **Alphabet**: [`alphabet.md`](alphabet.md) — letters and pronunciation.
- **Runes**: [`runes.md`](runes.md) — all 29 Futhorc runes plus background
  on their development and replacement by the Latin alphabet; shown in the
  app as a grid of large clickable squares (click reveals name/sound/
  meaning), not a plain table.
- **Sentences**: [`sentences.md`](sentences.md) — 50 short clauses excerpted
  from texts already in the repo; [`practice-sentences.md`](practice-sentences.md)
  — 46 original grammar-drilling sentences I composed (not from any text).
- **App**: [`scripts/app.py`](scripts/app.py) — Streamlit app with tabs for
  Vocabulary, Phrases, Grammar, Alphabet, Runes, Practice Sentences, Texts,
  and Quiz (Words / Sentences / Fill-in-the-Blank modes), plus an animated
  English↔Old English subtitle under the title.
- **Bulk dictionary**: Henry Sweet's *A Student's Dictionary of
  Anglo-Saxon*, ~25,600 entries, optional merge-in (see below).
- **Sourcing note**: two texts (`durham.md`, `exeter-book-riddles.md`) had
  an inaccurate Old English text citation ("Cook & Tinker 1902") that was
  traced and corrected; several other texts (Seafarer, Cædmon's Hymn,
  Maxims I, Descent into Hell, Finnsburh Fragment, Bede's Death Song, the
  Metrical Charms) still carry that same unverified citation and haven't
  been re-checked yet.

To continue this project in a new session, just point Claude at this
repo directory — this README plus the files it links to are enough context
to pick up where things left off. No other state needs to be carried over.

## Structure

- [`vocabulary.md`](vocabulary.md) — individual words (hand-curated)
- [`phrases.md`](phrases.md) — idioms, formulas, and notable lines from texts
- [`grammar.md`](grammar.md) — case system, verb classes, syntax rules
- [`alphabet.md`](alphabet.md) — letters, vowels, consonant/pronunciation rules
- [`runes.md`](runes.md) — the 29 Futhorc runes, their development, and
  their replacement by the Latin alphabet
- [`sentences.md`](sentences.md) — short clauses excerpted from `texts/`
- [`practice-sentences.md`](practice-sentences.md) — original sentences for
  grammar drilling (not from any historical text; read live by the app,
  not loaded into the DB)
- [`texts/`](texts/) — one Markdown file per work, each with a source
  citation/license header followed by parallel OE/ModE tables (some, like
  the Riddles and Charms, use multiple `## `-headed sections instead of one
  table)
- [`data/sweet-dictionary.csv`](data/sweet-dictionary.csv) — bulk import of
  Henry Sweet's *A Student's Dictionary of Anglo-Saxon* (1896), ~25,600
  entries (see [Bulk dictionary import](#bulk-dictionary-import) below).
  Kept separate from `vocabulary.md` since it's too large to hand-edit.
- [`scripts/build_db.py`](scripts/build_db.py) — compiles the Markdown
  tables (`vocabulary.md`, `phrases.md`, `grammar.md`, `sentences.md`) and
  the Sweet CSV into `old_english.db` (SQLite) for querying and quizzing.
  `texts/*.md`, `alphabet.md`, `runes.md`, and `practice-sentences.md` are
  read live from disk by the app instead, since they don't fit the
  single-table shape.
- [`scripts/import_sweet.py`](scripts/import_sweet.py) — re-fetches and
  re-parses the Sweet dictionary source into `data/sweet-dictionary.csv`
- [`scripts/app.py`](scripts/app.py) — Streamlit app (`streamlit run
  scripts/app.py`) with Vocabulary/Phrases/Grammar/Alphabet/Runes/Practice
  Sentences/Texts/Quiz tabs; a checkbox optionally merges in Sweet's
  Dictionary. The Runes tab renders `runes.md`'s table as a grid of large
  clickable squares (`render_rune_grid()`, pure CSS click-to-reveal, no
  server round-trip) instead of a plain table. **After editing any
  Markdown file or rebuilding the DB, fully stop and restart the Streamlit
  server** — `@st.cache_data` plus process reuse means a plain reload can
  serve stale data.

Each hand-curated file is a single Markdown table (one row = one entry) or,
for larger reference sections, several tables split by `## ` subheadings.
Keeping entries in tables (rather than free prose) means the files stay
easy to hand-edit *and* are trivially machine-readable — that's the "merge"
of the Markdown and database approaches: Markdown is the source of truth
you edit, SQLite is a generated view you query.

## Sourcing

- **Definitions**: [Bosworth-Toller Anglo-Saxon Dictionary](https://bosworthtoller.com/)
  (free, online, the standard reference)
- **Grammar**: Mitchell & Robinson, *A Guide to Old English* (or equivalent) —
  summarize rules in your own words rather than copying text verbatim
- **Example lines**: primary texts (*Beowulf*, the *Anglo-Saxon Chronicle*,
  etc.), all public domain

Always fill in the `Source` column per entry so you can re-verify later.
Line numbers can vary slightly by edition — note which edition you used if
it matters.

## Workflow

1. While reading or looking something up, add a row to the relevant table.
2. Keep rows roughly alphabetical by the first column (not enforced, just
   makes scanning easier — a re-sort script could be added later if the
   files get long).
3. Periodically re-run `build_db.py` to refresh the SQLite database.

## Building the database

Python 3 and Streamlit are installed on this machine. After editing
`vocabulary.md`, `phrases.md`, `grammar.md`, or `sentences.md`, rebuild
the database with:

```bash
python scripts/build_db.py
```

This regenerates `old_english.db` (stdlib only — no dependencies to
install) and prints row counts per table so you can sanity-check that new
rows actually made it in.

### Example queries once the DB exists

No `sqlite3` CLI is installed here — query via Python instead, and set
`PYTHONIOENCODING=utf-8` so æ/þ/ð display correctly in the terminal:

```bash
PYTHONIOENCODING=utf-8 python -c "
import sqlite3
conn = sqlite3.connect('old_english.db')
for row in conn.execute('SELECT word, gloss FROM vocabulary ORDER BY RANDOM() LIMIT 10'):
    print(row)
"
```

Or browse visually with [DB Browser for SQLite](https://sqlitebrowser.org/)
(File → Open Database → `old_english.db`), or run the Streamlit app:

```bash
python -m streamlit run scripts/app.py
```

## Bulk dictionary import

`data/sweet-dictionary.csv` is a bulk, automated parse of Henry Sweet's
*A Student's Dictionary of Anglo-Saxon* (1896), from the HTML edition at
https://mikepope.com/sweet/sweet-dictionary-entries.html, licensed
**CC BY-NC-SA 4.0** (attribution required, non-commercial, share-alike).
Keep that attribution if this data is ever shared or published.

It's kept out of `vocabulary.md` deliberately — at ~25,600 entries it
would make the hand-edited file unusable. Instead:

- `scripts/import_sweet.py` fetches the source page and regenerates the CSV
- `scripts/build_db.py` loads it into its own `vocabulary_sweet` table
  (separate from your hand-curated `vocabulary` table)
- the Streamlit app has a checkbox to merge it into the Vocabulary/Quiz
  views on demand

The parser takes a pragmatic approach: each entry's headword comes from
the page's entry `id` (clean, unaccented issues aside), and the full
definition text — including Sweet's part-of-speech/verb-class notation,
which is idiosyncratic and not reliably auto-splittable — is kept together
in the `gloss` column rather than parsed into separate fields. A small
number of entries (roughly 1 in 500) that use a rare dialectal-vowel
diacritic may have a slightly malformed headword as a result of that
simplification.
