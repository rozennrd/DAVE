import dwfpy as dwf
import logging
from utils.capture_v2 import capture_with_timestamps
import sys
from dave_cloud_main.cloud import upload_to_cloud
from datetime import datetime as dt, timedelta

# Config - initialisation du logger
logging.basicConfig(format="%(asctime)s - %(levelname)s : %(message)s", filename="dave.log", filemode="a", datefmt="%Y-%m-%d %H:%M:%s")
logger = logging.getLogger()
print("Entered Script channel1")

console_handler = logging.StreamHandler()

logger.addHandler(console_handler)

# Config - récupération du timestamp de début de manip pour créer le fichier csv
launch_dt = dt.now()
launch_timestamp = launch_dt.strftime('%Y-%m-%d %H:%M:%S')

# Saisie du nombre d'heures -  par défaut 0 (capture infinie), décommenter la section suivante et remplacer le 0 pour saisir la valeur
duree_heure = 0 # int(input("Saisissez le nombre d'heures pendant lesquelles le capteur doit enregistrer des données. Entrez 0 pour enregistrer indéfiniment. \n"))
duree_manip_en_secondes = duree_heure * 3600 or "infini"

print(launch_timestamp)
nb_attempts = 1
max_reconnections_authorized = 10
finished = 0;

while nb_attempts < max_reconnections_authorized and not finished:
    
    try:
        csv_file = f"captured_data_{launch_timestamp}.csv"
        print(f"Capture en cours pour {duree_manip_en_secondes} secondes. Les données seront enregistrées dans le fichier {csv_file}")
        device1 = dwf.Device(serial_number='210415BD5853')
        device2 = dwf.Device(serial_number='210415BD57E0') 
        device1.open()
        device2.open()
        # Capture des données sur les canaux disponibles
        capture_with_timestamps(csv_file=csv_file, device1=device1, device2=device2, duration=duree_manip_en_secondes, with_sensor_data=True, logger=logger)

        finished=1

    # ^C
    except KeyboardInterrupt :
        print("Done. Bye.")
        device1.close()
        device2.close()
        upload_to_cloud(csv_file)
        sys.exit(0)

    except Exception as e: 
        tb = e.__traceback__
        logger.error(f"Tentative {nb_attempts} :\n {e.with_traceback(tb)}")
        device1.close()
        device2.close()
        nb_attempts = nb_attempts + 1
        if max_reconnections_authorized < nb_attempts :
            # fin de la manip, on upload le fichier
            upload_to_cloud(csv_file)

    if finished:
        upload_to_cloud(csv_file)
        sys.exit(0)
