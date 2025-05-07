import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import pandas as pd

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
        "classic":       "Affichage classique",
        "24h":           "Affichage 24 h",
        "mean24h":       "Moyenne 24 h",
        "supermean24h":  "Moyenne canaux 24 h",
    }
    title_left = mode_names.get(mode, mode)

    # -------------------- Durée lisible , par ex : « 3 jours 4h 30min » --------------------
    duration = x_max - x_min
    days     = duration.days
    hours, rem = divmod(duration.seconds, 3600)
    minutes  = rem // 60
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