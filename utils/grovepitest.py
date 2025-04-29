
from grovepi import *
from time import sleep

# Configuration des capteurs d'environnement 
dht_sensor_port = 7 # connect the DHt sensor to port 7
dht_sensor_type = 0 # use 0 for the blue-colored sensor and 1 for the white-colored sensor


light_sensor_port = 0 
soil_sensor_port = 2 



# Programme
while(1):
	# get the temperature and Humidity from the DHT sensor
	[ temp,hum ] = dht(dht_sensor_port,dht_sensor_type)
	print("temp =", temp, "C\thumidity =", hum,"%")


	# Get value from light sensor
	light_intensity = analogRead(light_sensor_port)

	# Get value from light sensor
	moisture = analogRead(soil_sensor_port)


	print("light intensity : ", light_intensity)

	print("moisture : ", moisture)

	sleep(3)

