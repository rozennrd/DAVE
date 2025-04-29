from grovepi import *     

def soil_humidity_sensor_port_calibration() :
	"""
	Fonction interactive de calibrage des capteurs capacitifs d'humidité du sol DFROBOT SEN0193. 
	:return: message de calibration répertoriant les différents seuils selon la documentation du capteur.
	"""
	calibration_message = "Calibration du capteur d'humidité du sol"
	soil_humidity_sensor_port = int(input("Sur quel port est branché le capteur ? Le port doit être un port analogue : A0, A1, A2. Entrez le numéro du port en chiffres."))

	input("Placez le capteur dans l'air, sans le toucher, puis pressez entrée")

	air_value = analogRead(soil_humidity_sensor_port)

	input("Placez le capteur dans un verre d'eau, puis pressez entrée. ATTENTION n e pas dépasser la ligne, se référer à la documentation.")

	water_value = analogRead(soil_humidity_sensor_port)

	step = (air_value-water_value)/3

	calibration_message += f"Les valeurs lues sont {air_value} dans l'air, et {water_value} dans l'eau.\n"
	calibration_message += f"On considère {air_value} à {air_value - step} comme étant sec \n"
	calibration_message += f"On considère {air_value - step} à {water_value + step} comme étant humide \n"
	calibration_message += f"On considère {water_value + step} à {water_value} comme étant très mouillé / de l'eau"
	
	print(calibration_message)
	return calibration_message

def light_sensor_calibration():
	"""
	Fonction interactive de calibrage du capteur de luminosité fourni avec le grovepi. 
	:return: message de calibration répertoriant les valeurs maximales et minimales trouvées.
	"""
	calibration_message = "Calibration du capteur de luminosité"
	print(calibration_message)
	
	light_sensor_port = int(input("Sur quel port est branché le capteur ? Le port doit être un port analogue : A0, A1, A2. Entrez le numéro du port en chiffres."))

	input("Placez le capteur en plein soleil, puis pressez entrée")

	max_value = analogRead(light_sensor_port)

	input("Placez le capteur dans l'obscurité la plus complète possible, puis pressez entrée.")

	min_value = analogRead(light_sensor_port)
	
	calibration_message += f"Les valeurs lues sont {max_value} au soleil, et {min_value} dans l'obscurité.\n"

	print(calibration_message)
	return calibration_message


def calibrate_all(date):
	gonogo = input("Calibrer les capteurs ? N pour non, tout autre caractère = oui")
	print(gonogo)
	
	if gonogo == "N" or gonogo == 'N':
		return
	

	moisture_calibration = soil_humidity_sensor_port_calibration()
	light_calibration = light_sensor_calibration()
	calibration_file = f"calibration_{date}.txt"
	
	with open(calibration_file,'a') as f:
		f.write(moisture_calibration)
		f.write(light_calibration)

