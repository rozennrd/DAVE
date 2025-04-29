from ds1054z import DS1054Z
print("Entered Script channel2")
# ip = input("Enter device ip address :")
# if not ip:
ip = "200.0.1.20"

scope = DS1054Z(ip)
print("Connected to: ", scope.idn)
print("Currently displayed channels: ", str(scope.displayed_channels))

captures_channel2 = scope.capture_with_timestamps(duration=10, channel=2)
print(captures_channel2)


captures_channel2.to_csv("captured_data2.csv", index=False)

