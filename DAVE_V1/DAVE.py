from ds1054z import DS1054Z
import logging
from utils.capture import capture_with_timestamps
from utils.calibrators import calibrate_all
import sys


# Config
logging.basicConfig(format="%(asctime)s - %(levelname)s : %(message)s", filename="dave.log", filemode="a", datefmt="%Y-%m-%d %H:%M:%s")
logger = logging.getLogger()
print("Entered Script channel1")
ip = input("Enter device ip address :")
if not ip:
    ip = "200.0.1.20"

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
duree_heure = int(input("Saisissez le nombre d'heures pendant lesquelles le capteur doit enregistrer des données. Entrez 0 pour enregistrer indéfiniment. \n"))
duree_manip_en_secondes = duree_heure * 3600

# Phase de calibrage 
calibrate_all(launch_dt.strftime('%Y-%m-%d %Hh%Mm%Ss'))
	

print(new_timestamp_str)
nb_attempts = 1
max_reconnections_authorized = 10
finished = 0;

while nb_attempts < max_reconnections_authorized and not finished:
    
    try:
        scope = DS1054Z(ip)

	
        print("Connected to: ", scope.idn)
        print("Currently displayed channels: ", str(scope.displayed_channels))


		# Vérification des canaux branchés
        channels_to_check = ["CHAN1", "CHAN2", "CHAN3", "CHAN4"]
        scope.timebase_offset = 0
        scope.timebase_scale = 0.02
        for channel in channels_to_check:
                scope.set_channel_scale(channel, 0.075)
                scope.set_channel_offset(channel, 0.0)
                scope.set_probe_ratio(channel, 1)
		
        active_channels = [ch for ch in channels_to_check if ch in scope.displayed_channels]
        
        if not active_channels:
            print("No channels available for data capture. Exiting.")
        else:
	        print(f"Capturing data from: {active_channels}")

        # Capture des données sur les canaux disponibles
        captured_data = capture_with_timestamps(scope, duration=duree_manip_en_secondes, channels=active_channels, mode="NORMal", with_sensor_data=True, logger=logger)

        # Sauvegarde des données capturées pour chaque canal
        # timestamp = captured_data["timestamp"][0]
        # filename = f"captureddata{timestamp}.csv"
        # captured_data.to_csv(filename, index=False)
        print(captured_data)
        finished=1
	
    except KeyboardInterrupt :
	    print("Done. Bye.")
	    sys.exit(0)

    except Exception as e: 
        tb = e.__traceback__
        logger.error(f"Tentative {nb_attempts} :\n {e.with_traceback(tb)}")
        nb_attempts = nb_attempts + 1




