from typing import Optional
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
/* Period radio — 2 rows × 4 columns grid */
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

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">📅 Sessions</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">weekly training load · volume · sets · reps</div>', unsafe_allow_html=True)

# ── Period filter — 2 rows × 4 columns via CSS grid ──────────────────────────
window = st.radio(
    "Period", WINDOW_OPTIONS,
    index=WINDOW_OPTIONS.index(st.session_state.get("ses_window", "All")),
    horizontal=True,
    key="ses_window",
    label_visibility="collapsed",
)

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

# ── Weekly aggregation helper ─────────────────────────────────────────────────
def build_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate all training metrics by ISO week from a time-filtered DataFrame.

    Uses all set types for session/duration counts; restricts to normal+dropset
    for sets, volume and reps (excludes warmup sets from load metrics).

    Returns a DataFrame with one row per week containing:
    week, sessions, duration_min, sets, volume_kg, reps, exercises.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["week", "sessions", "duration_min", "sets", "volume_kg", "reps", "exercises"]
        )

    df = df.copy()
    df["week"] = df["start_time"].dt.to_period("W").dt.start_time

    # Sessions and duration — derived from all rows (one duration per session)
    session_meta = df.groupby(["week", "start_time"])["duration_min"].first()
    weekly_sessions = session_meta.groupby(level="week").count()
    weekly_duration = session_meta.groupby(level="week").sum()

    # Sets, volume, reps — working sets only (warmup excluded)
    df_work = df[df["set_type"].isin(["normal", "dropset"])]
    weekly_sets      = df_work.groupby("week").size()
    weekly_volume    = df_work.groupby("week")["volume_per_set"].sum()
    weekly_reps      = df_work.groupby("week")["reps"].sum()
    weekly_exercises = df_work.groupby("week")["exercise_title"].nunique()

    all_weeks = sorted(
        set(weekly_sessions.index) |
        set(weekly_sets.index)
    )

    weekly = pd.DataFrame({"week": all_weeks})
    weekly["sessions"]     = weekly_sessions.reindex(all_weeks, fill_value=0).values
    weekly["duration_min"] = weekly_duration.reindex(all_weeks, fill_value=0).values
    weekly["sets"]         = weekly_sets.reindex(all_weeks, fill_value=0).values
    weekly["volume_kg"]    = weekly_volume.reindex(all_weeks, fill_value=0).values
    weekly["reps"]         = weekly_reps.reindex(all_weeks, fill_value=0).values
    weekly["exercises"]    = weekly_exercises.reindex(all_weeks, fill_value=0).values

    return weekly.sort_values("week").reset_index(drop=True)


# ── KPI scalar helpers ────────────────────────────────────────────────────────
def kpi_sessions(df: pd.DataFrame) -> Optional[float]:
    """Total unique sessions in the period."""
    if df.empty:
        return None
    return float(df["start_time"].nunique())


def kpi_avg_weekly(df: pd.DataFrame, col: str) -> Optional[float]:
    """Average value of `col` per week across the period."""
    weekly = build_weekly(df)
    if weekly.empty:
        return None
    return float(weekly[col].mean())


# ── Compute KPIs for current and previous period ──────────────────────────────
df_curr = apply_time_filter(df_full, window)
df_prev = get_previous_period_df(df_full, window)

kpi_values = {
    "sessions":     (kpi_sessions(df_curr),                           kpi_sessions(df_prev)),
    "duration_min": (kpi_avg_weekly(df_curr, "duration_min"),          kpi_avg_weekly(df_prev, "duration_min")),
    "volume_kg":    (kpi_avg_weekly(df_curr, "volume_kg"),             kpi_avg_weekly(df_prev, "volume_kg")),
    "sets":         (kpi_avg_weekly(df_curr, "sets"),                  kpi_avg_weekly(df_prev, "sets")),
}

# ── KPI card renderers ────────────────────────────────────────────────────────
def fmt_delta(curr_val, prev_val):
    if curr_val is None or prev_val is None or prev_val == 0:
        return '<span class="kpi-delta-flat">—</span>'
    pct   = (curr_val - prev_val) / prev_val * 100
    arrow = "▲" if pct > 0 else "▼"
    cls   = "kpi-delta-up" if pct > 0 else "kpi-delta-down"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}%</span>'


def kpi_card(label, value, unit, delta_html, fmt=".0f"):
    val_str = f"{value:{fmt}}" if value is not None else "—"
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div><span class="kpi-value">{val_str}</span><span class="kpi-unit">{unit}</span></div>
        <div style="margin-top:6px">{delta_html}</div>
    </div>"""


# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
cards = [
    ("Sessions",          kpi_values["sessions"],     "",     ".0f"),
    ("Avg duration / wk", kpi_values["duration_min"], "min",  ".0f"),
    ("Avg volume / wk",   kpi_values["volume_kg"],    "kg",   ".0f"),
    ("Avg sets / wk",     kpi_values["sets"],         "sets", ".1f"),
]
for col, (label, (curr_v, prev_v), unit, fmt) in zip([k1, k2, k3, k4], cards):
    with col:
        st.markdown(kpi_card(label, curr_v, unit, fmt_delta(curr_v, prev_v), fmt), unsafe_allow_html=True)

st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)

# ── Weekly data for charts ────────────────────────────────────────────────────
weekly = build_weekly(df_curr)

# ── Chart helper — line + 4-week moving average ───────────────────────────────
def weekly_chart(weeks, values, title: str, color: str) -> go.Figure:
    """Line chart with a 4-week moving average overlay.

    The moving average is rendered as a dashed line in the same color
    at reduced opacity to avoid visual noise.
    """
    ma = pd.Series(values, dtype=float).rolling(4, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weeks, y=values,
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=4),
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=weeks, y=ma,
        mode="lines",
        line=dict(color=color, width=1.5, dash="dot"),
        opacity=0.45,
        showlegend=False,
        hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="#111118", plot_bgcolor="#111118",
        font=dict(family="DM Mono", color="#e8e8f0", size=12),
        margin=dict(l=12, r=12, t=40, b=12),
        title=dict(text=title, font=dict(size=14, color="#ccccdd"), x=0),
        xaxis=dict(
            gridcolor="#22222e", linecolor="#22222e",
            tickfont=dict(size=10), tickformat="%d %b %y",
        ),
        yaxis=dict(gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=11)),
        height=200,
    )
    return fig


# ── 5 stacked charts ──────────────────────────────────────────────────────────
if not weekly.empty:
    charts = [
        (weekly["duration_min"], "Duration / week (min)",       "#5b8fff"),
        (weekly["sets"],         "Sets / week",                 "#4ecdc4"),
        (weekly["volume_kg"],    "Volume / week (kg)",          "#ffd93d"),
        (weekly["reps"],         "Reps / week",                 "#ff6b6b"),
        (weekly["exercises"],    "Distinct exercises / week",   "#c084fc"),
    ]
    for values, title, color in charts:
        st.plotly_chart(
            weekly_chart(weekly["week"], values, title, color),
            use_container_width=True,
        )
else:
    st.info("No training data for the selected period.")
