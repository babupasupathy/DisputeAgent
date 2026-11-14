import streamlit as st

from data import ASSETS

st.title("LLM vs code")
st.caption("Which steps need a language model, and which should be a lookup, a formula or a smaller model.")
st.success("Built as **V1**: decisions moved to code, the model reads text and writes letters. Result: decisions "
           "100%, cost −52%, 0 wrongful auto-accepts. Haiku for reading is still to test. See **Results**.")
st.iframe(ASSETS / "llm_boundary.html", height=4400)
