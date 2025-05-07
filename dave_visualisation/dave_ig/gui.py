import tkinter as tk
from tkinter import filedialog, messagebox
import sys
from pathlib import Path
import pandas as pd
from datetime import timedelta, datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .config import DEFAULT_FONT, HOVER_FONT, HOVER_WIDTH, DEFAULT_WIDTH, OVERLAY_MAP
from .signal_tools import lowpass_filter
from .io_tools import load_csv, add_soil_humidity
from .plot_voltage import plot_voltage, plot_voltage_24h, plot_voltage_mean24h, plot_voltage_mean_chan24h
from .plot_sensor import plot_sensor_data, plot_sensor_data_24h, plot_sensor_data_mean24h
from .overlay import add_trend_line, add_overlay_curve
from .mpl_tools import new_figure, get_plot_titles

# ─────────────────────────────────────────────────────────────────────────────
# Fenêtre principale Tkinter (menu, callbacks, canvas)
# ─────────────────────────────────────────────────────────────────────────────
def start_gui(df: pd.DataFrame, *, csv_path: str, v_sec: int, v_eau: int,
              cutoff_hz: float | None, start_date: pd.Timestamp, end_date: pd.Timestamp) -> None:
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
    str_d0 = tk.StringVar(value=start_date.strftime("%d/%m/%Y"))
    str_d1 = tk.StringVar(value=end_date.strftime("%d/%m/%Y"))
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
