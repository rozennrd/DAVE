from grovepi import *     
import time
from datetime import datetime as dt
import pandas as pd
import csv
import dwfpy as dwf

def capture_with_timestamps(csv_file, logger, device1, device2, duration=0, with_sensor_data=False, max_fails=5):
	"""
	Capture les données d'un canal avec des timestamps machine à chaque seconde.
	Capture également les données du grovepi. Les capteurs pris en compte sont : 
	- humidité de l'air et température (dht) : port D7
	- Luminosité : A0
	- humidité du sol : A2

	:param csv_file: nom du fichier dans lequel il faut enregistrer les données
	:param logger: Logger qui servira à logger les erreurs dans un fichier de logs
	:param device1: oscilloscope Analog Digital 1
	:param device2: le deuxième oscilloscope Analog Digital.
	:param float duration: Durée en secondes pendant laquelle capturer les données. Si 0, capture indéfiniment jusqu'à ^C
	:param str channel: Le canal à capturer (par exemple, "CHAN1").
	:param boolean with_sensor_data: si true, capture les données du grovepi et les ajoute dans le dataframe. Si false, les données du grovepi+ ne sont pas capturées
	:param max_fails: nombre maximal d'erreurs de lecture tolérés avant la levée d'une exception
    :return: None
	"""
	
	start_time = time.time()  # Enregistre le temps de départ
	
	captured_data = []
	
	number_of_iterations = 0
	successive_io_ds1054z_fails = 0
	successive_io_dht_fails = 0
	successive_io_light_sensor_fails = 0
	successive_io_moisture_sensor_fails = 0


	# Initialisation des oscilloscopes
	scope1 = device1.analog_input
	scope1[0].setup(range=0.020)
	scope1[1].setup(range=0.020)
	scope1.configure()
	scope2 = device2.analog_input
	scope2[0].setup(range=0.020)
	scope2[1].setup(range=0.020)
	scope2.configure()

	if (with_sensor_data):
		# Configuration des capteurs d'environnement 
		dht_sensor_port = 7 # connect the DHt sensor to port 7
		dht_sensor_type = 0 # use 0 for the blue-colored sensor and 1 for the white-colored sensor
		
		light_sensor_port_temoin = 0
		soil_moisture_sensor_port= 1
		light_sensor_port_nolight = 2

	nb_channels = 4 
	

	while time.time() - start_time < duration or duration == 0:
		timestamp = dt.now().strftime("%Y-%m-%d %H:%M:%S.%f")
		
		voltages = [pd.NA for _ in range(nb_channels)]

		# Capture des échantillons pour le canal donné
		try:
			#record
			recorder1 = scope1.record(sample_rate=1e6, length=0.5, configure=True, start=True)
			recorder2 = scope2.record(sample_rate=1e6, length=0.5, configure=True, start=True)

			# retrieve info
			samples_dev1_chan1 = recorder1.channels[0].data_samples
			samples_dev1_chan2 = recorder1.channels[1].data_samples
			voltages[0] = samples_dev1_chan1.mean()
			voltages[1] = samples_dev1_chan2.mean()
			

			samples_dev2_chan1 = recorder2.channels[0].data_samples
			samples_dev2_chan2 = recorder2.channels[1].data_samples
			voltages[2] = samples_dev2_chan1.mean()
			voltages[3] = samples_dev2_chan2.mean()
			
			successive_io_ds1054z_fails = 0
			
		except Exception as e:
			tb = e.__traceback__
			logger.warning(f"Acquisition failed in scope, channel {channel_ind}")
			logger.warning(e.with_traceback(tb))
			successive_io_ds1054z_fails += 1
			if successive_io_ds1054z_fails > max_fails * nb_channels:
				raise Exception ("Too many failed attempts on ds1054z !")
					
			  
		dict_to_append = {}
		dict_to_append["timestamp"] = timestamp
		for i in range (nb_channels) :
				dict_to_append[f"chan{i+1}_voltage_V"] = voltages[i]
		
		# Capture des données des capteurs d'environnement
		if(with_sensor_data): 
			try:
					[ temp,hum ] = dht(dht_sensor_port,dht_sensor_type)
					
					successive_io_dht_fails = 0
			except Exception as e:
					tb = e.__traceback__
					logger.warning("Acquisition failed in dht sensor")
					logger.warning(e.with_traceback(tb))
					
					successive_io_dht_fails += 1
					[ temp,hum ] = [pd.NA, pd.NA]
					if successive_io_dht_fails > max_fails:
						raise Exception ("Too many failed attempts on dht sensor !")
					
			try:
					light_intensity_temoin = analogRead(light_sensor_port_temoin)
					light_intensity_stressor = analogRead(light_sensor_port_nolight)
					successive_io_light_sensor_fails = 0
			except Exception as e:
					tb = e.__traceback__
					logger.warning("Acquisition failed in light sensor")
					logger.warning(e.with_traceback(tb))
					light_intensity = pd.NA
					successive_io_light_sensor_fails += 1
					
					if successive_io_light_sensor_fails > max_fails:
						raise Exception ("Too many failed attempts on light sensor !")
			try:
					soil_moisture = analogRead(soil_moisture_sensor_port)
					successive_io_moisture_sensor_fails = 0
			except Exception as e:
					tb = e.__traceback__
					logger.warning("Acquisition failed in light sensor")
					logger.warning(e.with_traceback(tb))
					light_intensity = pd.NA
					successive_io_moisture_sensor_fails += 1
					
					if successive_io_light_sensor_fails > max_fails:
						raise Exception ("Too many failed attempts on light sensor !")
						
			dict_to_append["temp_degC"] = temp
			dict_to_append["humidity_air_percent"] = hum
			dict_to_append["light_intensity_baseline"] = light_intensity_temoin
			dict_to_append["light_intensity_stressor"] = light_intensity_stressor
			dict_to_append["soil_moisture"] = soil_moisture

		captured_data.append(dict_to_append)
		
		try:
				with open(csv_file, "a", newline='') as file:
						writer = csv.writer(file)
						if (number_of_iterations == 0) :  # First iteration of loop, write column headers
								writer.writerow(dict_to_append.keys())
						writer.writerow(dict_to_append.values())
						
		except IOError as e: 
				tb = e.__traceback__
				logger.error(f"CSV write failed at timestamp {timestamp}" )
				logger.error(e.with_traceback(tb))
				
		# on a fini la première itération
		number_of_iterations = number_of_iterations + 1
	
