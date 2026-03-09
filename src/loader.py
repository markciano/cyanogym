import re
import pandas as pd


def load_workouts(path: str = "data/workouts.csv") -> pd.DataFrame:
    """Load and clean the Hevy workouts CSV.

    Returns a DataFrame where each row is a set, with parsed dates
    and derived columns for date, session duration, week number,
    and mesocycle number.
    """
    df = pd.read_csv(path)

    # Parse timestamps
    fmt = "%d %b %Y, %H:%M"
    df["start_time"] = pd.to_datetime(df["start_time"], format=fmt)
    df["end_time"] = pd.to_datetime(df["end_time"], format=fmt)

    # Derive date (day only) and session duration in minutes
    df["date"] = df["start_time"].dt.date
    df["duration_min"] = (df["end_time"] - df["start_time"]).dt.total_seconds() / 60

    # Extract week and mesocycle numbers from session title
    # Pattern: wNmM (e.g. "Upper w1m2" → week=1, meso=2)
    # Pattern: wN only (e.g. "Upper w3" → week=3, meso=1)
    df["week_num"] = df["title"].str.extract(r"w(\d+)", expand=False).astype(float)
    meso = df["title"].str.extract(r"m(\d+)", expand=False)
    df["meso_num"] = meso.astype(float)
    # Sessions with wN but no mM suffix belong to meso 1
    df.loc[df["week_num"].notna() & df["meso_num"].isna(), "meso_num"] = 1.0

    return df

def load_workouts_from_buffer(buffer) -> pd.DataFrame:
    """Load and clean the Hevy workouts CSV from a file-like buffer."""
    df = pd.read_csv(buffer)

    fmt = "%d %b %Y, %H:%M"
    df["start_time"] = pd.to_datetime(df["start_time"], format=fmt)
    df["end_time"] = pd.to_datetime(df["end_time"], format=fmt)

    df["date"] = df["start_time"].dt.date
    df["duration_min"] = (df["end_time"] - df["start_time"]).dt.total_seconds() / 60

    df["week_num"] = df["title"].str.extract(r"w(\d+)", expand=False).astype(float)
    meso = df["title"].str.extract(r"m(\d+)", expand=False)
    df["meso_num"] = meso.astype(float)
    df.loc[df["week_num"].notna() & df["meso_num"].isna(), "meso_num"] = 1.0

    return df