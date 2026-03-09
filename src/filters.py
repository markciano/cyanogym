import pandas as pd


WINDOW_OPTIONS = ["All", "1 year", "YTD", "6 months", "3 months", "1 month", "2 weeks", "1 week"]


def apply_time_filter(df: pd.DataFrame, window: str,
                      date_col: str = "start_time") -> pd.DataFrame:
    """Filter the workouts DataFrame to a given time window.

    Args:
        df: Workouts DataFrame with a datetime column.
        window: One of the WINDOW_OPTIONS strings.
        date_col: Name of the datetime column to filter on.

    Returns:
        Filtered DataFrame. Returns the full DataFrame if window is "All".
    """
    today = pd.Timestamp.now().normalize()

    if window == "All":
        return df

    if window == "1 year":
        cutoff = today - pd.DateOffset(years=1)
    elif window == "YTD":
        cutoff = pd.Timestamp(today.year, 1, 1)
    elif window == "6 months":
        cutoff = today - pd.DateOffset(months=6)
    elif window == "3 months":
        cutoff = today - pd.DateOffset(months=3)
    elif window == "1 month":
        cutoff = today - pd.DateOffset(months=1)
    elif window == "2 weeks":
        cutoff = today - pd.Timedelta(weeks=2)
    elif window == "1 week":
        cutoff = today - pd.Timedelta(weeks=1)
    else:
        raise ValueError(f"Unknown window: '{window}'. Valid options: {WINDOW_OPTIONS}")

    return df[df[date_col] >= cutoff]


def get_comparison_period(window: str) -> str:
    """Return the label for the comparison period used in KPI delta calculations.

    Args:
        window: Active time window string.

    Returns:
        Label describing the comparison period (e.g. "vs previous week").
    """
    mapping = {
        "All": "vs start",
        "1 year": "vs previous year",
        "YTD": "vs previous year",
        "6 months": "vs previous 6 months",
        "3 months": "vs previous 3 months",
        "1 month": "vs previous month",
        "2 weeks": "vs previous 2 weeks",
        "1 week": "vs previous week",
    }
    return mapping.get(window, "vs previous period")


def get_previous_period_df(df: pd.DataFrame, window: str,
                           date_col: str = "start_time") -> pd.DataFrame:
    """Return the DataFrame slice for the previous equivalent period.

    Used to compute KPI deltas (e.g. 1RM this month vs 1RM last month).

    Args:
        df: Full workouts DataFrame.
        window: Active time window string.
        date_col: Name of the datetime column to filter on.

    Returns:
        Filtered DataFrame for the previous period.
    """
    today = pd.Timestamp.now().normalize()

    if window == "All":
        # Compare last half vs first half
        mid = df[date_col].min() + (df[date_col].max() - df[date_col].min()) / 2
        return df[df[date_col] < mid]

    if window == "1 year":
        start = today - pd.DateOffset(years=2)
        end = today - pd.DateOffset(years=1)
    elif window == "YTD":
        start = pd.Timestamp(today.year - 1, 1, 1)
        end = pd.Timestamp(today.year, 1, 1)
    elif window == "6 months":
        start = today - pd.DateOffset(months=12)
        end = today - pd.DateOffset(months=6)
    elif window == "3 months":
        start = today - pd.DateOffset(months=6)
        end = today - pd.DateOffset(months=3)
    elif window == "1 month":
        start = today - pd.DateOffset(months=2)
        end = today - pd.DateOffset(months=1)
    elif window == "2 weeks":
        start = today - pd.Timedelta(weeks=4)
        end = today - pd.Timedelta(weeks=2)
    elif window == "1 week":
        start = today - pd.Timedelta(weeks=2)
        end = today - pd.Timedelta(weeks=1)
    else:
        raise ValueError(f"Unknown window: '{window}'. Valid options: {WINDOW_OPTIONS}")

    return df[(df[date_col] >= start) & (df[date_col] < end)]
