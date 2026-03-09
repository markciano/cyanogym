import numpy as np
import pandas as pd


def epley_rm(weight: float, reps: float, target_rm: int = 1) -> float:
    """Estimate a target RM using the Epley formula.

    Formula: 1RM = weight * (1 + reps / 30)
    For target RM > 1: weight = 1RM / (1 + target_rm / 30)

    Args:
        weight: Weight lifted in kg.
        reps: Number of repetitions performed.
        target_rm: Target RM to estimate (1 to 10).

    Returns:
        Estimated weight for the target RM.
    """
    one_rm = weight * (1 + reps / 30)
    if target_rm == 1:
        return one_rm
    return one_rm / (1 + target_rm / 30)


def add_set_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-set calculated columns to the workouts DataFrame.

    Adds:
    - volume_per_set: weight_kg * reps (NaN for cardio sets)
    - estimated_1rm: Epley 1RM estimate per set
    - estimated_Nrm: Epley RM estimates for N=2 to 10

    Warmup sets are included in the DataFrame but should be excluded
    from aggregations downstream.

    Args:
        df: Workouts DataFrame with weight_kg and reps columns.

    Returns:
        DataFrame with additional metric columns.
    """
    df = df.copy()

    df["volume_per_set"] = df["weight_kg"] * df["reps"]

    for n in range(1, 11):
        col = f"estimated_{n}rm"
        df[col] = np.where(
            df["weight_kg"].notna() & df["reps"].notna(),
            df.apply(lambda row: epley_rm(row["weight_kg"], row["reps"], n), axis=1),
            np.nan
        )

    return df


def compute_fatigue(df: pd.DataFrame, reference_date: pd.Timestamp,
                    window_days: int = 7) -> pd.DataFrame:
    """Compute effective sets per muscle for a given reference date.

    Looks back `window_days` days from reference_date (exclusive of reference_date).
    Effective sets = direct sets * 1.0 + indirect sets * 0.5

    Only counts normal and dropset set types (warmup excluded).

    Args:
        df: Workouts DataFrame with mappings applied and set metrics added.
        reference_date: The date to compute fatigue for.
        window_days: Number of days to look back (default 7).

    Returns:
        DataFrame with columns: musculo, series_directas, series_indirectas,
        series_efectivas, nivel (low/optimal/high).
    """
    start = reference_date - pd.Timedelta(days=window_days)
    mask = (
        (df["start_time"] > start) &
        (df["start_time"] < reference_date) &
        (df["set_type"].isin(["normal", "dropset"]))
    )
    window_df = df[mask].copy()

    if window_df.empty:
        return pd.DataFrame(columns=[
            "musculo", "series_directas", "series_indirectas",
            "series_efectivas", "nivel"
        ])

    # Direct sets: counted by musculo_principal
    direct = (
        window_df.groupby("musculo_principal")
        .size()
        .reset_index(name="series_directas")
        .rename(columns={"musculo_principal": "musculo"})
    )

    # Indirect sets: expand musculo_secundario lists and count
    secondary_rows = window_df[window_df["musculo_secundario"].apply(len) > 0].copy()
    if not secondary_rows.empty:
        secondary_exploded = secondary_rows.explode("musculo_secundario")
        indirect = (
            secondary_exploded.groupby("musculo_secundario")
            .size()
            .reset_index(name="series_indirectas")
            .rename(columns={"musculo_secundario": "musculo"})
        )
    else:
        indirect = pd.DataFrame(columns=["musculo", "series_indirectas"])

    # Merge direct and indirect
    fatigue = pd.merge(direct, indirect, on="musculo", how="outer").fillna(0)
    fatigue["series_efectivas"] = (
        fatigue["series_directas"] * 1.0 +
        fatigue["series_indirectas"] * 0.5
    )

    # Assign fatigue level
    def _nivel(x):
        if x < 6:
            return "low"
        elif x <= 16:
            return "optimal"
        else:
            return "high"

    fatigue["nivel"] = fatigue["series_efectivas"].apply(_nivel)
    fatigue = fatigue.sort_values("series_efectivas", ascending=False).reset_index(drop=True)

    return fatigue
