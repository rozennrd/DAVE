#!/bin/bash

# Nom du script Python à exécuter
PYTHON_SCRIPT="test_ds1054z_channel1.py"

# Vérification de l'existence du script Python
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    echo "Erreur : Le fichier $PYTHON_SCRIPT n'existe pas dans le répertoire courant."
    exit 1
fi

# Exécution du script Python
echo "Exécution de $PYTHON_SCRIPT..."
python "$PYTHON_SCRIPT"

# Vérification de l'exécution
if [[ $? -eq 0 ]]; then
    echo "Le script Python s'est exécuté avec succès."
else
    echo "Erreur lors de l'exécution du script Python."
    exit 1
fi
