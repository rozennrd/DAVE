import pandas as pd

from .signal_tools import lowpass_filter
from .config import BASE_DATE, RESAMPLE_24H, OVERLAY_MAP

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

    if mode == "supermean24h":      # Pas pertinent dans cette vue
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