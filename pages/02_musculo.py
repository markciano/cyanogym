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

EXCLUDED = {"Cardio", "Mobility"}
working = df_full[
    df_full["set_type"].isin(["normal", "dropset"]) &
    ~df_full["musculo_principal"].isin(EXCLUDED)
].copy()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">💪 Muscle</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">weekly volume · effective sets · muscle comparison</div>', unsafe_allow_html=True)

# ── Period filter — 2 rows × 4 columns via CSS grid ──────────────────────────
window = st.radio(
    "Period", WINDOW_OPTIONS,
    index=WINDOW_OPTIONS.index(st.session_state.get("mu_window", "All")),
    horizontal=True,
    key="mu_window",
    label_visibility="collapsed",
)

st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

# ── Muscle selector ───────────────────────────────────────────────────────────
muscles_available = sorted(working["musculo_principal"].dropna().unique())

selected_muscle = st.selectbox(
    "Muscle group", muscles_available,
    key="mu_muscle",
    label_visibility="visible",
)

# ── Metric helpers ────────────────────────────────────────────────────────────
def _add_week(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'week' column (Monday timestamp) based on start_time."""
    d = df.copy()
    d["week"] = d["start_time"].dt.to_period("W").dt.start_time
    return d


def compute_metrics(df_time: pd.DataFrame, muscle: str) -> dict:
    """Compute KPI values for a given muscle from a time-filtered DataFrame.

    Counts direct sets (musculo_principal == muscle) and indirect sets
    (muscle in musculo_secundario). Effective sets = direct × 1.0 + indirect × 0.5.
    Volume includes both primary and secondary exercises at full value.

    Returns a dict with keys: weekly_sets, weekly_vol, distinct_ex, sessions.
    """
    df_p = df_time[df_time["musculo_principal"] == muscle]
    df_s = df_time[df_time["musculo_secundario"].apply(lambda x: muscle in x)]

    if df_p.empty and df_s.empty:
        return dict(weekly_sets=None, weekly_vol=None, distinct_ex=0, sessions=0)

    if not df_p.empty:
        df_p = _add_week(df_p)
    if not df_s.empty:
        df_s = _add_week(df_s)

    direct_w   = df_p.groupby("week").size()           if not df_p.empty else pd.Series(dtype=float)
    indirect_w = df_s.groupby("week").size()           if not df_s.empty else pd.Series(dtype=float)
    vol_p_w    = df_p.groupby("week")["volume_per_set"].sum() if not df_p.empty else pd.Series(dtype=float)
    vol_s_w    = df_s.groupby("week")["volume_per_set"].sum() if not df_s.empty else pd.Series(dtype=float)

    all_weeks = sorted(set(direct_w.index) | set(indirect_w.index))

    if all_weeks:
        eff_w = (
            direct_w.reindex(all_weeks, fill_value=0) * 1.0 +
            indirect_w.reindex(all_weeks, fill_value=0) * 0.5
        )
        vol_w = (
            vol_p_w.reindex(all_weeks, fill_value=0) +
            vol_s_w.reindex(all_weeks, fill_value=0)
        )
        weekly_sets = float(eff_w.mean())
        weekly_vol  = float(vol_w.mean())
    else:
        weekly_sets = None
        weekly_vol  = None

    ex_set = set()
    if not df_p.empty:
        ex_set.update(df_p["exercise_title"].unique())
    if not df_s.empty:
        ex_set.update(df_s["exercise_title"].unique())

    sess_set = set()
    if not df_p.empty:
        sess_set.update(df_p["start_time"].unique())
    if not df_s.empty:
        sess_set.update(df_s["start_time"].unique())

    return dict(
        weekly_sets=weekly_sets,
        weekly_vol=weekly_vol,
        distinct_ex=len(ex_set),
        sessions=len(sess_set),
    )


def build_weekly_data(df_time: pd.DataFrame, muscle: str) -> pd.DataFrame:
    """Build a per-week DataFrame with volume and effective sets for a muscle.

    Returns DataFrame with columns: week, volume, effective_sets.
    """
    df_p = df_time[df_time["musculo_principal"] == muscle]
    df_s = df_time[df_time["musculo_secundario"].apply(lambda x: muscle in x)]

    if df_p.empty and df_s.empty:
        return pd.DataFrame(columns=["week", "volume", "effective_sets"])

    if not df_p.empty:
        df_p = _add_week(df_p)
    if not df_s.empty:
        df_s = _add_week(df_s)

    direct_w   = df_p.groupby("week").size()                  if not df_p.empty else pd.Series(dtype=float)
    indirect_w = df_s.groupby("week").size()                  if not df_s.empty else pd.Series(dtype=float)
    vol_p_w    = df_p.groupby("week")["volume_per_set"].sum() if not df_p.empty else pd.Series(dtype=float)
    vol_s_w    = df_s.groupby("week")["volume_per_set"].sum() if not df_s.empty else pd.Series(dtype=float)

    all_weeks = sorted(set(direct_w.index) | set(indirect_w.index))
    if not all_weeks:
        return pd.DataFrame(columns=["week", "volume", "effective_sets"])

    weekly = pd.DataFrame({"week": all_weeks})
    weekly["volume"] = (
        vol_p_w.reindex(all_weeks, fill_value=0).values +
        vol_s_w.reindex(all_weeks, fill_value=0).values
    )
    weekly["effective_sets"] = (
        direct_w.reindex(all_weeks, fill_value=0).values * 1.0 +
        indirect_w.reindex(all_weeks, fill_value=0).values * 0.5
    )
    return weekly.sort_values("week").reset_index(drop=True)

# ── Compute current + previous metrics ───────────────────────────────────────
df_time      = apply_time_filter(working, window)
df_prev_time = get_previous_period_df(working, window)

curr = compute_metrics(df_time, selected_muscle)
prev = compute_metrics(df_prev_time, selected_muscle)

# ── KPI helpers ───────────────────────────────────────────────────────────────
def fmt_delta(curr_val, prev_val):
    if curr_val is None or prev_val is None or prev_val == 0:
        return '<span class="kpi-delta-flat">—</span>'
    pct   = (curr_val - prev_val) / prev_val * 100
    arrow = "▲" if pct > 0 else "▼"
    cls   = "kpi-delta-up" if pct > 0 else "kpi-delta-down"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}%</span>'


def kpi_card(label, value, unit, delta_html, fmt=".1f"):
    if value is None:
        val_str = "—"
    elif fmt == "d":
        val_str = str(int(value))
    else:
        val_str = f"{value:{fmt}}"
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
    ("Weekly sets",     curr["weekly_sets"], prev["weekly_sets"], "sets/wk", ".1f"),
    ("Weekly volume",   curr["weekly_vol"],  prev["weekly_vol"],  "kg/wk",   ".0f"),
    ("Exercises",       curr["distinct_ex"], prev["distinct_ex"], "",        "d"),
    ("Sessions",        curr["sessions"],    prev["sessions"],    "",        "d"),
]
for col, (label, c, p, unit, fmt) in zip([k1, k2, k3, k4], kpis):
    with col:
        st.markdown(kpi_card(label, c, unit, fmt_delta(c, p), fmt), unsafe_allow_html=True)

st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

# ── Progress chart — weekly volume (bars) + effective sets (line) ─────────────
weekly = build_weekly_data(df_time, selected_muscle)

if not weekly.empty:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=weekly["week"],
        y=weekly["volume"],
        name="Volume (kg)",
        marker_color="#5b8fff",
        opacity=0.85,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=weekly["week"],
        y=weekly["effective_sets"],
        name="Effective sets",
        mode="lines+markers",
        line=dict(color="#ffd93d", width=2),
        marker=dict(size=5),
    ), secondary_y=True)

    fig.update_layout(
        paper_bgcolor="#111118", plot_bgcolor="#111118",
        font=dict(family="DM Mono", color="#e8e8f0", size=12),
        margin=dict(l=12, r=12, t=40, b=12),
        title=dict(text="Weekly volume & effective sets", font=dict(size=14, color="#ccccdd"), x=0),
        legend=dict(
            orientation="h", x=1, xanchor="right", y=1.12,
            font=dict(size=11), bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=11)),
        yaxis=dict(
            title="Volume (kg)", gridcolor="#22222e", linecolor="#22222e",
            tickfont=dict(size=11), title_font=dict(size=11, color="#5b8fff"),
        ),
        yaxis2=dict(
            title="Effective sets", gridcolor="rgba(0,0,0,0)", linecolor="#22222e",
            tickfont=dict(size=11), title_font=dict(size=11, color="#ffd93d"),
        ),
        height=300,
        barmode="overlay",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for the selected muscle and period.")

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

# ── Comparison charts — direct sets and effective sets per muscle ─────────────
def _horizontal_bar(comp_df, x_col, title, selected_muscle):
    """Render a horizontal bar chart comparing all muscles for a given metric."""
    comp_sorted = comp_df.sort_values(x_col, ascending=True)
    bar_colors = ["#5b8fff" if m == selected_muscle else "#22222e"
                  for m in comp_sorted["musculo"]]
    fig = go.Figure(go.Bar(
        x=comp_sorted[x_col],
        y=comp_sorted["musculo"],
        orientation="h",
        marker_color=bar_colors,
        text=comp_sorted[x_col].round(1),
        textposition="outside",
        textfont=dict(size=10, color="#e8e8f0"),
    ))
    fig.update_layout(
        paper_bgcolor="#111118", plot_bgcolor="#111118",
        font=dict(family="DM Mono", color="#e8e8f0", size=12),
        margin=dict(l=12, r=48, t=40, b=12),
        title=dict(text=title, font=dict(size=14, color="#ccccdd"), x=0),
        xaxis=dict(gridcolor="#22222e", linecolor="#22222e", tickfont=dict(size=11)),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor="#22222e", tickfont=dict(size=11)),
        height=max(240, len(comp_sorted) * 24),
    )
    st.plotly_chart(fig, use_container_width=True)


df_comp = apply_time_filter(working, window)
df_comp = _add_week(df_comp)

# Direct sets per muscle per week → mean across weeks
direct_weekly = (
    df_comp.groupby(["musculo_principal", "week"])
    .size()
    .groupby(level="musculo_principal")
    .mean()
    .reset_index(name="direct_sets")
    .rename(columns={"musculo_principal": "musculo"})
)

# Indirect sets per muscle per week → mean across weeks
sec_rows = df_comp[df_comp["musculo_secundario"].apply(len) > 0].copy()
if not sec_rows.empty:
    sec_exploded = sec_rows.explode("musculo_secundario")
    indirect_weekly = (
        sec_exploded.groupby(["musculo_secundario", "week"])
        .size()
        .groupby(level="musculo_secundario")
        .mean()
        .reset_index(name="indirect_sets")
        .rename(columns={"musculo_secundario": "musculo"})
    )
else:
    indirect_weekly = pd.DataFrame(columns=["musculo", "indirect_sets"])

# Merge and compute weekly averages
comp_df = pd.merge(direct_weekly, indirect_weekly, on="musculo", how="outer").fillna(0)
comp_df["effective_sets"] = comp_df["direct_sets"] * 1.0 + comp_df["indirect_sets"] * 0.5

# Filter to muscles that appear as principal in this page
comp_df = comp_df[comp_df["musculo"].isin(working["musculo_principal"].unique())]

if not comp_df.empty:
    _horizontal_bar(comp_df, "direct_sets",    "Direct sets / week by muscle",    selected_muscle)
    _horizontal_bar(comp_df, "effective_sets", "Effective sets / week by muscle", selected_muscle)
