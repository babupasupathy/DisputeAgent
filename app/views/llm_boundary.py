import streamlit as st

from data import ASSETS

st.title("LLM vs code")
st.caption("Which steps need a language model, and which should be a lookup, a formula or a smaller model.")
st.iframe(ASSETS / "llm_boundary.html", height=4400)
