# DAVE IG – Visualisation de l’électrophysiologie végétale

Cette application **modulaire** basée sur **Tkinter / Matplotlib** permet d’explorer
interactivement les signaux électriques mesurés sur une plante ainsi que
les capteurs environnementaux (température, humidités, luminosité).

Version actuelle : **V3.0 (modulaire)**

---

## Sommaire

1. [Fonctionnalités](#fonctionnalités)  
2. [Structure du paquet](#structure-du-paquet)  
3. [Format du fichier CSV](#format-du-fichier-csv)  
4. [Installation](#installation)  
5. [Exécution rapide](#exécution-rapide)  
6. [FAQ](#faq)  
7. [Licence](#licence)

---

## Fonctionnalités

- _Filtre passe‑bas Butterworth_ configurable sur les 4 canaux.
- Affichages :  
  - **Classique** (chronologique)  
  - **24 h superposées** (comparaison jour / jour)  
  - **Moyenne 24 h** par canal  
  - **Moyenne des canaux 1‑3**
- Options visuelles : ±1 σ glissant, soustraction Chan 4, tendance grise,
  courbe secondaire (température, humidité, etc.).
- Changement de CSV **à chaud** sans relancer le script.
- Calcul natif du % humidité du sol (linéarisation _V<sub>sec</sub>_
  ↔ _V<sub>eau</sub>_).
- Interface plein‑écran et menu latéral extensible.
- **Architecture modulaire** avec séparation claire des responsabilités.

---

## Structure du paquet

```
.
├── pyproject.toml        # Configuration editable install
├── requirements.txt      # Dépendances Python
├── README.md             # Ce document
└── dave_ig/
    ├── app.py            # Point d’entrée principal
    ├── config.py         # Constantes globales
    ├── dialog.py         # Fenêtre Tkinter de configuration
    ├── gui.py            # Interface graphique
    ├── io_tools.py       # Lecture CSV, humidité sol
    ├── mpl_tools.py      # Aides Matplotlib
    ├── overlay.py        # Courbes secondaires (tendance, capteurs)
    ├── plot_sensor.py    # Tracés environnementaux
    ├── plot_voltage.py   # Tracés tensions
    ├── signal_tools.py   # Statistiques, filtrage, etc.
    └── __init__.py
```

---

## Format du fichier CSV

| Colonne                     | Unité      | Description                                |
|-----------------------------|------------|--------------------------------------------|
| `timestamp`                 | ISO 8601   | Horodatage de la mesure                    |
| `chan1_voltage_V … chan4_voltage_V` | Volt | Tension brute des 4 électrodes            |
| `temp_degC`                 | °C         | Température ambiante                       |
| `humidity_air_percent`      | %          | Humidité relative de l’air                 |
| `soil_moisture`             | Volt       | Tension brute du capteur sol               |
| `light_intensity_baseline`  | a. u.      | Intensité lumineuse (baseline)             |
| `light_intensity_stressor`  | a. u.      | Intensité lumineuse (stress)               |

> Le fichier doit contenir une colonne `timestamp` ou une première colonne convertible en index temporel.

---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # sous Windows : .venv\Scripts\activate

pip install -e .
```

---

## Exécution rapide

```bash
python -m dave_ig.app
```

1. Sélectionnez un fichier CSV.  
2. Réglez les paramètres de visualisation.  
3. Profitez de l’analyse interactive !

---

## FAQ

| Question                                              | Réponse courte |
|-------------------------------------------------------|----------------|
| **Le filtre passe‑bas n’a aucun effet ?**             | Vérifiez que la fréquence de coupure est << *fs*/2. |
| **Humidité du sol incohérente ?**                     | Recalibrez `V_sec` et `V_eau` dans le menu.          |
| **Le script fige avec de gros fichiers ?**            | Utilisez un découpage de dates plus réduit.          |

---

## Licence

Projet mis à disposition sous licence MIT. Voir `LICENSE` pour plus
d’informations.