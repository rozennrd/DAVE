from datetime import timedelta
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex

from .signal_tools import lowpass_filter, rolling_stats, annotate_extremes, split_by_day, stats_str
from .mpl_tools import format_axes, draw_sigma
from .config import BASE_DATE, RESAMPLE_24H, ROLLING_WINDOW

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
    ax_terre   = fig.add_subplot(gs[2, 0], sharex=ax_voltage)

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
    format_axes(ax_terre,  xlabel="Heure", ylabel="Voltage (mV)", xmin=xmin, xmax=xmax)
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
        line = ax_voltage.plot(data_mv, linewidth=1.5, label=f"Channel {i+1} (moy.)")[0]

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
    ax_volt  = fig.add_subplot(gs[:2, 0])
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
    format_axes(ax_volt,  ylabel="Voltage moy. (mV)", xmin=xt_min, xmax=xt_max)
    format_axes(ax_terre, xlabel="Heure", ylabel="Voltage (mV)", xmin=xt_min, xmax=xt_max)
    ax_volt.legend(fontsize=8)
    ax_terre.legend(fontsize=8)

    return ax_volt