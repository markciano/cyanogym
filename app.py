import os
import streamlit as st
from src.mappings import apply_mappings
from src.metrics import add_set_metrics
from src.loader import load_workouts

st.set_page_config(page_title="cianogym", page_icon="🏋️", layout="wide")

LOCAL_PATH = "data/workouts.csv"


@st.cache_data
def load_data(path: str):
    """Load, map and enrich the workouts dataset from a file path. Cached."""
    df = load_workouts(path)
    df = apply_mappings(df)
    df = add_set_metrics(df)
    return df


@st.cache_data
def load_data_from_upload(file_bytes: bytes):
    """Load, map and enrich the workouts dataset from uploaded bytes. Cached."""
    import io
    from src.loader import load_workouts_from_buffer
    df = load_workouts_from_buffer(io.BytesIO(file_bytes))
    df = apply_mappings(df)
    df = add_set_metrics(df)
    return df


if "df" not in st.session_state:
    if os.path.exists(LOCAL_PATH):
        st.session_state["df"] = load_data(LOCAL_PATH)
    else:
        st.markdown("## 🏋️ cianogym")
        st.markdown("Upload your Hevy workout export to get started.")
        uploaded = st.file_uploader(
            "Upload workouts.csv (exported from Hevy)",
            type="csv",
            label_visibility="collapsed",
        )
        if uploaded is not None:
            st.session_state["df"] = load_data_from_upload(uploaded.read())
            st.rerun()
        else:
            st.info(
                "Export your workout history from the Hevy app: "
                "**Profile → Settings → Export Workout Data**, "
                "then upload the CSV file above."
            )
            st.stop()

pages = [
    st.Page("pages/01_ejercicio.py",  title="Exercise",  icon="📈"),
    st.Page("pages/02_musculo.py",    title="Muscle",    icon="💪"),
    st.Page("pages/04_sesion.py",     title="Sessions",  icon="📅"),
    st.Page("pages/05_mesociclo.py",  title="Mesocycle", icon="🔄"),
    st.Page("pages/06_cardio.py",     title="Cardio",    icon="🏃"),
]

pg = st.navigation(pages)
pg.run()