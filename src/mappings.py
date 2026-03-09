import pandas as pd


def load_exercise_mapping(path: str = "data/mappings/ejercicios_mapping.csv") -> pd.DataFrame:
    """Load the exercise mapping CSV.

    Returns a DataFrame with columns:
    exercise_title, musculo_principal, patron
    """
    return pd.read_csv(path)


def load_secondary_muscles(path: str = "data/mappings/musculos_secundarios.csv") -> pd.DataFrame:
    """Load the secondary muscles mapping CSV.

    Returns a DataFrame with columns:
    exercise_title, musculo_secundario
    One row per secondary muscle per exercise.
    """
    return pd.read_csv(path)


def apply_mappings(df: pd.DataFrame,
                   mapping_path: str = "data/mappings/ejercicios_mapping.csv",
                   secondary_path: str = "data/mappings/musculos_secundarios.csv") -> pd.DataFrame:
    """Apply exercise and secondary muscle mappings to the workouts DataFrame.

    Adds columns: nombre_es, musculo_principal, patron, musculos_secundarios.
    Exercises not found in the mapping will have NaN in those columns.
    musculos_secundarios is a list of strings (empty list if none).
    """
    exercise_map = load_exercise_mapping(mapping_path)
    secondary_map = load_secondary_muscles(secondary_path)

    # Group secondary muscles into a list per exercise
    secondary_grouped = (
        secondary_map.groupby("exercise_title")["musculo_secundario"]
        .apply(list)
        .reset_index()
    )

    # Merge primary mapping
    df = df.merge(exercise_map, on="exercise_title", how="left")

    # Merge secondary muscles
    df = df.merge(secondary_grouped, on="exercise_title", how="left")

    # Replace NaN in musculos_secundarios with empty list
    df["musculo_secundario"] = df["musculo_secundario"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    return df
