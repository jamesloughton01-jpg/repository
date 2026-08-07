"""Interactive Streamlit viewer for the Old English repository.

Usage: streamlit run scripts/app.py

Reads old_english.db (built by build_db.py) and shows the vocabulary,
phrases, and grammar tables with search/filter, plus a quiz mode. Also
reads the parallel-text poems directly from texts/*.md.
"""

import random
import re
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "old_english.db"
TEXTS_DIR = ROOT / "texts"
ALPHABET_PATH = ROOT / "alphabet.md"
PRACTICE_PATH = ROOT / "practice-sentences.md"

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


st.title("Old English Repository")

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

if not DB_PATH.exists():
    st.error(f"No database found at {DB_PATH}. Run `python scripts/build_db.py` first.")
    st.stop()

tab_vocab, tab_phrases, tab_grammar, tab_alphabet, tab_practice, tab_texts, tab_quiz = st.tabs(
    ["Vocabulary", "Phrases", "Grammar", "Alphabet", "Practice Sentences", "Texts", "Quiz"]
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
    st.dataframe(filtered_view(df, "vocab_search"), use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} entries")

with tab_phrases:
    df = load_table("phrases")
    st.dataframe(filtered_view(df, "phrases_search"), use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} entries")

with tab_grammar:
    df = load_table("grammar")
    st.dataframe(filtered_view(df, "grammar_search"), use_container_width=True, hide_index=True)
    st.caption(f"{len(df)} entries")

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
                sec["df"], use_container_width=True, hide_index=True, height=row_height
            )
            if sec["note"]:
                st.markdown(sec["note"])

with tab_practice:
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
