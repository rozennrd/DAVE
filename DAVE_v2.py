import dwfpy as dwf
import logging
from utils.capture_v2 import capture_with_timestamps
import sys
from dave_cloud_main.cloud import upload_to_cloud


# Config
logging.basicConfig(format="%(asctime)s - %(levelname)s : %(message)s", filename="dave.log", filemode="a", datefmt="%Y-%m-%d %H:%M:%s")
logger = logging.getLogger()
print("Entered Script channel1")

console_handler = logging.StreamHandler()

logger.addHandler(console_handler)

from datetime import datetime as dt, timedelta

duree_heures = 50
launch_dt = dt.now()
launch_timestamp = launch_dt.strftime('%Y-%m-%d %H:%M:%S')

launch_datetime = dt.strptime(launch_timestamp, '%Y-%m-%d %H:%M:%S')
new_timestamp = launch_datetime + timedelta(hours=duree_heures)
new_timestamp_str = new_timestamp.strftime('%Y-%m-%d %H:%M:%S')


# Saisie du nombre d'heures
duree_heure = 0 # int(input("Saisissez le nombre d'heures pendant lesquelles le capteur doit enregistrer des données. Entrez 0 pour enregistrer indéfiniment. \n"))
duree_manip_en_secondes = duree_heure * 3600
	

print(new_timestamp_str)
nb_attempts = 1
max_reconnections_authorized = 10
finished = 0;

while nb_attempts < max_reconnections_authorized and not finished:
    
    try:
        csv_file = f"captured_data_{new_timestamp_str}.csv"
        print(f"Capture en cours pour {duree_manip_en_secondes} secondes. Les données seront enregistrées dans le fichier {csv_file}")
        device1 = dwf.Device(serial_number='210415BD5853')
        device2 = dwf.Device(serial_number='210415BD57E0') 
        device1.open()
        device2.open()
        # Capture des données sur les canaux disponibles
        capture_with_timestamps(csv_file=csv_file, device1=device1, device2=device2, duration=duree_manip_en_secondes, with_sensor_data=True, logger=logger)

        finished=1
	
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
        upload_to_cloud(csv_file)
        nb_attempts = nb_attempts + 1




