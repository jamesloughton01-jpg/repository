"""Interactive Streamlit viewer for the Old English repository.

Usage: streamlit run scripts/app.py

Reads old_english.db (built by build_db.py) and shows the vocabulary,
phrases, and grammar tables with search/filter, plus a quiz mode. Also
reads the parallel-text poems directly from texts/*.md.
"""

import base64
import html
import random
import re
import sqlite3
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "old_english.db"
TEXTS_DIR = ROOT / "texts"
ALPHABET_PATH = ROOT / "alphabet.md"
RUNES_PATH = ROOT / "runes.md"
NUMBERS_PATH = ROOT / "numbers.md"
PRACTICE_PATH = ROOT / "practice-sentences.md"
HELMET_PATH = ROOT / "assets" / "helmet.png"
TITLE_FONT = "'Source Serif Pro', Georgia, serif"

st.set_page_config(page_title="Old English Repository", layout="wide")


@st.cache_data
def load_table(name: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {name}", conn)
    except pd.errors.DatabaseError:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df.drop(columns=["id"], errors="ignore")


def filtered_view(df: pd.DataFrame, key: str) -> pd.DataFrame:
    query = st.text_input("Search", key=key, placeholder="Filter rows...")
    if not query:
        return df
    mask = df.apply(lambda col: col.astype(str).str.contains(query, case=False, na=False))
    return df[mask.any(axis=1)]


OE_ACCENT = "#FF4B4B"


@st.cache_data
def load_helmet_data_uri() -> str:
    """Sutton Hoo helmet artwork (red linework, transparent background),
    inlined as a data URI so it renders without a separate HTTP request."""
    data = HELMET_PATH.read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")


def style_oe_columns(df: pd.DataFrame, *columns: str):
    """Color the given Old English columns with the same red used for the
    active-tab underline, leaving other columns unstyled."""
    cols = [c for c in columns if c in df.columns]
    if not cols:
        return df
    return df.style.set_properties(subset=cols, **{"color": OE_ACCENT})


@st.cache_data
def list_texts() -> dict:
    if not TEXTS_DIR.exists():
        return {}
    titles = {}
    for path in sorted(TEXTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        titles[match.group(1) if match else path.stem] = path
    return titles


@st.cache_data
def load_text(path_str: str) -> tuple:
    """Parse a texts/*.md file into a header plus a list of sections.

    Most files are a single table (one poem). Files with "## " subheadings
    (e.g. a riddle collection) are split into one section per subheading,
    each with its own table and any trailing note (like a solution line).
    """
    path = Path(path_str)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    first_table = next((i for i, ln in enumerate(lines) if ln.startswith("|")), len(lines))
    header = "\n".join(lines[:first_table]).strip()

    raw_sections = []
    current_title = None
    current_lines = []
    for ln in lines[first_table:]:
        if ln.startswith("## "):
            if current_lines:
                raw_sections.append((current_title, current_lines))
            current_title = ln[3:].strip()
            current_lines = []
        else:
            current_lines.append(ln)
    if current_lines:
        raw_sections.append((current_title, current_lines))

    sections = []
    for title, sec_lines in raw_sections:
        columns, rows, note_lines = None, [], []
        for ln in sec_lines:
            if ln.startswith("|"):
                cells = [c.strip() for c in ln.strip("|").split("|")]
                if set("".join(cells)) <= {"-", ":"}:
                    continue  # separator row
                if columns is None:
                    columns = cells
                elif len(cells) == len(columns):
                    rows.append(cells)
            elif ln.strip():
                note_lines.append(ln.strip())
        df = pd.DataFrame(rows, columns=columns or [])
        sections.append({"title": title, "df": df, "note": "\n".join(note_lines).strip()})

    return header, sections


def render_rune_grid(df: pd.DataFrame) -> None:
    """Render a grid of large clickable rune squares (pure CSS flip-card,
    no server round-trip: click reveals name/sound/meaning instantly)."""
    cols = list(df.columns)
    rune_col, name_col, sound_col, meaning_col = cols[0], cols[1], cols[2], cols[3]

    cards = []
    for i, row in df.iterrows():
        cards.append(f"""
        <label class="rune-card" for="rune-{i}">
          <input type="checkbox" id="rune-{i}" class="rune-toggle">
          <span class="rune-face">
            <span class="rune-glyph">{row[rune_col]}</span>
          </span>
          <span class="rune-back">
            <strong>{row[name_col]}</strong>
            <span>Sound: {row[sound_col]}</span>
            <span class="rune-meaning">&ldquo;{row[meaning_col]}&rdquo;</span>
          </span>
        </label>""")

    st.markdown(
        f"""
        <style>
        .runes-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 14px;
            margin: 1rem 0 2rem 0;
        }}
        .rune-card {{
            position: relative;
            display: block;
            aspect-ratio: 1 / 1;
            border: 2px solid rgba(150, 150, 150, 0.4);
            border-radius: 10px;
            cursor: pointer;
            overflow: hidden;
            background: rgba(150, 150, 150, 0.06);
            transition: background 0.15s ease, transform 0.15s ease;
        }}
        .rune-card:hover {{
            background: rgba(150, 150, 150, 0.16);
            transform: translateY(-2px);
        }}
        .rune-toggle {{
            position: absolute;
            width: 0;
            height: 0;
            opacity: 0;
            pointer-events: none;
        }}
        .rune-face, .rune-back {{
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 6px;
            transition: opacity 0.15s ease;
        }}
        .rune-glyph {{
            font-size: 3.2rem;
            line-height: 1;
            color: {OE_ACCENT};
        }}
        .rune-back {{
            opacity: 0;
            gap: 3px;
            font-size: 0.72rem;
            color: #f5f5f5;
            background: rgba(20, 20, 20, 0.92);
        }}
        .rune-back strong {{
            font-size: 0.95rem;
        }}
        .rune-meaning {{
            font-style: italic;
            opacity: 0.85;
        }}
        .rune-toggle:checked ~ .rune-face {{
            opacity: 0;
        }}
        .rune-toggle:checked ~ .rune-back {{
            opacity: 1;
        }}
        </style>
        <div class="runes-grid">{"".join(cards)}</div>
        """,
        unsafe_allow_html=True,
    )


def load_sentence_pool() -> pd.DataFrame:
    sent_df = load_table("sentences").rename(
        columns={"old_english": "prompt", "gloss": "answer"}
    )[["prompt", "answer"]]

    practice_df = pd.DataFrame(columns=["prompt", "answer"])
    if PRACTICE_PATH.exists():
        _, practice_sections = load_text(str(PRACTICE_PATH))
        if practice_sections:
            practice_df = pd.concat(
                [s["df"] for s in practice_sections], ignore_index=True
            ).rename(columns={"Old English": "prompt", "Modern English": "answer"})[
                ["prompt", "answer"]
            ]

    return pd.concat([sent_df, practice_df], ignore_index=True), len(sent_df), len(practice_df)


def render_homescreen() -> None:
    """Landing screen: Old/Modern English words drift up the page and
    swap languages as they go; a real st.button (not a JS-only control,
    since components.html runs sandboxed in an iframe and can't reach
    back into Streamlit's own state) takes the visitor into the app."""
    st.markdown(
        textwrap.dedent(
            f"""
            <div style="text-align:center; margin-top:2rem;">
                <h1 style="margin-bottom:0; font-family:{TITLE_FONT}; color:{OE_ACCENT};">Old English Repository</h1>
                <p style="color:rgba(250,250,250,0.65); font-size:1.05rem; margin-top:0.3rem;">
                    Wilcuma. Welcome. Click Start when you're ready to begin.
                </p>
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )

    vocab = load_table("vocabulary")
    pool = vocab.dropna(subset=["word", "gloss"])
    sample = pool.sample(min(24, len(pool))) if len(pool) else pool

    words = []
    for _, row in sample.iterrows():
        oe = str(row["word"]).replace("\\", "").replace('"', "&quot;")
        gloss = str(row["gloss"]).split(";")[0].split(",")[0].strip()
        en = gloss.replace('"', "&quot;") or oe
        words.append((oe, en))

    cards = []
    for i, (oe, en) in enumerate(words):
        left = random.uniform(2, 94)
        duration = random.uniform(14, 26)
        delay = -random.uniform(0, duration)
        size = random.uniform(1.1, 2.4)
        swap_period = random.uniform(2200, 4200)
        swap_offset = random.uniform(0, swap_period)
        cards.append(
            f"""<span class="floating-word"
                data-oe="{oe}" data-en="{en}" data-flip="0"
                data-period="{swap_period}" data-offset="{swap_offset}"
                style="left:{left}%; font-size:{size}rem;
                       animation-duration:{duration}s; animation-delay:{delay}s;">{oe}</span>"""
        )

    components.html(
        f"""
        <style>
        html, body {{ margin: 0; overflow: hidden; background: transparent; }}
        .float-stage {{
            position: relative;
            width: 100%;
            height: 480px;
            overflow: hidden;
        }}
        @keyframes floatUp {{
            0%   {{ transform: translateY(520px); opacity: 0; }}
            8%   {{ opacity: 0.85; }}
            92%  {{ opacity: 0.85; }}
            100% {{ transform: translateY(-560px); opacity: 0; }}
        }}
        .floating-word {{
            position: absolute;
            bottom: 0;
            font-weight: 700;
            font-family: 'Source Serif Pro', Georgia, serif;
            color: rgba(255, 75, 75, 0.85);
            white-space: nowrap;
            animation-name: floatUp;
            animation-timing-function: linear;
            animation-iteration-count: infinite;
            text-shadow: 0 0 12px rgba(255, 75, 75, 0.25);
        }}
        </style>
        <div class="float-stage">
            {"".join(cards)}
        </div>
        <script>
        document.querySelectorAll('.floating-word').forEach((el) => {{
            const oe = el.dataset.oe, en = el.dataset.en;
            const period = parseFloat(el.dataset.period);
            const offset = parseFloat(el.dataset.offset);
            let showingOe = true;
            setTimeout(() => {{
                setInterval(() => {{
                    el.style.transition = 'opacity 0.4s ease';
                    el.style.opacity = 0.15;
                    setTimeout(() => {{
                        showingOe = !showingOe;
                        el.textContent = showingOe ? oe : en;
                        el.style.opacity = 0.85;
                    }}, 400);
                }}, period);
            }}, offset);
        }});
        </script>
        """,
        height=480,
    )

    st.markdown(
        """
        <style>
        div[data-testid="stButton"] button[kind="primary"] {
            display: block;
            margin: 0.5rem auto 0 auto;
            font-size: 1.4rem;
            font-weight: 700;
            padding: 0.7rem 3.5rem;
            border-radius: 999px;
            background-color: transparent;
            color: #ffffff;
            border: 2px solid #ffffff;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background-color: rgba(255, 255, 255, 0.1);
            color: #ffffff;
            border: 2px solid #ffffff;
        }
        div[data-testid="stButton"] button[kind="primary"]:focus:not(:active) {
            background-color: transparent;
            color: #ffffff;
            border: 2px solid #ffffff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("Start", type="primary", key="start_button", use_container_width=True):
            st.session_state.app_started = True
            st.rerun()


_CLEAN_TERM_RE = re.compile(r"[A-Za-z][A-Za-z '-]*")
_PARADIGM_GLOSS_RE = re.compile(
    r"\(\s*(ic|þū|þu|hē|he|hēo|heo|hit|wē|we|gē|ge|hīe|hie|hi|þēc|þonne)\s*\)", re.IGNORECASE
)


def _is_paradigm_listing(gloss: str) -> bool:
    """Sweet's Dictionary sometimes glosses an irregular verb (e.g. wesan)
    with its whole conjugation table instead of a definition — 'wesan,
    beon; (ic) eom, ... (he) is, bith; ...'. Splitting that on commas
    would extract conjugated forms like 'is' as if they were synonyms
    and wrongly map them back to the infinitive. Detected by parenthetical
    pronoun markers and skipped entirely rather than parsed."""
    return bool(_PARADIGM_GLOSS_RE.search(gloss))


def _gloss_terms(gloss: str) -> list:
    """Split a dictionary gloss like 'wealth, cattle' or 'the Measurer
    (God, or Fate)' into short standalone terms usable for lookup.
    Sweet's Dictionary glosses are raw, unedited dictionary definitions
    and can contain footnote marks, abbreviations, and other notation
    (e.g. daggers marking obsolete words) — anything that isn't a clean
    run of letters is rejected rather than risk leaking that notation
    into a translation."""
    if _is_paradigm_listing(gloss):
        return []
    cleaned = re.sub(r"\([^)]*\)", " ", gloss)
    cleaned = re.sub(r"—.*$", "", cleaned)
    parts = re.split(r"[;,/]|\bor\b", cleaned)
    terms = []
    for part in parts:
        term = part.strip().strip(".!?;:").strip()
        term = re.sub(r"^(a|an|the)\s+", "", term, flags=re.IGNORECASE).strip()
        if term and len(term) < 40 and _CLEAN_TERM_RE.fullmatch(term):
            terms.append(term)
    return terms


# The translator only matches exact dictionary headwords (no conjugation
# awareness), so even a very common verb like "habban" translates its own
# infinitive fine but not "hæbbe" ("I have"). Full conjugation is out of
# scope, but these five verbs are so frequent that leaving every inflected
# form untranslated would make the translator feel broken on ordinary
# sentences. Old-English-to-Modern-English direction only; translating a
# Modern English verb still correctly produces the Old English infinitive.
_IRREGULAR_OE_VERB_FORMS = {
    # habban "to have"
    "hæbbe": "have", "hafast": "have", "hafaþ": "have", "hafað": "have",
    "hæfst": "have", "hæfð": "have", "hæfþ": "have",
    "habbaþ": "have", "habbað": "have",
    "hæfde": "had", "hæfdest": "had", "hæfdon": "had",
    # wesan / bēon "to be"
    "eom": "am", "eart": "are", "is": "is", "sind": "are", "sindon": "are",
    "beo": "am", "bist": "are", "biþ": "is", "bið": "is", "beoþ": "are", "beoð": "are",
    "wæs": "was", "wære": "were", "wæron": "were",
    # willan "will, to wish"
    "wille": "want", "wilt": "want", "wile": "wants",
    "willað": "want", "willaþ": "want",
    "wolde": "wanted", "woldest": "wanted", "woldon": "wanted",
    # sculan "shall, must"
    "sceal": "must", "scealt": "must", "sculon": "must",
    "sceolde": "had to", "sceoldon": "had to",
    # magan "may, to be able"
    "mæg": "can", "meaht": "can", "miht": "can", "magon": "can",
    "meahte": "could", "mihte": "could", "meahton": "could", "mihton": "could",
}

# Same idea, for the handful of extremely common nouns whose plural is
# formed by i-mutation rather than just adding an ending -- "bōc" (book)
# is in the dictionary, but its plural "bēc" doesn't share enough letters
# with "bōc" for any suffix-based rule to help. Limited to nouns whose
# singular is already a vocabulary.md headword.
_IRREGULAR_OE_NOUN_PLURALS = {
    "bec": "books", "bēc": "books",        # bōc "book"
    "menn": "men",                         # mann "man"
    "fet": "feet", "fēt": "feet",          # fōt "foot"
    "teð": "teeth", "tēð": "teeth",        # tōð "tooth"
}

_MACRON_STRIP = str.maketrans("āēīōūȳǣ", "aeiouyæ")


def _strip_macrons(word: str) -> str:
    return word.translate(_MACRON_STRIP)


@st.cache_data
def build_translation_maps() -> tuple:
    """Build word-lookup dicts for the translator box: Old English -> a
    short Modern English gloss, and Modern English -> an Old English
    headword. vocabulary.md is indexed first so it always wins; Sweet's
    Dictionary only fills in words vocabulary.md doesn't have."""
    oe_to_mode: dict = {}
    mode_to_oe: dict = {}

    def index(df: pd.DataFrame) -> None:
        for _, row in df.iterrows():
            oe_field = str(row.get("word", "") or "").strip()
            gloss_field = str(row.get("gloss", "") or "").strip()
            if not oe_field or not gloss_field:
                continue
            oe_variants = [v.strip() for v in oe_field.split("/") if v.strip()]
            if not oe_variants:
                continue
            terms = _gloss_terms(gloss_field)
            if terms:
                for oe_word in oe_variants:
                    oe_to_mode.setdefault(oe_word.lower(), terms[0])
            for term in terms:
                mode_to_oe.setdefault(term.lower(), oe_variants[0])
                if term.lower().startswith("to "):
                    mode_to_oe.setdefault(term.lower()[3:], oe_variants[0])

    index(load_table("vocabulary"))
    index(load_table("vocabulary_sweet"))

    # Deliberately overrides any dictionary-derived entry for these exact
    # forms (e.g. Sweet's "is" also glosses the unrelated noun "ice") --
    # as a common verb form, "is" should win over a rarer homograph.
    oe_to_mode.update(_IRREGULAR_OE_VERB_FORMS)
    oe_to_mode.update(_IRREGULAR_OE_NOUN_PLURALS)

    # Macrons are a modern editorial convention -- the manuscripts never
    # marked vowel length (see the Alphabet tab) -- so most people typing
    # Old English won't type them either. Add a macron-stripped alias for
    # every headword (e.g. "gear" alongside "gēar") so unaccented input
    # still matches. setdefault only: a real unaccented word always wins
    # over an alias derived from a different, accented one.
    for key, value in list(oe_to_mode.items()):
        stripped = _strip_macrons(key)
        if stripped != key:
            oe_to_mode.setdefault(stripped, value)

    return oe_to_mode, mode_to_oe


_WORD_RE = re.compile(r"^(\W*)(\w+)(\W*)$", re.UNICODE)


def translate_text(text: str, target: str, oe_to_mode: dict, mode_to_oe: dict) -> str:
    """Word-for-word dictionary substitution (not real machine translation).
    Words not found in either dictionary are left exactly as typed."""
    lookup = mode_to_oe if target == "Old English" else oe_to_mode
    out = []
    for token in text.split(" "):
        m = _WORD_RE.match(token)
        if not m:
            out.append(token)
            continue
        lead, core, trail = m.groups()
        replacement = lookup.get(core.lower())
        if replacement is None:
            out.append(token)
        else:
            if core[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]
            out.append(lead + replacement + trail)
    return " ".join(out)


if not DB_PATH.exists():
    st.error(f"No database found at {DB_PATH}. Run `python scripts/build_db.py` first.")
    st.stop()

if "app_started" not in st.session_state:
    st.session_state.app_started = False

if not st.session_state.app_started:
    render_homescreen()
    st.stop()

st.markdown(
    textwrap.dedent(
        f"""
        <div style="display:flex; align-items:center; gap:2.5rem;">
            <h1 style="margin:0; font-size:3.6rem; font-family:{TITLE_FONT}; color:{OE_ACCENT};">Old English Repository</h1>
            <img src="{load_helmet_data_uri()}" alt="Sutton Hoo helmet"
                 style="width:110px; flex-shrink:0; margin-top:2rem;">
        </div>
        """
    ).strip(),
    unsafe_allow_html=True,
)

# Subtitle alternates between English and an Old English rendering every 5s.
# OE translation sourced from vocabulary.md (þis, tō) and Sweet's Dictionary
# for the rest (wilcuma "welcome", hord "treasure/hoard", tōl "tool",
# gereord "language", leornung "the act of learning").
_SUBTITLE_EN = "Welcome to the Old English Repository, a tool for language learning."
_SUBTITLE_OE = "Wilcuma tō þissum Ealdenglisce horde! Þis is tōl tō gereordes leornunge."
components.html(
    f"""
    <div id="oe-subtitle" style="
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 1.05rem;
        color: rgba(250, 250, 250, 0.75);
        opacity: 1;
        transition: opacity 0.5s ease-in-out;
        margin-top: -0.5rem;
        margin-bottom: 1rem;
    ">{_SUBTITLE_EN}</div>
    <script>
        const oeSubtitleTexts = {[_SUBTITLE_EN, _SUBTITLE_OE]!r};
        let oeSubtitleIndex = 0;
        setInterval(() => {{
            const el = document.getElementById('oe-subtitle');
            if (!el) return;
            el.style.opacity = 0;
            setTimeout(() => {{
                oeSubtitleIndex = (oeSubtitleIndex + 1) % oeSubtitleTexts.length;
                el.innerText = oeSubtitleTexts[oeSubtitleIndex];
                el.style.opacity = 1;
            }}, 500);
        }}, 5000);
    </script>
    """,
    height=50,
)

st.markdown(
    """
    <style>
    div[data-testid="stTextInput"] input[aria-label="Translator"] {
        font-size: 1.4rem;
        padding: 0.8rem 1.1rem;
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
translate_target = st.radio(
    "Translate into",
    ["Old English", "Modern English"],
    key="translate_target",
    horizontal=True,
)
translate_input = st.text_input(
    "Translator",
    key="translate_input",
    placeholder="Type a word or phrase to translate…",
    label_visibility="collapsed",
)
if translate_input.strip():
    _oe_to_mode, _mode_to_oe = build_translation_maps()
    _result = translate_text(translate_input, translate_target, _oe_to_mode, _mode_to_oe)
    st.markdown(
        f"""<div style="
            font-size: 1.5rem;
            font-weight: 600;
            padding: 0.9rem 1.1rem;
            margin: 0.5rem 0 1rem 0;
            border: 1px solid rgba(150, 150, 150, 0.35);
            border-radius: 10px;
            background: rgba(150, 150, 150, 0.06);
        ">{html.escape(_result)}</div>""",
        unsafe_allow_html=True,
    )
    st.caption(
        "Word-for-word dictionary lookup — vocabulary.md first, then Sweet's "
        "Dictionary; words not found in either are left unchanged."
    )
else:
    st.caption(
        "Word-for-word translator: checks vocabulary.md first, then Sweet's "
        "Dictionary; unmatched words are left as typed."
    )

tab_vocab, tab_grammar, tab_numbers, tab_alphabet, tab_runes, tab_phrases_sentences, tab_texts, tab_quiz = st.tabs(
    ["Vocabulary", "Grammar", "Numbers", "Alphabet", "Runes", "Phrases & Sentences", "Texts", "Quiz"]
)

with tab_vocab:
    df = load_table("vocabulary")
    include_sweet = st.checkbox(
        "Include Sweet's Dictionary (25,000+ entries, bulk import)", key="vocab_include_sweet"
    )
    if include_sweet:
        df = pd.concat([df, load_table("vocabulary_sweet")], ignore_index=True)
        st.caption(
            "Sweet entries: Henry Sweet, *A Student's Dictionary of Anglo-Saxon* (1896), "
            "HTML edition by mikepope.com, licensed CC BY-NC-SA 4.0."
        )
    vocab_view = filtered_view(df, "vocab_search")
    st.dataframe(
        style_oe_columns(vocab_view, "word"), use_container_width=True, hide_index=True
    )
    st.caption(f"{len(df)} entries")

with tab_grammar:
    df = load_table("grammar")
    st.dataframe(filtered_view(df, "grammar_search"), use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} entries")

with tab_numbers:
    if not NUMBERS_PATH.exists():
        st.info("numbers.md not found.")
    else:
        header, sections = load_text(str(NUMBERS_PATH))
        st.markdown(header)
        for sec in sections:
            if sec["title"]:
                st.subheader(sec["title"])
            row_height = min(600, 38 * (len(sec["df"]) + 1) + 3)
            st.dataframe(
                style_oe_columns(sec["df"], "Old English"),
                use_container_width=True,
                hide_index=True,
                height=row_height,
            )
            if sec["note"]:
                st.markdown(sec["note"])

with tab_alphabet:
    if not ALPHABET_PATH.exists():
        st.info("alphabet.md not found.")
    else:
        header, sections = load_text(str(ALPHABET_PATH))
        st.markdown(header)
        for sec in sections:
            if sec["title"]:
                st.subheader(sec["title"])
            row_height = min(600, 38 * (len(sec["df"]) + 1) + 3)
            st.dataframe(
                style_oe_columns(sec["df"], "Letter", "Letter(s)"),
                use_container_width=True,
                hide_index=True,
                height=row_height,
            )
            if sec["note"]:
                st.markdown(sec["note"])

with tab_runes:
    if not RUNES_PATH.exists():
        st.info("runes.md not found.")
    else:
        header, sections = load_text(str(RUNES_PATH))
        st.markdown(header)
        for sec in sections:
            if sec["title"]:
                st.subheader(sec["title"])
            render_rune_grid(sec["df"])
            if sec["note"]:
                st.markdown(sec["note"])

with tab_phrases_sentences:
    st.header("Phrases")
    df = load_table("phrases")
    st.dataframe(filtered_view(df, "phrases_search"), use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} entries")

    st.divider()

    st.header("Practice Sentences")
    if not PRACTICE_PATH.exists():
        st.info("practice-sentences.md not found.")
    else:
        header, sections = load_text(str(PRACTICE_PATH))
        st.markdown(header)
        for sec in sections:
            if sec["title"]:
                st.subheader(sec["title"])
            row_height = min(600, 38 * (len(sec["df"]) + 1) + 3)
            st.dataframe(
                sec["df"], use_container_width=True, hide_index=True, height=row_height
            )
            if sec["note"]:
                st.markdown(sec["note"])

with tab_texts:
    titles = list_texts()
    if not titles:
        st.info("No texts found in texts/.")
    else:
        choice = st.selectbox("Poem", list(titles.keys()), key="texts_choice")
        header, sections = load_text(str(titles[choice]))
        st.markdown(header)
        for sec in sections:
            if sec["title"]:
                st.subheader(sec["title"])
            row_height = min(600, 38 * (len(sec["df"]) + 1) + 3)
            st.dataframe(
                sec["df"], use_container_width=True, hide_index=True, height=row_height
            )
            if sec["note"]:
                st.markdown(sec["note"])

with tab_quiz:
    quiz_mode = st.radio(
        "Quiz me on", ["Words", "Sentences", "Fill in the Blank"], key="quiz_mode", horizontal=True
    )

    if quiz_mode == "Words":
        quiz_include_sweet = st.checkbox(
            "Quiz from Sweet's Dictionary too", key="quiz_include_sweet"
        )
        df = load_table("vocabulary")
        if quiz_include_sweet:
            df = pd.concat([df, load_table("vocabulary_sweet")], ignore_index=True)
        prompt_col, answer_col = "word", "gloss"
        st.caption(f"{len(df)} entries in the quiz pool.")

        if df.empty:
            st.info("Add some entries first.")
        else:
            state_key = "quiz_Words"
            if state_key not in st.session_state or st.button("Next", key="next_Words"):
                row = df.sample(1).iloc[0]
                st.session_state[state_key] = {
                    "prompt": row[prompt_col],
                    "answer": row[answer_col],
                    "revealed": False,
                }
            current = st.session_state[state_key]
            st.subheader(current["prompt"])
            if st.button("Reveal", key="reveal_Words"):
                current["revealed"] = True
            if current["revealed"]:
                st.success(current["answer"])

    elif quiz_mode == "Sentences":
        df, n_real, n_practice = load_sentence_pool()
        st.caption(f"{n_real} from real texts, {n_practice} original practice sentences ({len(df)} total).")

        if df.empty:
            st.info("Add some entries first.")
        else:
            state_key = "quiz_Sentences"
            if state_key not in st.session_state or st.button("Next", key="next_Sentences"):
                row = df.sample(1).iloc[0]
                st.session_state[state_key] = {
                    "prompt": row["prompt"],
                    "answer": row["answer"],
                    "revealed": False,
                }
            current = st.session_state[state_key]
            st.subheader(current["prompt"])
            if st.button("Reveal", key="reveal_Sentences"):
                current["revealed"] = True
            if current["revealed"]:
                st.success(current["answer"])

    else:  # Fill in the Blank
        df, n_real, n_practice = load_sentence_pool()
        vocab_pool = load_table("vocabulary")["word"].dropna().tolist()
        st.caption(f"{n_real} from real texts, {n_practice} original practice sentences ({len(df)} total).")

        if df.empty or len(vocab_pool) < 3:
            st.info("Add some sentences and vocabulary first.")
        else:
            def new_blank_question():
                row = df.sample(1).iloc[0]
                words = row["prompt"].split()
                blank_len = 2 if len(words) > 6 and random.random() < 0.5 else 1
                blank_len = min(blank_len, len(words))
                start = random.randrange(0, len(words) - blank_len + 1)
                correct = " ".join(words[start:start + blank_len]).strip(".,!?;:\"'")
                blanked = " ".join(words[:start] + ["____"] + words[start + blank_len:])

                other_prompts = [p for p in df["prompt"].tolist() if p != row["prompt"]]
                distractors = set()
                for _ in range(60):
                    if len(distractors) >= 3 or not other_prompts:
                        break
                    ow = random.choice(other_prompts).split()
                    if len(ow) < blank_len:
                        continue
                    i = random.randrange(0, len(ow) - blank_len + 1)
                    chunk = " ".join(ow[i:i + blank_len]).strip(".,!?;:\"'")
                    if chunk and chunk.lower() != correct.lower():
                        distractors.add(chunk)
                distractors = list(distractors)[:3]
                while len(distractors) < 3:
                    w = random.choice(vocab_pool)
                    if w.lower() != correct.lower() and w not in distractors:
                        distractors.append(w)

                choices = distractors + [correct]
                random.shuffle(choices)
                return {
                    "blanked": blanked,
                    "correct": correct,
                    "answer": row["answer"],
                    "choices": choices,
                    "selected": None,
                }

            if "quiz_fitb" not in st.session_state or st.button("Next", key="next_fitb"):
                st.session_state.quiz_fitb = new_blank_question()

            q = st.session_state.quiz_fitb
            st.subheader(q["blanked"])
            cols = st.columns(4)
            for i, choice in enumerate(q["choices"]):
                if cols[i].button(choice, key=f"fitb_choice_{i}"):
                    q["selected"] = choice

            if q["selected"] is not None:
                if q["selected"] == q["correct"]:
                    st.success(f"Correct! {q['answer']}")
                else:
                    st.warning("Not quite — try another option.")
