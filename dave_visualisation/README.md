# DAVE IG – Visualisation de l’électrophysiologie végétale

Cette application **Tkinter / Matplotlib** permet d’explorer
interactivement les signaux électriques mesurés sur une plante ainsi que
les capteurs environnementaux (température, humidités, luminosité).

Version actuelle : **V2.7.2**

---

## Sommaire

1. [Fonctionnalités](#fonctionnalités)  
2. [Structure du dépôt](#structure-du-dépôt)  
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

---

## Structure du dépôt

```
.
├── IG V2.7.2.py      # Script principal (single‑file)
├── README.md         # Ce document
└── data_csv/
    └── captured_data_YYYY‑MM‑DD_HH‑MM‑SS.csv
```

---

## Format du fichier CSV

Chaque ligne correspond à un échantillon horodaté. La première colonne
**doit** être `timestamp` ou être utilisable comme index temporel.

| Colonne                     | Unité      | Description                                |
|-----------------------------|------------|--------------------------------------------|
| `timestamp`                 | ISO 8601   | Horodatage de la mesure                    |
| `chan1_voltage_V … chan4_voltage_V` | Volt | Tension brute des 4 électrodes            |
| `temp_degC`                 | °C         | Température ambiante                       |
| `humidity_air_percent`      | %          | Humidité relative de l’air                 |
| `soil_moisture`             | Volt       | Tension brute du capteur sol               |
| `light_intensity_baseline`  | a. u.      | Intensité lumineuse (baseline)             |
| `light_intensity_stressor`  | a. u.      | Intensité lumineuse (stress)               |

> **Astuce :** Un extrait est affiché ci‑dessous à titre d’exemple.

```csv
{df.head().to_csv(index=False, line_terminator='\n').strip()}
```

---

## Installation

1. Créez un environnement :

```bash
python -m venv .venv
source .venv/bin/activate  # sous Windows : .venv\Scripts\activate
```

2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

> Fichier `requirements.txt` minimal :

```
matplotlib
numpy
pandas
scipy
```

---

## Exécution rapide

```bash
python "IG V2.7.2.py"
```

1. Sélectionnez un CSV.  
2. Réglez les paramètres dans la boîte de dialogue.  
3. Profitez !

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
