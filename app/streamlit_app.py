"""Dispute Agent showcase: where the project started, what was measured, and where it goes next.

Run locally:   streamlit run app/streamlit_app.py
Deploy:        Streamlit Community Cloud, main file path app/streamlit_app.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # repo root, for src.review_ui

st.set_page_config(page_title="Dispute Agent", page_icon="⚖️", layout="wide")

VIEWS = Path(__file__).resolve().parent / "views"
pages = [
    st.Page(VIEWS / "overview.py", title="Overview", icon="🏠", default=True),
    st.Page(VIEWS / "architecture.py", url_path="architecture", title="Architecture", icon="🧩"),
    st.Page(VIEWS / "results.py", url_path="results", title="Results", icon="📊"),
    st.Page(VIEWS / "explorer.py", url_path="cases", title="Case explorer", icon="🔎"),
    st.Page(VIEWS / "review.py", url_path="review", title="Review queue", icon="✅"),
    st.Page(VIEWS / "llm_boundary.py", url_path="llm-vs-code", title="LLM vs code", icon="⚙️"),
    st.Page(VIEWS / "roadmap.py", url_path="roadmap", title="Roadmap", icon="🧭"),
]
st.navigation(pages).run()

REPO = "https://github.com/babupasupathy/DisputeAgent/tree/claude/relaxed-faraday-ubs0ec"

with st.sidebar:
    st.link_button("Source code on GitHub", REPO, icon=":material/code:", width="stretch")
    DOCS = REPO.replace("/tree/", "/blob/") + "/docs"
    st.markdown(f"[How decisions were made]({DOCS}/decisions.md) · [Every measurement]({DOCS}/evals.md)")
    st.caption("A product-management portfolio project. All data is synthetic. "
               "Results shown are stored eval runs; this site makes no model calls.")
