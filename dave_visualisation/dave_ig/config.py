import pandas as pd

# ── Constantes interface et traitement ───────────────────────────────────────
BASE_DATE         = pd.Timestamp(2000, 1, 1)    # date « origine » pour les courbes 24h
DEFAULT_WIDTH     = 180                                             # largeur menu (px)
HOVER_WIDTH       = 240                                             # largeur menu au survol
DEFAULT_FONT      = ("Arial", 11)                                   # style police menu par défaut
HOVER_FONT        = ("Arial", 15)                                   # style police menu lors du hover

ROLLING_WINDOW    = "10min"                                         # fenêtre moyenne/σ
RESAMPLE_24H      = "10s"                                           # pas de rééchantillonage pour 24h
DEFAULT_CUTOFF_HZ = 0.1                                             # fréquence de coupure par défaut (Hz)
DEFAULT_V_SEC     = 480                                             # valeur « sécheresse » (capteur sol)
DEFAULT_V_EAU     = 234                                             # valeur « eau »

# Correspondance des courbes superposables (overlay) --------------------------
OVERLAY_MAP = {
    "Température"         : ("temp_degC",               "Température (°C)"),
    "Humidité air"        : ("humidity_air_percent",    "Humidité air (%)"),
    "Humidité sol"        : ("humidity_soil_percent",   "Humidité sol (%)"),
    "Luminosité baseline" : ("light_intensity_baseline","Luminosité"),
    "Luminosité stress"   : ("light_intensity_stressor","Luminosité"),
    "Tension terre"       : ("chan4_voltage_V",         "Voltage Terre (mV)"),
}