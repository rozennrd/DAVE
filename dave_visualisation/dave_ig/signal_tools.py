from functools import lru_cache
from typing import Any
import numpy as np
import pandas as pd
from scipy import signal as sig

from .config import ROLLING_WINDOW, BASE_DATE

# ─────────────────────────────────────────────────────────────────────────────
# Utilitaires statistiques, filtrage et manipulation d’index
# ─────────────────────────────────────────────────────────────────────────────
def rolling_stats(series: pd.Series, window: str = ROLLING_WINDOW) -> tuple[pd.Series, pd.Series]:
    """
    Calculer la moyenne et l’écart‑type glissants d’une série.

    Paramètres :
        - series : pandas.Series
            Série numérique indexée en temps.
        - window : str, optional
            Fenêtre Pandas (ex. ``"10min"``). Par défaut : ``ROLLING_WINDOW``.

    Retour :
        - tuple(pandas.Series, pandas.Series)
            Moyenne glissante puis écart‑type glissant.
    """

    rolling_mean = series.rolling(window, min_periods=1).mean() # calcul de la moyenne glissante
    rolling_std  = series.rolling(window, min_periods=1).std()  # calcul de l'écart-type glissant
    return rolling_mean, rolling_std

def stats_str(series: pd.Series) -> str:
    """
    Formater quelques statistiques descriptives (4 décimales).

    Paramètres :
        - series : pandas.Series
            Série de nombres.

    Retour :
        - str
            Chaîne « σ=…  IQR=…  Méd=… ».
    """

    q1, median, q3 = np.percentile(series, [25, 50, 75])    # calcul du 1er quartile, médiane et 3ème quartile
    iqr = q3 - q1                                              # calcul écart inter-quartile

    return f"σ={series.std():.4f}  IQR={iqr:.4f}  Méd={median:.4f}"

def annotate_extremes(ax, y: pd.Series, *, color: str) -> None:
    """
    Annoter les valeurs min. et max. d’une courbe sur un axe Matplotlib.

    Paramètres :
        - ax : matplotlib.axes.Axes
            Axe sur lequel écrire les annotations.
        - y : pandas.Series
            Série tracée.
        - color : str
            Couleur du texte (généralement celle de la courbe).
    """

    # Récupérer l'y max et min de la série
    idx_max = y.idxmax()
    idx_min = y.idxmin()

    # Ajouter les anotations :
    # max
    ax.annotate(f"{y.max():.4f}", xy=(idx_max, y.max()), xytext=(0, 5), textcoords="offset points",
                ha="center", va="bottom", fontsize=8, color=color)

    # min
    ax.annotate(f"{y.min():.4f}", xy=(idx_min, y.min()),xytext=(0, -10), textcoords="offset points",
                ha="center", va="top",   fontsize=8, color=color)

def split_by_day(df: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.DataFrame]]:
    """
    Découper un `DataFrame` journalier et réaligner chaque sous‑série sur 2000‑01‑01.

    Paramètres :
        - df : pandas.DataFrame
            Indexé par un `DatetimeIndex`.

    Retour :
        - list(tuple(Timestamp, DataFrame))
            Liste : (date d’origine, sous‑DataFrame réindexé sur `BASE_DATE`).
    """

    # Liste des tuples (date d’origine, DataFrame de la journée réindexé sur BASE_DATE)
    groups: list[tuple[pd.Timestamp, pd.DataFrame]] = []

    # Parcourir chaque journée distincte et regrouper les données correspondantes
    # Pour chaque journée unique, extraire les données et les préparer pour un affichage 24h
    for day_key, grp in df.groupby(df.index.normalize()):
        # Convertir explicitement la clé pour éviter un avertissement de type.
        day: pd.Timestamp = pd.Timestamp(day_key)

        # Copier le sous‑DataFrame pour éviter toute modification de l’original
        shifted = grp.copy()

        # Conserver uniquement l’heure en déplaçant l’index sur BASE_DATE.
        shifted.index = BASE_DATE + (shifted.index - day)
        groups.append((day, shifted))
    return groups

@lru_cache(maxsize=32)
def _butter_coeff(cutoff_hz: float, fs: float, order: int = 4) -> tuple[Any, Any]:
    """
    Calculer les coefficients d’un filtre passe‑bas de Butterworth.

    Notes :
    Le résultat est mis en cache (lru_cache) car les mêmes couples
    (cutoff_hz, fs, order) sont appelés à répétition.
    """

    nyq = 0.5 * fs               # Fréquence de Nyquist
    wn  = cutoff_hz / nyq        # Fréquence normalisée (entre 0 et 1)

    if wn >= 1:
        raise ValueError("La fréquence de coupure doit être < fs/2.")

    return sig.butter(order, wn, btype="low")

def lowpass_filter(series: pd.Series, cutoff_hz: float, order: int = 4) -> pd.Series:
    """
    Appliquer un filtre passe‑bas Butterworth à une série.

    Paramètres :
        - series : pandas.Series
            Signal d’entrée.
        - cutoff_hz : float
            Fréquence de coupure (Hz). Si `None`, la série d’origine est renvoyée.
        - order : int, optional
            Ordre du filtre. Par défaut : 4.

    Retour :
        - pandas.Series
            Série filtrée (index conservé).

    Notes :
    La fonction saute le filtrage si la série est trop courte pour `scipy.signal.filtfilt`
    (condition ``len(x) < 3 * max(len(a), len(b))``).
    """

    if cutoff_hz is None:
        return series   # Aucun filtrage demandé

    # Déterminer la fréquence d’échantillonnage (Hz)
    dt = series.index.to_series().diff().median().total_seconds()
    fs = 1.0 / dt
    b, a = _butter_coeff(cutoff_hz, fs, order=order)

    # Condition minimale pour filtfilt : éviter ValueError
    if len(series) < 3 * max(len(a), len(b)):
        return series   # Série trop courte → retour brut

    filtered = sig.filtfilt(b, a, series.values, method="pad") # Filtrage passe-bas sans déphasage
    return pd.Series(filtered, index=series.index)