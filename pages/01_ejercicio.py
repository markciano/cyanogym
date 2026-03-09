import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.filters import WINDOW_OPTIONS, apply_time_filter, get_previous_period_df

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
.kpi-delta-up   { font-family: 'DM Mono', monospace; font-size: 11px; color: #4ecdc4; }
.kpi-delta-down { font-family: 'DM Mono', monospace; font-size: 11px; color: #ff6b6b; }
.kpi-delta-flat { font-family: 'DM Mono', monospace; font-size: 11px; color: #888899; }
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
/* Period radio — 2 rows × 4 columns grid with aligned dots */
div[data-testid="stRadio"]:first-of-type div[role="radiogroup"] {
    display: grid !important;
    grid-template-columns: repeat(4, max-content) !important;
    gap: 4px 24px;
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

# Exclude cardio and mobility from this page
EXCLUDED = {"Cardio", "Mobility"}
working = df_full[
    df_full["set_type"].isin(["normal", "dropset"]) &
    ~df_full["musculo_principal"].isin(EXCLUDED)
].copy()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">📈 Exercise</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">individual progress · RMs · volume</div>', unsafe_allow_html=True)

# ── Period filter — 2 rows × 4 columns via CSS grid ──────────────────────────
window = st.radio(
    "Period", WINDOW_OPTIONS,
    index=WINDOW_OPTIONS.index(st.session_state.get("ex_window", "All")),
    horizontal=True,
    key="ex_window",
    label_visibility="collapsed",
)

st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

# ── Muscle + Exercise selectors ───────────────────────────────────────────────
muscles_available = sorted(working["musculo_principal"].dropna().unique())

col_muscle, col_ex = st.columns([2, 4])

with col_muscle:
    selected_muscle = st.selectbox(
        "Muscle group", muscles_available,
        key="ex_muscle",
        label_visibility="visible"
    )

exercises_for_muscle = sorted(
    working[working["musculo_principal"] == selected_muscle]["exercise_title"].unique()
)

# Reset exercise when muscle changes; preserve it when only period changes
if st.session_state.get("_ex_muscle_last") != selected_muscle:
    st.session_state["_ex_muscle_last"] = selected_muscle
    st.session_state["ex_exercise"] = exercises_for_muscle[0]
elif st.session_state.get("ex_exercise") not in exercises_for_muscle:
    st.session_state["ex_exercise"] = exercises_for_muscle[0]

with col_ex:
    selected_exercise = st.selectbox(
        "Exercise", exercises_for_muscle,
        key="ex_exercise",
        label_visibility="visible"
    )

# ── Filter data ───────────────────────────────────────────────────────────────
df_ex = working[working["exercise_title"] == selected_exercise].copy()
df_filtered = apply_time_filter(df_ex, window)
df_prev = get_previous_period_df(df_ex, window)

# ── KPI helpers ───────────────────────────────────────────────────────────────
def best_1rm(df):
    return df["estimated_1rm"].max() if not df.empty else None

def max_weight(df):
    return df["weight_kg"].max() if not df.empty else None

def avg_vol_per_set(df):
    return df["volume_per_set"].mean() if not df.empty else None

def avg_vol_per_session(df):
    return df.groupby("start_time")["volume_per_set"].sum().mean() if not df.empty else None

def fmt_delta(curr, prev):
    if curr is None or prev is None or prev == 0:
        return '<span class="kpi-delta-flat">—</span>'
    pct = (curr - prev) / prev * 100
    arrow = "▲" if pct > 0 else "▼"
    cls = "kpi-delta-up" if pct > 0 else "kpi-delta-down"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}%</span>'

def kpi_card(label, value, unit, delta_html):
    val_str = f"{value:.1f}" if value is not None else "—"
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div><span class="kpi-value">{val_str}</span><span class="kpi-unit">{unit}</span></div>
        <div style="margin-top:6px">{delta_html}</div>
    </div>"""

# ── KPI row ───────────────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
k1, k2, k3, k4 = st.columns(4)
kpis = [
    ("Est. 1RM",         best_1rm(df_filtered),           best_1rm(df_prev),           "kg"),
    ("Max weight",       max_weight(df_filtered),          max_weight(df_prev),          "kg"),
    ("Volume / set",     avg_vol_per_set(df_filtered),     avg_vol_per_set(df_prev),     "kg"),
    ("Volume / session", avg_vol_per_session(df_filtered), avg_vol_per_session(df_prev), "kg"),
]
for col, (label, curr, prev, unit) in zip([k1, k2, k3, k4], kpis):
    with col:
        st.markdown(kpi_card(label, curr, unit, fmt_delta(curr, prev)), unsafe_allow_html=True)

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# ── Aggregate per session ─────────────────────────────────────────────────────
if not df_filtered.empty:
    agg = (
        df_filtered.groupby("start_time")
        .agg(rm1=("estimated_1rm", "max"), peso=("weight_kg", "max"), vol=("volume_per_set", "mean"))
        .reset_index()
        .sort_values("start_time")
    )
else:
    agg = pd.DataFrame(columns=["start_time", "rm1", "peso", "vol"])

# ── Slim chart helper ─────────────────────────────────────────────────────────
def slim_chart(x, y, color, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=5),
        showlegend=False,
    ))
    fig.update_layout(
        paper_bgcolor="#111118", plot_bgcolor="#111118",
        font=dict(family="DM Mono", color="#e8e8f0", size=12),
        margin=dict(l=12, r=12, t=40, b=12),
        title=dict(text=title, font=dict(size=14, color="#ccccdd"), x=0),
        xaxis=dict(gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=12)),
        yaxis=dict(gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=12)),
        height=200,
    )
    return fig

# ── Charts 1–3: slim stacked ──────────────────────────────────────────────────
st.plotly_chart(slim_chart(agg["start_time"], agg["rm1"],  "#5b8fff", "Est. 1RM (kg)"),    use_container_width=True)
st.plotly_chart(slim_chart(agg["start_time"], agg["peso"], "#4ecdc4", "Max weight (kg)"),  use_container_width=True)
st.plotly_chart(slim_chart(agg["start_time"], agg["vol"],  "#ffd93d", "Volume / set (kg)"),use_container_width=True)

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

# ── Chart 4: Comparison — isolated with fragment to avoid scroll ──────────────
@st.fragment
def comparison_section(selected_muscle, selected_exercise, window, working):
    comp_metric = st.radio(
        "Compare by", ["Est. 1RM", "Max weight", "Volume / set"],
        index=0, horizontal=True, label_visibility="visible"
    )

    df_comp = apply_time_filter(
        working[working["musculo_principal"] == selected_muscle], window
    )

    comp_agg = (
        df_comp.groupby("exercise_title")
        .agg(rm1=("estimated_1rm", "max"), peso=("weight_kg", "max"), vol=("volume_per_set", "mean"))
        .reset_index()
        .dropna(subset=["rm1"])
    )

    comp_col_map = {"Est. 1RM": "rm1", "Max weight": "peso", "Volume / set": "vol"}
    comp_col = comp_col_map[comp_metric]
    comp_agg = comp_agg.sort_values(comp_col, ascending=True)

    bar_colors = ["#5b8fff" if ex == selected_exercise else "#22222e"
                  for ex in comp_agg["exercise_title"]]

    fig = go.Figure(go.Bar(
        x=comp_agg[comp_col],
        y=comp_agg["exercise_title"],
        orientation="h",
        marker_color=bar_colors,
        text=comp_agg[comp_col].round(1),
        textposition="outside",
        textfont=dict(size=10, color="#e8e8f0"),
    ))
    fig.update_layout(
        paper_bgcolor="#111118", plot_bgcolor="#111118",
        font=dict(family="DM Mono", color="#e8e8f0", size=12),
        margin=dict(l=12, r=40, t=40, b=12),
        title=dict(text="Exercise comparison", font=dict(size=14, color="#ccccdd"), x=0),
        xaxis=dict(gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=11)),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="#22222e", tickfont=dict(size=11)),
        height=max(280, len(comp_agg) * 26),
    )
    st.plotly_chart(fig, use_container_width=True)

comparison_section(selected_muscle, selected_exercise, window, working)
