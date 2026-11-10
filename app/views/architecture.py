import streamlit as st

from data import ASSETS

st.title("Architecture")
st.caption("Click any box in the diagram for what it does and where it lives in the repo.")
st.iframe(ASSETS / "architecture.html", height=4200)
