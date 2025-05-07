import tkinter as tk
from tkinter import simpledialog, messagebox
from datetime import datetime, timedelta
import pandas as pd

from .config import DEFAULT_CUTOFF_HZ, DEFAULT_V_SEC, DEFAULT_V_EAU


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