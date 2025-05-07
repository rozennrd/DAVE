import sys
import tkinter as tk
from tkinter import filedialog

from .io_tools import load_csv, add_soil_humidity
from .dialog import GlobalConfigDialog
from .gui import start_gui

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
    root.destroy()

    # ── 3) Lancement de l’interface graphique ────────────────────────────────
    start_gui(df, csv_path=path, v_sec=v_sec, v_eau=v_eau, cutoff_hz=cutoff_hz, start_date=x_min, end_date=x_max)

if __name__ == "__main__":
    main()