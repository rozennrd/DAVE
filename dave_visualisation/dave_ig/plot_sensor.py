from datetime import timedelta
import matplotlib.pyplot as plt
import pandas as pd

from .mpl_tools import format_axes
from .signal_tools import annotate_extremes, stats_str, split_by_day
from .config import BASE_DATE, RESAMPLE_24H

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