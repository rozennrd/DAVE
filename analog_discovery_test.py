import dwfpy as dwf
import pandas as pd

number_of_channels = 4;
all_voltages = []

voltages = [pd.NA for _ in range(number_of_channels)]
channel = 0

"""
for adevice in dwf.Device.enumerate():
	print(f'Found device: {adevice.name} ({adevice.serial_number})')
	
	with dwf.Device(serial_number=adevice.serial_number) as device: 
		print(f'Found device: {device.name} ({device.serial_number})')
		scope = device.analog_input
		scope[0].setup(range=0.5)
		scope[1].setup(range=0.5)
		scope.configure()
		recorder = scope.record(sample_rate=1e6, configure=True, start=True)
		samples_chan1 = recorder.channels[0].data_samples
		samples_chan2 = recorder.channels[1].data_samples
		
		voltages[channel] = samples_chan1
		channel += 1
		if (channel < number_of_channels - 1):
			voltages[channel] = samples_chan2
			channel += 1
		if (channel == number_of_channels - 1):
			channel = 0
			all_voltages.append(voltages)
			print(voltages)

with dwf.Device(serial_number='210415BD57E0') as device: 
	print(f'Found device: {device.name} ({device.serial_number})')
	scope = device.analog_input
	scope[0].setup(range=0.5)
	scope[1].setup(range=0.5)
	scope.configure()
	recorder = scope.record(sample_rate=1e6, configure=True, start=True)
	samples_chan1 = recorder.channels[0].data_samples
	samples_chan2 = recorder.channels[1].data_samples
	print(samples_chan1)
	print(samples_chan2)
	print(samples_chan2.size)
"""

device1 = dwf.Device(serial_number='210415BD5853')
device2 = dwf.Device(serial_number='210415BD57E0') 
device1.open()
device2.open()
print(f'Device open: {device1.name} ({device1.serial_number})')
print(f'Device open: {device2.name} ({device2.serial_number})')
scope1 = device1.analog_input
scope1[0].setup(range=0.5)
scope1[1].setup(range=0.5)
scope1.configure()
scope2 = device2.analog_input
scope2[0].setup(range=0.5)
scope2[1].setup(range=0.5)
scope2.configure()
for _ in range(50):
	#record
	recorder1 = scope1.record(sample_rate=1e6, length=0.5, configure=True, start=True)
	recorder2 = scope2.record(sample_rate=1e6, length=0.5, configure=True, start=True)

	# retrieve info
	samples_dev1_chan1 = recorder1.channels[0].data_samples
	samples_dev1_chan2 = recorder1.channels[1].data_samples
	print(samples_dev1_chan1)
	print(samples_dev1_chan2)
	print(samples_dev1_chan2.size)

	samples_dev2_chan1 = recorder2.channels[0].data_samples
	samples_dev2_chan2 = recorder2.channels[1].data_samples
	print(samples_dev2_chan1)
	print(samples_dev2_chan2)
	print(samples_dev2_chan2.size)

device1.close()
device2.close()
