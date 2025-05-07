import pandas as pd
from pandas.errors import ParserError
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires I/O
# ─────────────────────────────────────────────────────────────────────────────
def load_csv(path: str | Path) -> pd.DataFrame:
    """
    Charger un fichier CSV horodaté (robuste).

    Paramètres :
        - path : str | Path
            Chemin du fichier à lire.

    Retour :
        - pandas.DataFrame
            Données indexées par un `DatetimeIndex`.

    Lève :
        - FileNotFoundError si le fichier est absent.
        - ParserError / ValueError si le format n’est pas reconnu.

    Le lecteur tente trois stratégies :
        1. Colonne explicite « timestamp » (`parse_dates=['timestamp']`).
        2. Première colonne = index date (`index_col=0`, `parse_dates=True`).
        3. Lecture brute puis conversion manuelle.
    """

    # ── 1. Colonne 'timestamp' explicite ────────────────────────────────────
    try:
        return pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp").dropna()
    except (ParserError, ValueError, KeyError):
        pass

    # ── 2. Première colonne = index ─────────────────────────────────────────
    try:
        return pd.read_csv(path, index_col=0, parse_dates=True).dropna()
    except (ParserError, ValueError):
        pass

    # ── 3. Fallback : lecture brute + conversion ────────────────────────────
    try:
        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        df.dropna(inplace=True)
        return df
    except (KeyError, ParserError, ValueError) as err:
        raise ValueError(f"Impossible de lire le CSV « {path} » : format non reconnu") from err

def add_soil_humidity(df: pd.DataFrame, v_sec: int, v_eau: int) -> pd.DataFrame:
    """
    Ajouter la colonne « humidity_soil_percent » (calcul en place).

    Paramètres :
        - df : pandas.DataFrame
            Doit contenir une colonne ``soil_moisture`` (en volts).
        - v_sec : int
            Valeur mesurée à sec (calibrage).
        - v_eau : int
            Valeur mesurée dans l’eau (calibrage).

    Retour :
        - pandas.DataFrame
            Le même objet, pour chaînage éventuel.
    """

    # Conversion tension → pourcentage d’humidité :
    #  - 0 % si soil_moisture == v_sec  (sol sec)
    #  - 100 % si soil_moisture == v_eau (sol saturé)
    # Interpolation linéaire entre ces deux bornes.
    df["humidity_soil_percent"] = ((v_sec - df["soil_moisture"]) / (v_sec - v_eau) * 100)
    return df