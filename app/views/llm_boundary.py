import streamlit as st

from data import ASSETS

st.title("LLM vs code")
st.caption("Which steps need a language model and which are lookups or formulas, in V0 and in V1.")
st.iframe(ASSETS / "llm_boundary.html", height=4400)
