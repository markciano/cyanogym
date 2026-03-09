from typing import Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

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
st.markdown('<div class="page-title">🏃 Cardio</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">running · pace · distance</div>', unsafe_allow_html=True)

# ── Extract cardio sessions: title contains "Run" ─────────────────────────────
cardio_raw = df_full[df_full["title"].str.contains("Run", case=False, na=False)].copy()

if cardio_raw.empty:
    st.info("No cardio sessions found. Sessions with 'Run' in the title will appear here.")
    st.stop()

# ── Period filter — 2 rows × 4 columns via CSS grid ──────────────────────────
window = st.radio(
    "Period", WINDOW_OPTIONS,
    index=WINDOW_OPTIONS.index(st.session_state.get("cardio_window", "All")),
    horizontal=True,
    key="cardio_window",
    label_visibility="collapsed",
)

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

# ── Aggregate cardio data per session ─────────────────────────────────────────
def aggregate_cardio(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate distance and duration per cardio session.

    Computes pace as total_duration_min / total_distance_km.
    Rows with zero distance are excluded from pace calculation.

    Returns a DataFrame sorted by start_time with columns:
    start_time, distance_km, duration_min, pace.
    """
    if df.empty:
        return pd.DataFrame(columns=["start_time", "distance_km", "duration_min", "pace"])

    agg = (
        df.groupby("start_time")
        .agg(
            distance_km=("distance_km",     "sum"),
            duration_min=("duration_seconds", lambda x: x.sum() / 60),
        )
        .reset_index()
        .sort_values("start_time")
    )

    agg["pace"] = agg.apply(
        lambda r: r["duration_min"] / r["distance_km"]
        if r["distance_km"] > 0 else None,
        axis=1,
    )
    return agg.reset_index(drop=True)


def compute_cardio_kpis(df_sessions: pd.DataFrame) -> dict:
    """Compute KPI values from an aggregated cardio sessions DataFrame."""
    if df_sessions.empty:
        return dict(runs=None, total_km=None, best_pace=None, avg_pace=None)

    valid_pace = df_sessions["pace"].dropna()
    return dict(
        runs=float(len(df_sessions)),
        total_km=float(df_sessions["distance_km"].sum()),
        best_pace=float(valid_pace.min()) if not valid_pace.empty else None,
        avg_pace=float(valid_pace.mean()) if not valid_pace.empty else None,
    )


# ── Apply time filter ─────────────────────────────────────────────────────────
cardio_curr_raw = apply_time_filter(cardio_raw, window)
cardio_prev_raw = get_previous_period_df(cardio_raw, window)

cardio      = aggregate_cardio(cardio_curr_raw)
cardio_prev = aggregate_cardio(cardio_prev_raw)

kpis_curr = compute_cardio_kpis(cardio)
kpis_prev = compute_cardio_kpis(cardio_prev)

# ── KPI helpers ───────────────────────────────────────────────────────────────
def fmt_delta(curr_val: Optional[float], prev_val: Optional[float],
              lower_is_better: bool = False) -> str:
    """Return an HTML delta badge. lower_is_better inverts the colour logic (pace)."""
    if curr_val is None or prev_val is None or prev_val == 0:
        return '<span class="kpi-delta-flat">—</span>'
    pct   = (curr_val - prev_val) / prev_val * 100
    up    = pct > 0
    arrow = "▲" if up else "▼"
    # For pace: going down is good (faster), so invert colour
    good  = (not up) if lower_is_better else up
    cls   = "kpi-delta-up" if good else "kpi-delta-down"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}%</span>'


def kpi_card(label: str, value: Optional[float], unit: str,
             delta_html: str, fmt: str = ".1f") -> str:
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
    ("Runs",       kpis_curr["runs"],       kpis_prev["runs"],       "",       ".0f", False),
    ("Distance",   kpis_curr["total_km"],   kpis_prev["total_km"],   "km",     ".1f", False),
    ("Best pace",  kpis_curr["best_pace"],  kpis_prev["best_pace"],  "min/km", ".2f", True),
    ("Avg pace",   kpis_curr["avg_pace"],   kpis_prev["avg_pace"],   "min/km", ".2f", True),
]
for col, (label, c, p, unit, fmt, lower) in zip([k1, k2, k3, k4], cards):
    with col:
        st.markdown(kpi_card(label, c, unit, fmt_delta(c, p, lower), fmt), unsafe_allow_html=True)

st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)

if cardio.empty:
    st.info("No cardio sessions in the selected period.")
    st.stop()

# ── Chart 1: distance (left) + pace (right, inverted) per session ─────────────
pace_ma = cardio["pace"].rolling(4, min_periods=1).mean()

fig1 = make_subplots(specs=[[{"secondary_y": True}]])

fig1.add_trace(go.Scatter(
    x=cardio["start_time"], y=cardio["distance_km"],
    name="Distance (km)",
    mode="lines+markers",
    line=dict(color="#5b8fff", width=2),
    marker=dict(size=5),
), secondary_y=False)

fig1.add_trace(go.Scatter(
    x=cardio["start_time"], y=cardio["pace"],
    name="Pace (min/km)",
    mode="lines+markers",
    line=dict(color="#ffd93d", width=2),
    marker=dict(size=5),
), secondary_y=True)

fig1.add_trace(go.Scatter(
    x=cardio["start_time"], y=pace_ma,
    name="Pace MA 4",
    mode="lines",
    line=dict(color="#ffd93d", width=1.5, dash="dot"),
    opacity=0.45,
    hoverinfo="skip",
    showlegend=False,
), secondary_y=True)

fig1.update_layout(
    paper_bgcolor="#111118", plot_bgcolor="#111118",
    font=dict(family="DM Mono", color="#e8e8f0", size=12),
    margin=dict(l=12, r=12, t=40, b=12),
    title=dict(text="Distance & pace per session", font=dict(size=14, color="#ccccdd"), x=0),
    legend=dict(
        orientation="h", x=1, xanchor="right", y=1.12,
        font=dict(size=11), bgcolor="rgba(0,0,0,0)",
    ),
    xaxis=dict(
        gridcolor="#22222e", linecolor="#22222e",
        tickfont=dict(size=10), tickformat="%d %b %y",
    ),
    yaxis=dict(
        title="Distance (km)", gridcolor="#22222e", linecolor="#22222e",
        tickfont=dict(size=11), title_font=dict(size=11, color="#5b8fff"),
    ),
    yaxis2=dict(
        title="Pace (min/km)", gridcolor="rgba(0,0,0,0)", linecolor="#22222e",
        tickfont=dict(size=11), title_font=dict(size=11, color="#ffd93d"),
        autorange="reversed",  # lower pace = faster = higher on chart
    ),
    height=280,
)
st.plotly_chart(fig1, use_container_width=True)

# ── Chart 2: distance bar per session ────────────────────────────────────────
fig2 = go.Figure(go.Bar(
    x=cardio["start_time"],
    y=cardio["distance_km"],
    marker_color="#5b8fff",
    text=cardio["distance_km"].round(1),
    textposition="outside",
    textfont=dict(size=9, color="#e8e8f0"),
))
fig2.update_layout(
    paper_bgcolor="#111118", plot_bgcolor="#111118",
    font=dict(family="DM Mono", color="#e8e8f0", size=12),
    margin=dict(l=12, r=12, t=40, b=12),
    title=dict(text="Distance per session (km)", font=dict(size=14, color="#ccccdd"), x=0),
    xaxis=dict(
        gridcolor="#22222e", linecolor="#22222e",
        tickfont=dict(size=10), tickformat="%d %b %y",
    ),
    yaxis=dict(
        gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=11),
        range=[0, cardio["distance_km"].max() * 1.2],
    ),
    height=200,
)
st.plotly_chart(fig2, use_container_width=True)

# ── Chart 3: distance accumulated by month ────────────────────────────────────
cardio["month"] = cardio["start_time"].dt.to_period("M").dt.start_time
monthly = cardio.groupby("month")["distance_km"].sum().reset_index()

fig3 = go.Figure(go.Bar(
    x=monthly["month"],
    y=monthly["distance_km"],
    marker_color="#4ecdc4",
    text=monthly["distance_km"].round(1),
    textposition="outside",
    textfont=dict(size=9, color="#e8e8f0"),
))
fig3.update_layout(
    paper_bgcolor="#111118", plot_bgcolor="#111118",
    font=dict(family="DM Mono", color="#e8e8f0", size=12),
    margin=dict(l=12, r=12, t=40, b=12),
    title=dict(text="Distance by month (km)", font=dict(size=14, color="#ccccdd"), x=0),
    xaxis=dict(
        gridcolor="#22222e", linecolor="#22222e",
        tickfont=dict(size=10), tickformat="%b %Y",
    ),
    yaxis=dict(
        gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=11),
        range=[0, monthly["distance_km"].max() * 1.2],
    ),
    height=200,
)
st.plotly_chart(fig3, use_container_width=True)
