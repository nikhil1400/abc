loop_flag = 0
while loop_flag == 0:
    ssid = raw_input("Input Wifi SSID: ")
    password = raw_input("Input WiFi Password: ")
    print "SSID = " + ssid
    print "Password = " + password

    while True:
        resp = raw_input("Is the above information correct? (Y/N)")
        if resp == "Y":
            with open("./config/wifi.txt", "w") as text_file:   #Writes model to temp_model.txt
                text_file.write(ssid)
                text_file.write("\n")
                text_file.write(password)
            loop_flag = 1
            break
        elif resp == "N":
            break
        else:
            pass
