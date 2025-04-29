#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec

# Charger les données
data_path = "./captured_data_2025-04-17 13h59m19s.csv"
df = pd.read_csv(data_path, index_col=0, parse_dates=True)
df.dropna(inplace=True)
# Création de la figure avec GridSpec pour un contrôle précis de la disposition
fig = plt.figure(figsize=(12, 8))
gs = gridspec.GridSpec(3, 2, width_ratios=[1, 1], height_ratios=[1, 1, 1])

# Extraire la date de début et de fin pour formater le titre
start_time = df.index.min()
end_time = df.index.max()
duration_hours = (end_time - start_time).total_seconds() / 3600

# Formater la date et la durée pour le titre
title_date = start_time.strftime('%d/%m/%Y')  # Format : jour mois année (ex: 21 janvier 2025)
title_text = f"Capture du {title_date} pendant {duration_hours:.1f} heures"
fig.suptitle(title_text, fontsize=16)

# Graphique de tension occupant toute la colonne gauche
i=0
big_ax = fig.add_subplot(gs[:2, 0])  # Fusionne toutes les lignes de la première colonne
for chan in ["chan1", "chan2", "chan3"]:
    i=i+1
    df[f"{chan}_voltage_V"].plot(ax=big_ax, legend=True, label=f"Channel {i}")

# Calcul et ajout de la courbe de moyenne des trois tensions
df["moyenne_voltage"] = df[["chan1_voltage_V", "chan2_voltage_V", "chan3_voltage_V"]].mean(axis=1)
df["moyenne_voltage"].plot(ax=big_ax, linestyle="-", color="red", linewidth=2, legend=True, label="Moyenne globale")


big_ax.set_ylabel("Voltage (V)")
big_ax.set_xticklabels([])
big_ax.set_xlabel("")

# Graphique pour chan4_voltage_V en bas de la colonne gauche
ax4 = fig.add_subplot(gs[2, 0], sharex=big_ax)
df["chan4_voltage_V"].plot(ax=ax4, color='brown', legend=True, label="Channel 4 (Terre)")
ax4.set_ylabel("Voltage (V)")
ax4.set_xlabel("Temps")

# Appliquer le format de date sur l'axe X du graphique du chanel4
date_format = mdates.DateFormatter('%d/%m %Hh%M')
ax4.xaxis.set_major_formatter(date_format)
ax4.xaxis.set_major_locator(mdates.AutoDateLocator())

# Rotation des dates pour une meilleure lisibilité
plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha="right")

# Température dans la 1ère ligne de la 2ème colonne
ax1 = fig.add_subplot(gs[0, 1], sharex=big_ax)
df["temp_degC"].plot(ax=ax1, color='m')
ax1.set_ylabel("Température (°C)")
ax1.set_xticklabels([])  # Supprime les labels des ticks
ax1.set_xlabel("")  # Supprime complètement le label de l'axe X

# Humidité dans la 2ème ligne de la 2ème colonne
#df["humidity_percent"].plot(ax=ax2, color='r')
#ax2.set_ylabel("Humidité (%)")
#ax2.set_xticklabels([])  # Supprime les labels des ticks
#ax2.set_xlabel("")  # Supprime complètement le label de l'axe X

ax2 = fig.add_subplot(gs[1, 1], sharex=big_ax)
df["humidity_soil_percent"] = (df["humidity_air_percent"]+((df["soil_moisture"]-240)/240)*100*(100-df["humidity_air_percent"])/100)
df["humidity_air_percent"].plot(ax=ax2, color='darkturquoise', legend=True, label="Humidité de l'air")
df["humidity_soil_percent"].plot(ax=ax2, color='royalblue', legend=True, label="Humidité du sol")
ax2.set_ylabel("Humidité (%)")
ax2.set_xticklabels([])  # Supprime les labels des ticks
ax2.set_xlabel("")  # Supprime complètement le label de l'axe X

# Intensité lumineuse dans la 3ème ligne de la 2ème colonne
ax3 = fig.add_subplot(gs[2, 1], sharex=big_ax)
df["light_intensity_baseline"].plot(ax=ax3, color='c')
ax3.set_xlabel("Temps")
ax3.set_ylabel("Intensité lumineuse")

# Appliquer le format de date sur l'axe X du graphique d'intensité lumineuse
ax3.xaxis.set_major_formatter(date_format)
ax3.xaxis.set_major_locator(mdates.AutoDateLocator())

# Rotation des dates pour une meilleure lisibilité
plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha="right")


# Ajuster l'espacement pour un rendu propre
plt.tight_layout()

# Afficher la figure
plt.show()
