"""
                        DAVE IG V2.7.2
Visualisation interactive des mesures électrophysiologiques végétales
---------------------------------------------------------------------

CONVENTIONS COMMENTAIRES
========================
• Tout commentaire et toute docstring sont rédigés en **français**.
• **Docstrings** : format *Numpy*
  - Première ligne : phrase concise à l’infinitif, majuscule initiale.
  - Sections autorisées : « Paramètres », « Retour », « Notes », « Exemples ».
  - Corps ≤ 8 lignes (lisibilité).
• **Commentaires bloc** :
  - Précédés d’un séparateur « # ─── titre ─── ».
  - Expliquent la logique métier ou une opération complexe.
• **Commentaires ligne** :
  - Phrase brève (verbe à l’infinitif), majuscule après « # ».
  - Pas de doublon avec le nom de la variable/fonction.
• Éviter les commentaires évidents ou redondants (« # boucle », « # format axes »).
• Largeur ≤ 80 caractères pour tous les commentaires.
"""

# ──────────────────────────────────────────────────────────────────────────────
# Bibliothèques et constantes
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

# ── Bibliothèque standard ────────────────────────────────────────────────────
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

# ── Pile scientifique ────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
from pandas.errors import ParserError
from scipy import signal as sig

# ── Matplotlib ───────────────────────────────────────────────────────────────
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
from matplotlib.colors import to_hex

# ── Tkinter ──────────────────────────────────────────────────────────────────
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ── Constantes interface et traitement ───────────────────────────────────────
BASE_DATE = pd.Timestamp(2000, 1, 1)  # date « origine » pour les courbes 24h
DEFAULT_WIDTH = 180  # largeur menu (px)
HOVER_WIDTH = 240  # largeur menu au survol
DEFAULT_FONT = ("Arial", 11)  # style police menu par défaut
HOVER_FONT = ("Arial", 15)  # style police menu lors du hover

ROLLING_WINDOW = "10min"  # fenêtre moyenne/σ
RESAMPLE_24H = "10s"  # pas de rééchantillonage pour 24h
DEFAULT_CUTOFF_HZ = 0.1  # fréquence de coupure par défaut (Hz)
DEFAULT_V_SEC = 480  # valeur « sécheresse » (capteur sol)
DEFAULT_V_EAU = 234  # valeur « eau »

# Correspondance des courbes superposables (overlay) --------------------------
OVERLAY_MAP = {
    "Température": ("temp_degC", "Température (°C)"),
    "Humidité air": ("humidity_air_percent", "Humidité air (%)"),
    "Humidité sol": ("humidity_soil_percent", "Humidité sol (%)"),
    "Luminosité baseline": ("light_intensity_baseline", "Luminosité"),
    "Luminosité stress": ("light_intensity_stressor", "Luminosité"),
    "Tension terre": ("chan4_voltage_V", "Voltage Terre (mV)"),
}


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

    rolling_mean = series.rolling(window, min_periods=1).mean()  # calcul de la moyenne glissante
    rolling_std = series.rolling(window, min_periods=1).std()  # calcul de l'écart-type glissant
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

    q1, median, q3 = np.percentile(series, [25, 50, 75])  # calcul du 1er quartile, médiane et 3ème quartile
    iqr = q3 - q1  # calcul écart inter-quartile

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
    ax.annotate(f"{y.min():.4f}", xy=(idx_min, y.min()), xytext=(0, -10), textcoords="offset points",
                ha="center", va="top", fontsize=8, color=color)


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

    nyq = 0.5 * fs  # Fréquence de Nyquist
    wn = cutoff_hz / nyq  # Fréquence normalisée (entre 0 et 1)

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
        return series  # Aucun filtrage demandé

    # Déterminer la fréquence d’échantillonnage (Hz)
    dt = series.index.to_series().diff().median().total_seconds()
    fs = 1.0 / dt
    b, a = _butter_coeff(cutoff_hz, fs, order=order)

    # Condition minimale pour filtfilt : éviter ValueError
    if len(series) < 3 * max(len(a), len(b)):
        return series  # Série trop courte → retour brut

    filtered = sig.filtfilt(b, a, series.values, method="pad")  # Filtrage passe-bas sans déphasage
    return pd.Series(filtered, index=series.index)


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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers Matplotlib (figures et axes)
# ─────────────────────────────────────────────────────────────────────────────
def new_figure(title_center: str, title_left: str | None = None):
    """
    Créer une figure 3 × 2 avec `constrained_layout`.

    Paramètres :
        - title_center : str
            Titre principal (centré).
        - title_left : str | None
            Sous‑titre aligné à gauche (optionnel).

    Retour :
        - tuple(matplotlib.figure.Figure, matplotlib.gridspec.GridSpec)
    """

    # Création de la figure et ajout du titre principal (centré)
    fig = plt.figure(figsize=(12, 8), dpi=150, constrained_layout=True)
    fig.suptitle(title_center, fontsize=16, ha="center")

    # Ajout du second titre (à gauche)
    if title_left:
        fig.text(0.01, 0.99, title_left, fontsize=13,
                 va="top", ha="left", weight="bold")

    # Sépartion de la figure en 3 lignes et 2 colonnes
    gs = gridspec.GridSpec(3, 2, figure=fig, width_ratios=[0.5, 0.5])
    return fig, gs


def format_axes(ax, *, xlabel: str = "", ylabel: str = "", xmin=None, xmax=None) -> None:
    """
    Mettre en forme un axe : grille, labels et dates.

    Paramètres :
        - ax : matplotlib.axes.Axes
            Axe à configurer.
        - xlabel / ylabel : str
            Libellés d’axes (vides par défaut).
        - xmin / xmax : pandas.Timestamp | float | None
            Limites X facultatives.
    """

    # Ajout label en X si != ""
    if xlabel:
        ax.set_xlabel(xlabel)

    # Ajout label en Y si != ""
    if ylabel:
        ax.set_ylabel(ylabel)

    # Ajout cradillage en pointillé
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.margins(x=0)

    # Si une plage est spécifiée → fixer les bornes de l’axe X
    if xmin is not None and xmax is not None:
        ax.set_xlim(xmin, xmax)

    # Format de date court « JJ/MM HHhMM »
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %Hh%M"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")


def draw_sigma(ax, mean: pd.Series, std: pd.Series, *, color: str) -> None:
    """
    Tracer ±1σ autour d’une moyenne glissante, en pointillé.

    Paramètres :
        - ax : matplotlib.axes.Axes
            Axe cible.
        - mean / std : pandas.Series
            Moyenne et écart‑type glissants (index identiques).
        - color : str
            Couleur de la courbe principale, réutilisée en pointillé.
    """

    ax.plot(mean + std, color=color, linestyle=":", linewidth=1)
    ax.plot(mean - std, color=color, linestyle=":", linewidth=1)


def get_plot_titles(x_min: pd.Timestamp, x_max: pd.Timestamp, mode: str) -> tuple[str, str]:
    """
    Générer les deux titres d’un graphique selon le mode d’affichage.

    Paramètres :
        - x_min / x_max : pandas.Timestamp
            Bornes temporelles de l’intervalle affiché.
        - mode : str
            « classic », « 24h », « mean24h » ou « supermean24h ».

    Retour :
        - tuple(str, str)
            (titre_gauche, titre_centré).
    """

    mode_names = {
        "classic": "Affichage classique",
        "24h": "Affichage 24 h",
        "mean24h": "Moyenne 24 h",
        "supermean24h": "Moyenne canaux 24 h",
    }
    title_left = mode_names.get(mode, mode)

    # -------------------- Durée lisible , par ex : « 3 jours 4h 30min » --------------------
    duration = x_max - x_min
    days = duration.days
    hours, rem = divmod(duration.seconds, 3600)
    minutes = rem // 60
    parts: list[str] = []
    if days:
        parts.append(f"{days} jour{'s' if days > 1 else ''}")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}min")

    span_string = " ".join(parts)

    title_center = f"Données du {x_min.strftime('%d/%m/%Y')} "f"au {x_max.strftime('%d/%m/%Y')} ({span_string})"
    return title_left, title_center


# ─────────────────────────────────────────────────────────────────────────────
# Plots des tensions des plantes et de la terre
# ─────────────────────────────────────────────────────────────────────────────
def plot_voltage(df: pd.DataFrame, gs, fig, x_min: pd.Timestamp, x_max: pd.Timestamp,
                 *, cutoff_hz: float | None = None, show_sigma: bool = True):
    """
    Vue « classique » : Chan 1‑3 empilés + Chan 4 (terre).

    Paramètres :
        - df : pandas.DataFrame
            Données brutes ou filtrées.
        - gs / fig : GridSpec, Figure
            Grille et figure cibles.
        - x_min / x_max : pandas.Timestamp
            Limites X pour `format_axes`.
        - cutoff_hz : float | None
            Fréquence de coupure passe‑bas ; `None` = pas de filtrage.
        - show_sigma : bool
            Afficher ±1 σ glissant.

    Retour :
        - matplotlib.axes.Axes
            Axe principal (Chan 1‑3) – sert de référence à d’autres tracés.
    """

    # ── Canal Plante (Chan 1-3) ──────────────────────────────────────────────
    # Crée l’axe principal (canaux 1 à 3 superposés) en haut de la colonne gauche
    # Liste des colonnes correspondant aux canaux d’entrée (fils sur plante)
    ax_voltage = fig.add_subplot(gs[:2, 0])
    channels = ["chan1_voltage_V", "chan2_voltage_V", "chan3_voltage_V"]

    # Parcours des canaux pour les tracer sur le même axe
    for idx, chan in enumerate(channels, start=1):
        # Filtrage passe-bas si demandé, puis conversion en millivolts
        data = (lowpass_filter(df[chan], cutoff_hz) if cutoff_hz else df[chan]) * 1000

        # Trace la courbe de tension pour le canal courant
        line = ax_voltage.plot(data, linewidth=1.5, label=f"Channel {idx}\n{stats_str(data)}")[0]

        # Ajoute les annotations du min et max sur la courbe
        annotate_extremes(ax_voltage, data, color=line.get_color())

        # Tracer ±σ si demandé
        if show_sigma:
            mean, std = rolling_stats(data, ROLLING_WINDOW)
            draw_sigma(ax_voltage, mean, std, color=line.get_color())

    # Mise en forme des axes : limites X, labels, grille, format date
    format_axes(ax_voltage, ylabel="Voltage (mV)", xmin=x_min, xmax=x_max)

    # ── Canal Terre (Chan 4) ─────────────────────────────────────────────────
    # Ce canal est tracé en dessous, sur un axe séparé
    ax_terre = fig.add_subplot(gs[2, 0], sharex=ax_voltage)

    # Même logique que ci-dessus : filtrage éventuel + conversion mV
    terre_mv = (lowpass_filter(df["chan4_voltage_V"], cutoff_hz) if cutoff_hz else df["chan4_voltage_V"]) * 1000
    line = ax_terre.plot(terre_mv, color="brown", linewidth=1.5, label=f"Channel 4 (Terre)\n{stats_str(terre_mv)}")[0]

    # Annotation des extrêmes
    annotate_extremes(ax_terre, terre_mv, color=line.get_color())

    # Tracer ±σ si demandé
    if show_sigma:
        mean_t, std_t = rolling_stats(terre_mv, ROLLING_WINDOW)
        draw_sigma(ax_terre, mean_t, std_t, color=line.get_color())

    # Mise en forme de l’axe X + légende
    format_axes(ax_terre, xlabel="Temps", ylabel="Voltage (mV)", xmin=x_min, xmax=x_max)
    ax_terre.legend(fontsize=8, framealpha=0.9)

    return ax_voltage


def plot_voltage_24h(df: pd.DataFrame, gs, fig, *, show_sigma: bool = True):
    """
    Vue 24 h : superposition par jour — moyenne(Chan 1‑3) + Chan 4 (terre).

    Chaque journée est tracée avec une couleur distincte (colormap tab10),
    réalignée sur `BASE_DATE` pour ne conserver que l’heure dans l’axe X.

    Paramètres :
        - df : pandas.DataFrame
            Données temporelles sur plusieurs jours.
        - gs / fig : GridSpec, Figure
            Grille et figure cibles.
        - show_sigma : bool
            Afficher ±1 σ glissant.

    Retour :
        - matplotlib.axes.Axes
            Axe principal (Chan 1‑3) – utilisé pour superposition.
    """

    # ── Préparation des axes (même logique que plot_voltage) ─────────────────
    ax_voltage = fig.add_subplot(gs[:2, 0])
    ax_terre = fig.add_subplot(gs[2, 0], sharex=ax_voltage)

    # Découper le DataFrame en sous-groupes par jour et réaligner sur BASE_DATE
    daily_groups = split_by_day(df)
    cmap = plt.get_cmap("tab10", len(daily_groups))  # Palette de couleurs

    # Parcours des canaux pour les tracer sur le même axe
    for i, (_day, g) in enumerate(daily_groups):
        color = to_hex(cmap(i))  # Convertit RGBA → "#rrggbb" (attendu par les stubs)

        # ── Moyenne des Chan 1-3 (plante) ────────────────────────────────────
        g["voltage_mean"] = g[["chan1_voltage_V", "chan2_voltage_V", "chan3_voltage_V"]].mean(axis=1) * 1000
        ax_voltage.plot(g["voltage_mean"], color=color, linewidth=1.4)

        # Tracer ±σ si demandé
        if show_sigma:
            mean, std = rolling_stats(g["voltage_mean"], ROLLING_WINDOW)
            draw_sigma(ax_voltage, mean, std, color=color)

        # ── Canal Terre ──────────────────────────────────────────────────────
        terre_mv = g["chan4_voltage_V"] * 1000
        ax_terre.plot(terre_mv, color=color, linewidth=1.2)

        # Tracer ±σ si demandé
        if show_sigma:
            mean_t, std_t = rolling_stats(terre_mv, ROLLING_WINDOW)
            draw_sigma(ax_terre, mean_t, std_t, color=color)

    # ── Mise en forme des axes ───────────────────────────────────────────────
    xmin, xmax = BASE_DATE, BASE_DATE + timedelta(hours=23, minutes=59)
    format_axes(ax_voltage, ylabel="Voltage moyen (mV)", xmin=xmin, xmax=xmax)
    format_axes(ax_terre, xlabel="Heure", ylabel="Voltage (mV)", xmin=xmin, xmax=xmax)
    ax_voltage.legend(title="Jour", fontsize=8, framealpha=0.9)

    return ax_voltage


def plot_voltage_mean24h(df: pd.DataFrame, gs, fig, *, show_sigma: bool = True):
    """
    Moyenne 24 h individuelle : Chan 1‑3 empilés + Chan 4 (terre).

    Les données sont réalignées sur `BASE_DATE` (on ne garde que l’heure)
    puis moyennées toutes les 10 secondes (``RESAMPLE_24H``).

    Paramètres :
        - df : pandas.DataFrame
            Données horodatées.
        - gs / fig : GridSpec, Figure
            Grille et figure matplotlib.
        - show_sigma : bool
            Afficher ±1 σ glissant.

    Retour :
        - matplotlib.axes.Axes
            Axe principal (Chan 1‑3).
    """

    # Réaligner sur BASE_DATE pour superposition horaire
    df = df.copy()
    df.index = BASE_DATE + (df.index - df.index.normalize())

    # Moyenne par pas de 10 s
    df_resampled = df.resample(RESAMPLE_24H).mean()

    # ── Préparation des axes (même logique que plot_voltage) ─────────────────
    ax_voltage = fig.add_subplot(gs[:2, 0])

    # Parcours des canaux pour les tracer sur le même axe
    for i, chan in enumerate(["chan1_voltage_V", "chan2_voltage_V", "chan3_voltage_V"]):
        data_mv = df_resampled[chan] * 1000
        line = ax_voltage.plot(data_mv, linewidth=1.5, label=f"Channel {i + 1} (moy.)")[0]

        # Tracer ±σ si demandé
        if show_sigma:
            mean, std = rolling_stats(data_mv, ROLLING_WINDOW)
            draw_sigma(ax_voltage, mean, std, color=line.get_color())

    # ── Mise en forme ────────────────────────────────────────────────────────
    xt_min, xt_max = BASE_DATE, BASE_DATE + timedelta(hours=23, minutes=59)
    format_axes(ax_voltage, ylabel="Voltage (mV)", xmin=xt_min, xmax=xt_max)
    ax_voltage.set_title("Voltage – Moyenne sur 24 h")
    ax_voltage.legend(fontsize=8)

    # ── Chan 4 (terre) ───────────────────────────────────────────────────────
    ax_terre = fig.add_subplot(gs[2, 0], sharex=ax_voltage)
    terre_mv = df_resampled["chan4_voltage_V"] * 1000
    line = ax_terre.plot(terre_mv, color="brown", linewidth=1.5, label="Channel 4 (Terre)")[0]

    # Tracer ±σ si demandé
    if show_sigma:
        mean_t, std_t = rolling_stats(terre_mv, ROLLING_WINDOW)
        draw_sigma(ax_terre, mean_t, std_t, color=line.get_color())

    # Mettre en forme les axes
    format_axes(ax_terre, xlabel="Heure", ylabel="Voltage (mV)", xmin=xt_min, xmax=xt_max)
    ax_terre.legend(fontsize=8)

    return ax_voltage


def plot_voltage_mean_chan24h(df: pd.DataFrame, gs, fig, *, show_sigma: bool = True):
    """
    Moyenne(Chan 1‑3) + Chan 4 (terre) – vue 24 h superposée.

    Les 3 canaux plante sont moyennés en une seule courbe.
    Chan 4 (terre) est affiché séparément.

    Paramètres :
        - df : pandas.DataFrame
            Données horodatées.
        - gs / fig : GridSpec, Figure
            Grille et figure matplotlib.
        - show_sigma : bool
            Afficher ±1 σ glissant.

    Retour :
        - matplotlib.axes.Axes
            Axe principal (Moyenne Chan 1‑3).
    """

    # Réaligner sur BASE_DATE pour superposition horaire
    df = df.copy()
    df.index = BASE_DATE + (df.index - df.index.normalize())
    df_res = df.resample(RESAMPLE_24H).mean()

    # ── Moyenne Chan 1-3 ─────────────────────────────────────────────────────
    ax_volt = fig.add_subplot(gs[:2, 0])
    chan_mean = df_res[["chan1_voltage_V", "chan2_voltage_V", "chan3_voltage_V"]].mean(axis=1) * 1000
    line = ax_volt.plot(chan_mean, label="Moyenne Chan 1‑3", linewidth=1.5)[0]

    # Tracer ±σ si demandé
    if show_sigma:
        mean, std = rolling_stats(chan_mean, ROLLING_WINDOW)
        draw_sigma(ax_volt, mean, std, color=line.get_color())

    # ── Chan 4 (Terre) ───────────────────────────────────────────────────────
    ax_terre = fig.add_subplot(gs[2, 0], sharex=ax_volt)
    terre_mv = df_res["chan4_voltage_V"] * 1000
    line_t = ax_terre.plot(terre_mv, color="brown", linewidth=1.5, label="Channel 4 (Terre)")[0]

    # Tracer ±σ si demandé
    if show_sigma:
        mean_t, std_t = rolling_stats(terre_mv, ROLLING_WINDOW)
        draw_sigma(ax_terre, mean_t, std_t, color=line_t.get_color())

    # ── Mise en forme ────────────────────────────────────────────────────────
    xt_min, xt_max = BASE_DATE, BASE_DATE + timedelta(hours=23, minutes=59)
    format_axes(ax_volt, ylabel="Voltage moy. (mV)", xmin=xt_min, xmax=xt_max)
    format_axes(ax_terre, xlabel="Heure", ylabel="Voltage (mV)", xmin=xt_min, xmax=xt_max)
    ax_volt.legend(fontsize=8)
    ax_terre.legend(fontsize=8)

    return ax_volt


# ─────────────────────────────────────────────────────────────────────────────
# Plots capteurs environnementaux
# ─────────────────────────────────────────────────────────────────────────────
def plot_sensor_data(df: pd.DataFrame, gs, ax_shared, fig, x_min: pd.Timestamp,
                     x_max: pd.Timestamp, v_sec: int, v_eau: int) -> None:
    """
    Tracer température, humidités (air + sol) et luminosité (baseline / stress).

    Paramètres :
        - df : pandas.DataFrame
            Données brutes filtrées par plage temporelle.
        - gs : matplotlib.gridspec.GridSpec
            Grille 3 × 2 partagée.
        - ax_shared : matplotlib.axes.Axes
            Axe des voltages pour synchroniser l’axe X.
        - fig : matplotlib.figure.Figure
            Figure parente.
        - x_min / x_max : pandas.Timestamp
            Limites temporelles pour `format_axes`.
        - v_sec / v_eau : int
            Tensions de référence pour le calcul d’humidité du sol.
    """

    # ── Température ──────────────────────────────────────────────────────────
    ax_temp = fig.add_subplot(gs[0, 1], sharex=ax_shared)
    line = ax_temp.plot(df["temp_degC"], color="m", linewidth=1.5, label=stats_str(df["temp_degC"]))[0]
    annotate_extremes(ax_temp, df["temp_degC"], color=line.get_color())
    format_axes(ax_temp, ylabel="Température (°C)", xmin=x_min, xmax=x_max)
    ax_temp.legend(title="Température", fontsize=8, framealpha=0.9)

    # ── Humidités (air + sol) ────────────────────────────────────────────────
    ax_hum = fig.add_subplot(gs[1, 1], sharex=ax_shared)

    # Convertir la mesure brut « soil_moisture » → % humidité du sol
    df["humidity_soil_percent"] = ((v_sec - df["soil_moisture"]) / (v_sec - v_eau) * 100)

    # Air
    line_air = ax_hum.plot(df["humidity_air_percent"], color="darkturquoise", linewidth=1.5,
                           label=f"Air\n{stats_str(df['humidity_air_percent'])}")[0]

    annotate_extremes(ax_hum, df["humidity_air_percent"], color=line_air.get_color())

    # Sol
    line_soil = ax_hum.plot(df["humidity_soil_percent"], color="royalblue", linewidth=1.5,
                            label=f"Sol\n{stats_str(df['humidity_soil_percent'])}")[0]

    annotate_extremes(ax_hum, df["humidity_soil_percent"], color=line_soil.get_color())

    format_axes(ax_hum, ylabel="Humidité (%)", xmin=x_min, xmax=x_max)
    ax_hum.legend(fontsize=8, framealpha=0.9)

    # ── Luminosité ───────────────────────────────────────────────────────────
    ax_light = fig.add_subplot(gs[2, 1], sharex=ax_shared)
    line_base = ax_light.plot(df["light_intensity_baseline"], color="gold", linewidth=1.5,
                              label=f"Baseline\n{stats_str(df['light_intensity_baseline'])}")[0]

    annotate_extremes(ax_light, df["light_intensity_baseline"], color=line_base.get_color())

    line_stress = ax_light.plot(df["light_intensity_stressor"], color="black", linewidth=1.5,
                                label=f"Stress\n{stats_str(df['light_intensity_stressor'])}")[0]

    annotate_extremes(ax_light, df["light_intensity_stressor"], color=line_stress.get_color())

    format_axes(ax_light, xlabel="Temps", ylabel="Intensité lumineuse", xmin=x_min, xmax=x_max)
    ax_light.legend(fontsize=8, framealpha=0.9)


def plot_sensor_data_24h(df: pd.DataFrame, gs, ax_shared, fig) -> None:
    """
    Superposer les capteurs sur 24 h, couleur par journée (vue « 24 h »).

    Paramètres :
        - df : pandas.DataFrame
            Données brutes.
        - gs, ax_shared, fig : objets Matplotlib analogues à `plot_sensor_data`.
    """

    daily_groups = split_by_day(df)
    cmap = plt.get_cmap("tab10", len(daily_groups))

    # Température -------------------------------------------------------------
    ax_temp = fig.add_subplot(gs[0, 1], sharex=ax_shared)
    for i, (_, g) in enumerate(daily_groups):
        ax_temp.plot(g["temp_degC"], color=cmap(i), linewidth=1.4)

    format_axes(ax_temp, ylabel="Température (°C)", xmin=BASE_DATE, xmax=BASE_DATE + timedelta(hours=23, minutes=59))
    ax_temp.set_title("Température", fontsize=9)

    # Humidités ---------------------------------------------------------------
    ax_hum = fig.add_subplot(gs[1, 1], sharex=ax_shared)
    for i, (_, g) in enumerate(daily_groups):
        ax_hum.plot(g["humidity_air_percent"], color=cmap(i), linewidth=1.4, alpha=0.6)
        ax_hum.plot(g["humidity_soil_percent"], color=cmap(i), linewidth=1.4)

    format_axes(ax_hum, ylabel="Humidité (%)", xmin=BASE_DATE, xmax=BASE_DATE + timedelta(hours=23, minutes=59))
    ax_hum.set_title("Air (α 0,6)  &  Sol", fontsize=9)

    # Luminosité --------------------------------------------------------------
    ax_light = fig.add_subplot(gs[2, 1], sharex=ax_shared)
    for i, (_, g) in enumerate(daily_groups):
        ax_light.plot(g["light_intensity_baseline"], color=cmap(i), linewidth=1.4, alpha=0.6)

    format_axes(ax_light, xlabel="Heure", ylabel="Intensité lumineuse", xmin=BASE_DATE,
                xmax=BASE_DATE + timedelta(hours=23, minutes=59))
    ax_light.set_title("Baseline (α 0,6)", fontsize=9)


def plot_sensor_data_mean24h(df: pd.DataFrame, gs, ax_shared, fig, v_sec: int, v_eau: int) -> None:
    """
    Afficher la moyenne 24 h des capteurs (un cycle typique).

    Paramètres :
        - df : pandas.DataFrame
            Données brutes multi‑jours.
        - Les autres paramètres sont analogues aux fonctions précédentes.
    """

    df = df.copy()
    df["humidity_soil_percent"] = ((v_sec - df["soil_moisture"]) / (v_sec - v_eau) * 100)

    # Aligner toutes les journées sur BASE_DATE puis rééchantillonner à 10 s
    df.index = BASE_DATE + (df.index - df.index.normalize())
    df_resampled = df.resample(RESAMPLE_24H).mean()

    # Température -------------------------------------------------------------
    ax_temp = fig.add_subplot(gs[0, 1], sharex=ax_shared)
    ax_temp.plot(df_resampled["temp_degC"], color="magenta", linewidth=1.5)
    format_axes(ax_temp, ylabel="Température (°C)", xmin=BASE_DATE, xmax=BASE_DATE + timedelta(hours=23, minutes=59))
    ax_temp.set_title("Température moyenne")

    # Humidité ----------------------------------------------------------------
    ax_hum = fig.add_subplot(gs[1, 1], sharex=ax_shared)
    ax_hum.plot(df_resampled["humidity_air_percent"], color="turquoise", linewidth=1.5, label="Air")
    ax_hum.plot(df_resampled["humidity_soil_percent"], color="royalblue", linewidth=1.5, label="Sol")
    format_axes(ax_hum, ylabel="Humidité (%)", xmin=BASE_DATE, xmax=BASE_DATE + timedelta(hours=23, minutes=59))
    ax_hum.set_title("Humidité moyenne")
    ax_hum.legend(fontsize=8)

    # Luminosité --------------------------------------------------------------
    ax_light = fig.add_subplot(gs[2, 1], sharex=ax_shared)
    ax_light.plot(df_resampled["light_intensity_baseline"], color="gold", linewidth=1.5, label="Baseline")
    ax_light.plot(df_resampled["light_intensity_stressor"], color="black", linewidth=1.5, label="Stress")
    format_axes(ax_light, xlabel="Heure", ylabel="Luminosité", xmin=BASE_DATE,
                xmax=BASE_DATE + timedelta(hours=23, minutes=59))
    ax_light.set_title("Luminosité moyenne")
    ax_light.legend(fontsize=8)


# ─────────────────────────────────────────────────────────────────────────────
# Courbes additionnelles (tendance / overlay)
# ─────────────────────────────────────────────────────────────────────────────
def add_trend_line(ax, df_src: pd.DataFrame, mode: str, cutoff_hz: float | None) -> None:
    """
    Ajouter la courbe « Tendance » (moyenne des canaux 1‑3).

    Paramètres :
        - ax : matplotlib.axes.Axes
            Axe principal des voltages.
        - df_src : pandas.DataFrame
            Données déjà filtrées/alignées.
        - mode : str
            Identifiant de la vue courante (« classic », « 24h », …).
        - cutoff_hz : float | None
            Fréquence de coupure appliquée ou `None`.
    """

    if mode == "supermean24h":  # Pas pertinent dans cette vue
        return

    chans = ["chan1_voltage_V", "chan2_voltage_V", "chan3_voltage_V"]
    df_work = df_src.copy()

    # Filtrer chaque canal si un cutoff est appliqué
    if cutoff_hz is not None:
        for c in chans:
            df_work[c] = lowpass_filter(df_work[c], cutoff_hz)

    # Construction de la série « trend » selon le mode ────────────────────────
    if mode == "classic":
        trend = df_work[chans].mean(axis=1) * 1000
    elif mode in {"24h", "mean24h"}:
        df_tmp = df_work.copy()
        df_tmp.index = BASE_DATE + (df_tmp.index - df_tmp.index.normalize())
        if mode != "24h":
            df_tmp = df_tmp.resample(RESAMPLE_24H).mean()
        trend = df_tmp[chans].mean(axis=1) * 1000
    else:  # mode inattendu → rien à faire
        return

    ax.plot(trend, color="#999999", alpha=0.4, linewidth=0.8, label="Tendance")


def add_overlay_curve(ax, df_src: pd.DataFrame, overlay_var, mode: str) -> None:
    """
    Superposer une courbe secondaire (température, humidité, etc.) sur l’axe droit.

    Paramètres :
        - ax : matplotlib.axes.Axes
            Axe principal des voltages.
        - df_src : pandas.DataFrame
            Données d’origine (non modifiées).
        - overlay_var : tk.StringVar
            Choix utilisateur (« Température », « Humidité sol », …).
        - mode : str
            Vue courante, pour savoir s’il faut ré‑aligner sur 24 h.
    """

    choice = overlay_var.get()
    if choice == "None":
        return

    col, ylab = OVERLAY_MAP[choice]
    y = df_src[col].copy()

    # Aligner l’index sur BASE_DATE si la vue est en 24 h ─────────────────────
    if mode in {"24h", "mean24h", "supermean24h"}:
        y.index = BASE_DATE + (y.index - y.index.normalize())
        if mode != "24h":
            y = y.resample(RESAMPLE_24H).mean()

    # Conversion spéciale tension Terre : volts → millivolts
    if choice == "Tension terre":
        y *= 1000

    ax2 = ax.twinx()
    ax2.plot(y, color="firebrick", linewidth=1, alpha=0.30, label=choice, zorder=0)
    ax2.set_ylabel(ylab, color="firebrick")
    ax2.tick_params(axis="y", colors="firebrick")

    # Combiner les légendes ───────────────────────────────────────────────────
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=8, framealpha=0.9)


# ─────────────────────────────────────────────────────────────────────────────
# Boîte de dialogue Tkinter : plage de dates, filtrage, Vsec / Veau
# ─────────────────────────────────────────────────────────────────────────────
class GlobalConfigDialog(simpledialog.Dialog):
    """
    Fenêtre modale permettant de définir les paramètres globaux d’affichage.

    Paramètres :
        - parent : tk.Tk | tk.Toplevel
            Fenêtre parente.
        - min_date / max_date : pandas.Timestamp
            Bornes disponibles dans le jeu de données.
        - default_cutoff : float
            Fréquence de coupure pré‑remplie (Hz).
        - default_vsec / default_veau : int
            Tensions de référence pour le calcul d’humidité du sol.

    Retour (attribué à `self.result`) :
        tuple(
            pandas.Timestamp,  # date début 00:00:00
            pandas.Timestamp,  # date fin   23:59:59
            float | None,      # cutoff_hz  (None si « Pas de filtre »)
            int,               # V_sec
            int                # V_eau
        )
    """

    # init ────────────────────────────────────────────────────────────────────
    def __init__(self, parent, min_date, max_date, default_cutoff: float = DEFAULT_CUTOFF_HZ,
                 default_vsec: int = DEFAULT_V_SEC, default_veau: int = DEFAULT_V_EAU, ):

        # Widgets d’entrée (initialisés dans body)
        self.e_start = self.e_end = self.e_cut = None
        self.no_filter_var = None
        self.e_vsec = self.e_veau = None

        # Résultat final
        self.result = None

        # Contexte
        self.min_date = min_date
        self.max_date = max_date
        self.def_cutoff = default_cutoff
        self.def_vsec = default_vsec
        self.def_veau = default_veau

        super().__init__(parent, title="Paramètres d’affichage")

    # body ────────────────────────────────────────────────────────────────────
    def body(self, master):
        """Construire le corps de la boîte de dialogue (Tk callback)."""

        fmt = "%d/%m/%Y"

        # --- Sélection des dates -------------------------------------------
        tk.Label(master, text="Date début (dd/mm/yyyy)").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        self.e_start = tk.Entry(master, width=12)
        self.e_start.insert(0, self.min_date.strftime(fmt))
        self.e_start.grid(row=0, column=1, padx=5)

        tk.Label(master, text="Date fin (dd/mm/yyyy)").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        self.e_end = tk.Entry(master, width=12)
        self.e_end.insert(0, self.max_date.strftime(fmt))
        self.e_end.grid(row=1, column=1, padx=5)

        # --- Fréquence de coupure ------------------------------------------
        tk.Label(master, text="Fréquence coupure (Hz)").grid(row=2, column=0, sticky="w", padx=5, pady=4)
        self.e_cut = tk.Entry(master, width=12)
        self.e_cut.insert(0, str(self.def_cutoff))
        self.e_cut.grid(row=2, column=1, padx=5)

        # Option « Pas de filtre »
        self.no_filter_var = tk.BooleanVar(value=False)
        tk.Checkbutton(master, text="Pas de filtre passe-bas", variable=self.no_filter_var,
                       command=self._toggle_filter).grid(row=2, column=2, padx=5)

        # --- V_sec / V_eau --------------------------------------------------
        tk.Label(master, text="V_sec").grid(row=3, column=0, sticky="w", padx=5, pady=4)
        self.e_vsec = tk.Entry(master, width=12)
        self.e_vsec.insert(0, str(self.def_vsec))
        self.e_vsec.grid(row=3, column=1, padx=5)

        tk.Label(master, text="V_eau").grid(row=4, column=0, sticky="w", padx=5, pady=4)
        self.e_veau = tk.Entry(master, width=12)
        self.e_veau.insert(0, str(self.def_veau))
        self.e_veau.grid(row=4, column=1, padx=5)

        # Info plage valide
        info = f"(données du {self.min_date.strftime(fmt)} " f"au {self.max_date.strftime(fmt)})"
        tk.Label(master, text=info, fg="blue").grid(row=5, column=0, columnspan=3, pady=(4, 0))

        return self.e_start  # Focus initial

    # callbacks internes ──────────────────────────────────────────────────────
    def _toggle_filter(self) -> None:
        """Activer/désactiver l’entrée fréquence selon la case à cocher."""

        state = "disabled" if self.no_filter_var.get() else "normal"
        self.e_cut.configure(state=state)

    # validate ────────────────────────────────────────────────────────────────
    def validate(self) -> bool:
        """Valider les champs ; afficher un message d’erreur si besoin."""

        try:
            # -- Vérification des dates -------------------------------------
            d0_str, d1_str = self.e_start.get().strip(), self.e_end.get().strip()
            d0 = datetime.strptime(d0_str, "%d/%m/%Y") if d0_str else self.min_date
            d1 = datetime.strptime(d1_str, "%d/%m/%Y") if d1_str else self.max_date
            if d0 > d1:
                raise ValueError("La date de début doit précéder la date de fin.")

            # Tolérance d’un jour (saisie sans heure)
            tol = timedelta(days=1)
            if d0 < self.min_date - tol or d1 > self.max_date + tol:
                self._out_of_range_warning()
                return False

            # -- Fréquence de coupure --------------------------------------
            if not self.no_filter_var.get():
                freq = float(self.e_cut.get())
                if freq <= 0:
                    raise ValueError("La fréquence doit être > 0 Hz.")

            # -- V_sec / V_eau ---------------------------------------------
            _ = int(self.e_vsec.get())
            _ = int(self.e_veau.get())

        except Exception as err:
            messagebox.showwarning("Entrée invalide", str(err), parent=self)
            return False

        return True  # OK

    # avertissement dates ─────────────────────────────────────────────────────
    def _out_of_range_warning(self) -> None:
        """Afficher une fenêtre d’alerte si les dates dépassent la plage."""

        warn = tk.Toplevel(self)
        warn.title("Dates hors plage")
        warn.grab_set()
        warn.transient(self)

        tk.Label(warn, text=(f"Les dates doivent être comprises entre "
                             f"{self.min_date.strftime('%d/%m/%Y')} et "
                             f"{self.max_date.strftime('%d/%m/%Y')}."),
                 font=("Arial", 11), padx=10, pady=10, wraplength=320).pack()

        def use_all():
            self.e_start.delete(0, tk.END)
            self.e_end.delete(0, tk.END)
            warn.destroy()

        def retry():
            warn.destroy()

        btnf = tk.Frame(warn);
        btnf.pack(pady=10)
        tk.Button(btnf, text="Utiliser toutes les données", width=22, command=use_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btnf, text="Corriger les dates", width=18, command=retry).pack(side=tk.RIGHT, padx=5)

        self.wait_window(warn)

    # apply ───────────────────────────────────────────────────────────────────
    def apply(self) -> None:
        """Construire le tuple résultat et le stocker dans `self.result`."""

        # Dates bornées 00:00 / 23:59:59
        d0 = datetime.strptime(self.e_start.get(), "%d/%m/%Y")
        d1 = datetime.strptime(self.e_end.get(), "%d/%m/%Y")
        d0 = pd.Timestamp(d0.year, d0.month, d0.day, 0, 0, 0)
        d1 = pd.Timestamp(d1.year, d1.month, d1.day, 23, 59, 59)

        cutoff = None if self.no_filter_var.get() else float(self.e_cut.get())

        self.result = (d0, d1, cutoff, int(self.e_vsec.get()), int(self.e_veau.get()))


# ─────────────────────────────────────────────────────────────────────────────
# Fenêtre principale Tkinter (menu, callbacks, canvas)
# ─────────────────────────────────────────────────────────────────────────────
def start_gui(df: pd.DataFrame, *, csv_path: str, v_sec: int, v_eau: int, cutoff_hz: float | None) -> None:
    """
    Construire l’interface Tk et lancer la boucle principale.

    Paramètres :
        - df : pandas.DataFrame
            Données filtrées après la boîte de dialogue initiale.
        - csv_path : str
            Chemin du fichier actuellement chargé (affiché dans le menu).
        - v_sec / v_eau : int
            Références pour l’humidité du sol.
        - cutoff_hz : float | None
            Fréquence de coupure appliquée au chargement (ou `None`).
    """

    # ── Fenêtre racine ───────────────────────────────────────────────────────
    root = tk.Tk()
    root.title("Visualisation interactive")
    root.state("zoomed")

    def on_closing():
        print("Fermeture de l’interface par l’utilisateur.")
        root.destroy()
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # ── Menu latéral gauche ──────────────────────────────────────────────────
    frame_menu = tk.Frame(root, width=DEFAULT_WIDTH, bg="lightgray")
    frame_menu.pack(side=tk.LEFT, fill=tk.Y)
    frame_menu.pack_propagate(False)

    # Effet « hover » : agrandir/réduire le menu et ajuster la police
    widget_pool: list[tk.Widget] = []  # Tous les widgets du menu
    FONT_AWARE = (tk.Label, tk.Button, tk.Entry, tk.Checkbutton, tk.Menubutton)

    def _set_hover(state: bool) -> None:
        frame_menu.config(width=HOVER_WIDTH if state else DEFAULT_WIDTH)
        font = HOVER_FONT if state else DEFAULT_FONT
        for w in widget_pool:
            if isinstance(w, FONT_AWARE):
                w.configure(font=font)

    frame_menu.bind("<Enter>", lambda _e: _set_hover(True))
    frame_menu.bind("<Leave>", lambda _e: _set_hover(False))

    # ── Zone centrale de tracé ───────────────────────────────────────────────
    frame_plot = tk.Frame(root)
    frame_plot.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # États réactifs (mutable via closures)
    # ─────────────────────────────────────────────────────────────────────────
    df_filtered: pd.DataFrame = df.copy()
    v_sec: int = v_sec
    v_eau: int = v_eau
    cutoff: float | None = cutoff_hz

    current_mode = ["classic"]  # Vue courante
    soustraction_active = {"enabled": False}  # Chan1‑3 − Chan4 ?
    sigma_visible = {"enabled": False}  # Afficher ±1 σ ?
    trend_visible = {"enabled": False}  # Courbe tendance ?
    canvas_holder: dict[str, FigureCanvasTkAgg | None] = {"widget": None}

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers « formulaire »
    # ─────────────────────────────────────────────────────────────────────────
    def parse_form_values() -> tuple[pd.Timestamp, pd.Timestamp, float | None, int, int]:
        """Lire et valider les champs de saisie (dates, cutoff, Vsec/eau)."""

        try:
            d0 = datetime.strptime(str_d0.get(), "%d/%m/%Y")
            d1 = datetime.strptime(str_d1.get(), "%d/%m/%Y")
            x_min = pd.Timestamp(d0.year, d0.month, d0.day, 0, 0, 0)
            x_max = pd.Timestamp(d1.year, d1.month, d1.day, 23, 59, 59)
            cutoff_val = None if no_filter.get() else float(str_cutoff.get())
            v_sec_val = int(str_vsec.get())
            v_eau_val = int(str_veau.get())

        except (ValueError, TypeError) as err:
            messagebox.showerror("Erreur", f"Paramètres invalides : {err}")
            raise ValueError from err

        return x_min, x_max, cutoff_val, v_sec_val, v_eau_val

    def apply_soustraction(df_src: pd.DataFrame) -> pd.DataFrame:
        """Appliquer Chan4 en référence (Chan1‑3 -= Chan4) si l’option est active."""

        df_mod = df_src.copy()
        if soustraction_active["enabled"]:
            for i in range(1, 4):
                df_mod[f"chan{i}_voltage_V"] -= df_mod["chan4_voltage_V"]
        return df_mod

    # ─────────────────────────────────────────────────────────────────────────
    # Fonctions de dessin (une par vue)
    # ─────────────────────────────────────────────────────────────────────────
    def draw_classic_plot(df_src: pd.DataFrame, parent):
        df_mod = apply_soustraction(df_src)
        ttl_left, ttl_center = get_plot_titles(df_mod.index.min(), df_mod.index.max(), "classic")
        fig, gs = new_figure(ttl_center, ttl_left)
        ax = plot_voltage(df_mod, gs, fig, df_mod.index.min(), df_mod.index.max(), cutoff_hz=cutoff,
                          show_sigma=sigma_visible["enabled"])

        if trend_visible["enabled"]:
            add_trend_line(ax, df_mod, "classic", cutoff)

        add_overlay_curve(ax, df_mod, overlay_var, "classic")
        ax.legend(fontsize=8, framealpha=0.9)

        plot_sensor_data(df_mod, gs, ax, fig, df_mod.index.min(), df_mod.index.max(), v_sec, v_eau)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw();
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return canvas

    def draw_daily_plot(df_src: pd.DataFrame, parent):
        df_mod = apply_soustraction(df_src)
        ttl_left, ttl_center = get_plot_titles(df_mod.index.min(), df_mod.index.max(), "24h")
        fig, gs = new_figure(ttl_center, ttl_left)
        ax = plot_voltage_24h(df_mod, gs, fig, show_sigma=sigma_visible["enabled"])

        if trend_visible["enabled"]:
            add_trend_line(ax, df_mod, "24h", cutoff)

        add_overlay_curve(ax, df_mod, overlay_var, "24h")
        plot_sensor_data_24h(df_mod, gs, ax, fig)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw();
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return canvas

    def draw_mean24h_plot(df_src: pd.DataFrame, parent):
        df_mod = apply_soustraction(df_src)
        ttl_left, ttl_center = get_plot_titles(df_mod.index.min(), df_mod.index.max(), "mean24h")
        fig, gs = new_figure(ttl_center, ttl_left)
        ax = plot_voltage_mean24h(df_mod, gs, fig, show_sigma=sigma_visible["enabled"])

        if trend_visible["enabled"]:
            add_trend_line(ax, df_mod, "mean24h", cutoff)

        add_overlay_curve(ax, df_mod, overlay_var, "mean24h")
        plot_sensor_data_mean24h(df_mod, gs, ax, fig, v_sec, v_eau)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw();
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return canvas

    def draw_supermean_plot(df_src: pd.DataFrame, parent):
        df_mod = apply_soustraction(df_src)
        ttl_left, ttl_center = get_plot_titles(df_mod.index.min(), df_mod.index.max(), "supermean24h")
        fig, gs = new_figure(ttl_center, ttl_left)
        ax = plot_voltage_mean_chan24h(df_mod, gs, fig, show_sigma=sigma_visible["enabled"])
        add_overlay_curve(ax, df_mod, overlay_var, "supermean24h")
        plot_sensor_data_mean24h(df_mod, gs, ax, fig, v_sec, v_eau)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw();
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        return canvas

    # ─────────────────────────────────────────────────────────────────────────
    # Rafraîchir l’affichage
    # ─────────────────────────────────────────────────────────────────────────
    def update_plot(view_mode: str = "classic") -> None:
        """Déposer la bonne vue sur `frame_plot` après avoir détruit l’ancienne."""

        current_mode[0] = view_mode

        if canvas_holder["widget"]:
            canvas_holder["widget"].get_tk_widget().destroy()

        drawer = {
            "classic": draw_classic_plot,
            "24h": draw_daily_plot,
            "mean24h": draw_mean24h_plot,
            "supermean24h": draw_supermean_plot,
        }[view_mode]

        canvas_holder["widget"] = drawer(df_filtered, frame_plot)

    # ─────────────────────────────────────────────────────────────────────────
    # Actualiser les données (lecture formulaire) puis redessiner
    # ─────────────────────────────────────────────────────────────────────────
    def update_data_and_plot() -> None:
        """Filtrer le DataFrame selon les champs puis rafraîchir la vue courante."""

        nonlocal df_filtered, v_sec, v_eau, cutoff

        try:
            x_min, x_max, cutoff_hz_val, v_sec_val, v_eau_val = parse_form_values()

        except ValueError:
            return

        df_sel = df[(df.index >= x_min) & (df.index <= x_max)].copy()

        # Éliminer le tout début d’une capture longue (bruit de branchement)
        capture_span = df_sel.index.max() - df_sel.index.min()
        cutoff_time = df_sel.index.min()

        if capture_span >= timedelta(hours=24):
            cutoff_time += timedelta(hours=1)

        elif capture_span >= timedelta(minutes=30):
            cutoff_time += timedelta(minutes=10)

        df_sel = df_sel[df_sel.index > cutoff_time]

        # Filtre Butterworth éventuellement
        if cutoff_hz_val is not None:
            for col in ["chan1_voltage_V", "chan2_voltage_V", "chan3_voltage_V", "chan4_voltage_V"]:
                df_sel[col] = lowpass_filter(df_sel[col], cutoff_hz_val)

        add_soil_humidity(df_sel, v_sec_val, v_eau_val)

        df_filtered = df_sel
        v_sec, v_eau, cutoff = v_sec_val, v_eau_val, cutoff_hz_val
        update_plot(current_mode[0])

    # ─────────────────────────────────────────────────────────────────────────
    # Toggles visuels
    # ─────────────────────────────────────────────────────────────────────────
    def toggle_soustraction():
        soustraction_active["enabled"] = not soustraction_active["enabled"]
        btn_soustraction.config(text=f"Soustraction {'ON' if soustraction_active['enabled'] else 'OFF'}")
        update_plot(current_mode[0])

    def toggle_sigma():
        sigma_visible["enabled"] = not sigma_visible["enabled"]
        btn_sigma.config(text=f"±1σ {'ON' if sigma_visible['enabled'] else 'OFF'}")
        update_plot(current_mode[0])

    def toggle_trend():
        trend_visible["enabled"] = not trend_visible["enabled"]
        btn_trend.config(text=f"Tendance {'ON' if trend_visible['enabled'] else 'OFF'}")
        update_plot(current_mode[0])

    # ─────────────────────────────────────────────────────────────────────────
    # Widgets – menu de gauche
    # ─────────────────────────────────────────────────────────────────────────
    def add_sep_label(text: str) -> None:
        """Ajouter un label de séparation stylé dans le menu."""

        sep_label_widget = tk.Label(frame_menu, text=text, bg="lightgray",
                                    font=(DEFAULT_FONT[0], DEFAULT_FONT[1], "bold"))
        sep_label_widget.pack(pady=(30 if widget_pool else 20, 0))
        widget_pool.append(sep_label_widget)

    # load CSV ────────────────────────────────────────────────────────────────
    def load_new_file() -> None:
        """Sélectionner un CSV, recharger les données et réinitialiser les champs."""

        nonlocal df, df_filtered, csv_path
        new_path = filedialog.askopenfilename(title="Sélectionner un fichier CSV", filetypes=[("CSV files", "*.csv")])

        if not new_path:
            return

        try:
            new_df = load_csv(new_path)

        except ValueError as err:
            messagebox.showerror("Erreur de chargement", f"Impossible de lire ce fichier :\n{err}")
            return

        df = new_df
        csv_path = new_path
        df_filtered = new_df.copy()
        file_name_var.set(Path(new_path).name)

        # Maj plages date dans le formulaire
        str_d0.set(df.index.min().strftime("%d/%m/%Y"))
        str_d1.set(df.index.max().strftime("%d/%m/%Y"))

        add_soil_humidity(df_filtered, v_sec, v_eau)
        update_data_and_plot()

    # champs ──────────────────────────────────────────────────────────────────
    str_d0 = tk.StringVar(value=df.index.min().strftime("%d/%m/%Y"))
    str_d1 = tk.StringVar(value=df.index.max().strftime("%d/%m/%Y"))
    str_cutoff = tk.StringVar(value="" if cutoff is None else str(cutoff))
    str_vsec = tk.StringVar(value=str(v_sec))
    str_veau = tk.StringVar(value=str(v_eau))
    no_filter = tk.BooleanVar(value=cutoff is None)

    def add_labeled_entry(label_text: str, text_var: tk.StringVar) -> None:
        """Ajouter une ligne « label + entry » au menu."""

        field_label_widget = tk.Label(frame_menu, text=label_text, anchor="w", bg="lightgray", font=DEFAULT_FONT)
        field_label_widget.pack(fill=tk.X, padx=8, pady=(6, 0))
        entry = tk.Entry(frame_menu, textvariable=text_var, width=12, font=DEFAULT_FONT)
        entry.pack(padx=10, pady=(0, 4))
        widget_pool.extend([field_label_widget, entry])

    # Section « Fichier » ─────────────────────────────────────────────────────
    add_sep_label("────── Fichier CSV ──────")
    file_name_var = tk.StringVar(value=Path(csv_path).name)
    btn_load_csv = tk.Button(frame_menu, text="Charger un autre fichier", command=load_new_file, font=DEFAULT_FONT)
    btn_load_csv.pack(padx=10, pady=6, fill=tk.X)
    widget_pool.append(btn_load_csv)

    # Section « Affichage » ───────────────────────────────────────────────────
    add_sep_label("────── Affichage ──────")
    for lbl, mode in [("Affichage classique", "classic"),
                      ("Affichage 24h", "24h"),
                      ("Moyenne 24h", "mean24h"),
                      ("Moyenne canaux 24h", "supermean24h"), ]:
        b = tk.Button(frame_menu, text=lbl, font=DEFAULT_FONT, command=lambda m=mode: update_plot(m))
        b.pack(padx=10, pady=6, fill=tk.X)
        widget_pool.append(b)

    # Section « Options » ─────────────────────────────────────────────────────
    add_sep_label("────── Options ──────")
    btn_soustraction = tk.Button(frame_menu, text="Soustraction OFF", font=DEFAULT_FONT, command=toggle_soustraction)
    btn_soustraction.pack(padx=10, pady=8, fill=tk.X)
    widget_pool.append(btn_soustraction)

    btn_sigma = tk.Button(frame_menu, text="±1σ OFF", font=DEFAULT_FONT, command=toggle_sigma)
    btn_sigma.pack(padx=10, pady=6, fill=tk.X)
    widget_pool.append(btn_sigma)

    btn_trend = tk.Button(frame_menu, text="Tendance OFF", font=DEFAULT_FONT, command=toggle_trend)
    btn_trend.pack(padx=10, pady=6, fill=tk.X)
    widget_pool.append(btn_trend)

    overlay_var = tk.StringVar(value="None")
    overlay_list = ["None"] + list(OVERLAY_MAP.keys())
    opt_overlay = tk.OptionMenu(frame_menu, overlay_var, *overlay_list, command=lambda *_: update_plot(current_mode[0]))
    opt_overlay.config(font=DEFAULT_FONT, width=18)
    opt_overlay.pack(padx=10, pady=6, fill=tk.X)
    widget_pool.append(opt_overlay)

    # Section « Paramètres dynamiques » ───────────────────────────────────────
    add_sep_label("────── Paramètres ──────")
    for lbl, var in [("Date début :", str_d0),
                     ("Date fin :", str_d1),
                     ("Fréquence coupure :", str_cutoff),
                     ("V_sec :", str_vsec),
                     ("V_eau :", str_veau), ]:
        add_labeled_entry(lbl, var)

    chk = tk.Checkbutton(frame_menu, text="Pas de filtre", variable=no_filter, bg="lightgray", font=DEFAULT_FONT)
    chk.pack(padx=6, pady=4)
    widget_pool.append(chk)

    btn_apply = tk.Button(frame_menu, text="Appliquer", command=update_data_and_plot, bg="#dff0d8", font=DEFAULT_FONT)
    btn_apply.pack(padx=10, pady=10, fill=tk.X)
    widget_pool.append(btn_apply)

    # ─────────────────────────────────────────────────────────────────────────
    # Premier tracé puis boucle Tk
    # ─────────────────────────────────────────────────────────────────────────
    update_data_and_plot()
    root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# Point d’entrée du programme
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    """
    Lancement complet du script : sélection du CSV, dialogue de paramètres,
    pré‑filtrage des données puis ouverture de l’interface graphique.

    Étapes :
        1. Sélection d’un fichier CSV via une boîte de dialogue.
        2. Affichage de `GlobalConfigDialog` pour :
           plage de dates, fréquence de coupure, V_sec, V_eau.
        3. Filtrage initial des données selon la plage choisie.
        4. Démarrage de la fenêtre principale (`start_gui`).
    """

    # ── 0) Racine unique, masquée immédiatement ──────────────────────────────
    root = tk.Tk()
    root.withdraw()

    # ── 1) Sélection du fichier CSV ──────────────────────────────────────────
    path = filedialog.askopenfilename(title="Sélectionner un fichier CSV", filetypes=[("CSV files", "*.csv")])

    if not path:
        sys.exit("Aucun fichier sélectionné.")

    df = load_csv(path)

    # ── 2) Boîte de dialogue initiale ────────────────────────────────────────
    dialog = GlobalConfigDialog(root, df.index.min(), df.index.max())

    if dialog.result is None:  # L’utilisateur a annulé
        root.destroy()
        sys.exit("Annulé par l’utilisateur.")

    x_min, x_max, cutoff_hz, v_sec, v_eau = dialog.result

    # Filtrage immédiat selon la plage retenue & ajout humidité sol────────────
    df = df[(df.index >= x_min) & (df.index <= x_max)].copy()
    add_soil_humidity(df, v_sec, v_eau)

    # ── 3) Lancement de l’interface graphique ────────────────────────────────
    start_gui(df, csv_path=path, v_sec=v_sec, v_eau=v_eau, cutoff_hz=cutoff_hz)

if __name__ == "__main__":
    main()