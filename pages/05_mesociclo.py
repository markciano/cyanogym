from typing import Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.kpi-card {
    background: #111118;
    border: 1px solid #22222e;
    border-radius: 10px;
    padding: 18px;
}
.kpi-label {
    font-family: 'DM Mono', monospace;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #aaaacc;
    margin-bottom: 6px;
}
.kpi-value {
    font-family: 'DM Mono', monospace;
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -1px;
    color: #e8e8f0;
}
.kpi-unit {
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    color: #888899;
    margin-left: 4px;
}
.page-title {
    font-family: 'DM Mono', monospace;
    font-size: 22px;
    font-weight: 500;
    color: #e8e8f0;
    letter-spacing: -0.5px;
}
.page-subtitle {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #888899;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-top: 4px;
    margin-bottom: 24px;
}
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    from src.loader import load_workouts
    from src.mappings import apply_mappings
    from src.metrics import add_set_metrics
    st.session_state["df"] = add_set_metrics(apply_mappings(load_workouts()))

df_full = st.session_state["df"]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">🔄 Mesocycle</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">cross-mesocycle comparison · strength progression</div>', unsafe_allow_html=True)

# ── Guard: require at least one session with a mesocycle pattern ──────────────
EXCLUDED = {"Cardio", "Mobility"}
working = df_full[
    df_full["set_type"].isin(["normal", "dropset"]) &
    ~df_full["musculo_principal"].isin(EXCLUDED)
].copy()

if not working["meso_num"].notna().any():
    st.info(
        "No mesocycle data detected. "
        "Sessions must include patterns like **Upper w3** (Meso 1) "
        "or **Upper w1m2** (Meso 2+) to enable this comparison."
    )
    st.stop()

# ── Prepare meso data ─────────────────────────────────────────────────────────
meso_data = working[working["meso_num"].notna()].copy()
meso_data["meso_label"] = meso_data["meso_num"].apply(lambda x: f"Meso {int(x)}")

# ── Info cards ────────────────────────────────────────────────────────────────
n_mesos     = int(meso_data["meso_num"].nunique())
latest_meso = int(meso_data["meso_num"].max())
n_sessions  = int(meso_data["start_time"].nunique())

c1, c2, c3 = st.columns(3)
for col, label, value, unit in [
    (c1, "Mesocycles detected", n_mesos,    ""),
    (c2, "Latest mesocycle",    latest_meso, ""),
    (c3, "Sessions in mesos",   n_sessions,  ""),
]:
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div><span class="kpi-value">{value}</span><span class="kpi-unit">{unit}</span></div>
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

# ── Muscle + Exercise selectors (same cascade pattern as page 1) ──────────────
muscles_available = sorted(meso_data["musculo_principal"].dropna().unique())

col_muscle, col_ex = st.columns([2, 4])
with col_muscle:
    selected_muscle = st.selectbox(
        "Muscle group", muscles_available,
        key="meso_muscle",
        label_visibility="visible",
    )

exercises_for_muscle = sorted(
    meso_data[meso_data["musculo_principal"] == selected_muscle]["exercise_title"].unique()
)

if st.session_state.get("_meso_muscle_last") != selected_muscle:
    st.session_state["_meso_muscle_last"] = selected_muscle
    st.session_state["meso_exercise"] = exercises_for_muscle[0]
elif st.session_state.get("meso_exercise") not in exercises_for_muscle:
    st.session_state["meso_exercise"] = exercises_for_muscle[0]

with col_ex:
    selected_exercise = st.selectbox(
        "Exercise", exercises_for_muscle,
        key="meso_exercise",
        label_visibility="visible",
    )

# ── Metric selector ───────────────────────────────────────────────────────────
metric_radio = st.radio(
    "Metric", ["Est. 1RM", "Max weight", "Volume / set"],
    index=0, horizontal=True, label_visibility="visible",
)
METRIC_COL = {"Est. 1RM": "est_1rm", "Max weight": "max_weight", "Volume / set": "vol_per_set"}
METRIC_UNIT = {"Est. 1RM": "kg", "Max weight": "kg", "Volume / set": "kg"}
METRIC_COLORS = {"Est. 1RM": "#5b8fff", "Max weight": "#4ecdc4", "Volume / set": "#ffd93d"}

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

# ── Aggregate per exercise × mesocycle ───────────────────────────────────────
agg_all = (
    meso_data.groupby(["musculo_principal", "exercise_title", "meso_label", "meso_num"])
    .agg(
        max_weight=("weight_kg",      "max"),
        vol_per_set=("volume_per_set", "mean"),
        est_1rm=("estimated_1rm",     "max"),
    )
    .reset_index()
    .dropna(subset=["est_1rm"])
)

# ── Chart: selected exercise across mesocycles ────────────────────────────────
ex_agg = (
    agg_all[agg_all["exercise_title"] == selected_exercise]
    .sort_values("meso_num")
)

col   = METRIC_COL[metric_radio]
color = METRIC_COLORS[metric_radio]
unit  = METRIC_UNIT[metric_radio]

if not ex_agg.empty:
    fig = go.Figure(go.Bar(
        x=ex_agg["meso_label"],
        y=ex_agg[col],
        marker_color=color,
        text=ex_agg[col].round(1),
        textposition="outside",
        textfont=dict(size=11, color="#e8e8f0"),
    ))
    fig.update_layout(
        paper_bgcolor="#111118", plot_bgcolor="#111118",
        font=dict(family="DM Mono", color="#e8e8f0", size=12),
        margin=dict(l=12, r=12, t=40, b=12),
        title=dict(
            text=f"{selected_exercise} — {metric_radio} per mesocycle",
            font=dict(size=14, color="#ccccdd"), x=0,
        ),
        xaxis=dict(gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=12)),
        yaxis=dict(
            gridcolor="#22222e", linecolor="#22222e",
            tickfont=dict(size=11), title=unit,
            title_font=dict(size=11, color="#888899"),
        ),
        height=260,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for this exercise across mesocycles.")

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

# ── Comparison: all exercises in selected muscle, grouped by mesocycle ────────
MESO_COLORS = ["#5b8fff", "#4ecdc4", "#ffd93d", "#ff6b6b", "#c084fc"]

@st.fragment
def comparison_section(selected_muscle: str, selected_exercise: str, agg_all: pd.DataFrame) -> None:
    """Grouped horizontal bar chart: all exercises in muscle, one bar per mesocycle."""
    comp_metric = st.radio(
        "Compare by", ["Est. 1RM", "Max weight", "Volume / set"],
        index=0, horizontal=True, label_visibility="visible",
    )
    comp_col = METRIC_COL[comp_metric]

    muscle_agg = agg_all[agg_all["musculo_principal"] == selected_muscle].copy()
    mesos = sorted(muscle_agg["meso_num"].unique())

    if muscle_agg.empty:
        st.info("No comparison data for this muscle group.")
        return

    # Order exercises by their best value across all mesos
    ex_order = (
        muscle_agg.groupby("exercise_title")[comp_col]
        .max()
        .sort_values(ascending=True)
        .index.tolist()
    )

    fig = go.Figure()
    for i, meso_n in enumerate(mesos):
        df_m = muscle_agg[muscle_agg["meso_num"] == meso_n].set_index("exercise_title")
        values = [df_m.loc[ex, comp_col] if ex in df_m.index else None for ex in ex_order]
        fig.add_trace(go.Bar(
            x=values,
            y=ex_order,
            orientation="h",
            name=f"Meso {int(meso_n)}",
            marker_color=MESO_COLORS[i % len(MESO_COLORS)],
            text=[f"{v:.1f}" if v is not None else "" for v in values],
            textposition="outside",
            textfont=dict(size=10, color="#e8e8f0"),
        ))

    fig.update_layout(
        paper_bgcolor="#111118", plot_bgcolor="#111118",
        font=dict(family="DM Mono", color="#e8e8f0", size=12),
        barmode="group",
        margin=dict(l=12, r=48, t=40, b=12),
        title=dict(
            text=f"Muscle comparison — {comp_metric}",
            font=dict(size=14, color="#ccccdd"), x=0,
        ),
        legend=dict(
            orientation="h", x=1, xanchor="right", y=1.1,
            font=dict(size=11), bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=11)),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="#22222e", tickfont=dict(size=11)),
        height=max(280, len(ex_order) * 32 * len(mesos)),
    )
    st.plotly_chart(fig, use_container_width=True)


comparison_section(selected_muscle, selected_exercise, agg_all)
