import streamlit as st
from src.loader import load_workouts
from src.mappings import apply_mappings
from src.metrics import add_set_metrics


st.set_page_config(page_title="cianogym", page_icon="🏋️", layout="wide")


@st.cache_data
def load_data():
    """Load, map and enrich the workouts dataset. Cached for the session."""
    df = load_workouts()
    df = apply_mappings(df)
    df = add_set_metrics(df)
    return df


if "df" not in st.session_state:
    st.session_state["df"] = load_data()

pages = [
    st.Page("pages/01_ejercicio.py",  title="Exercise",  icon="📈"),
    st.Page("pages/02_musculo.py",    title="Muscle",    icon="💪"),
    st.Page("pages/04_sesion.py",     title="Sessions",  icon="📅"),
    st.Page("pages/05_mesociclo.py",  title="Mesocycle", icon="🔄"),
    st.Page("pages/06_cardio.py",     title="Cardio",    icon="🏃"),
]

pg = st.navigation(pages)
pg.run()
