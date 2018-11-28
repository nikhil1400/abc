###############################################################################
#######     TITLE "Project Clover Radio Board Programming Script"      ########
#######     SUBTITLE "COPYRIGHT 2015 BRK BRANDS, INC., FIRST ALERT"    ########
###############################################################################
#######     MODEL:         AC10-500 DC10-500                           ########
###############################################################################
#######     PROJECT:       ONELINK WiFi Smoke and CO Alarm             ########
#######     FILENAME:      serialization.py                            ########
#######     DATE:          10/8/2015                                   ########
#######     FILE VERSION:  VERSION 1.0                                 ########
#######     SW1 RELEASE:   SW1-0242-000E1 SCRIPT, PRGRM BLE WIFI RADIOS########
#######     AUTHOR:        CHIA-HUA "CHARLIE" LIN                      ########
#######     COMPANY:       BRK BRANDS, INC., FIRST ALERT, INC.         ########
#######                    3901 LIBERTY STREET ROAD                    ########
#######                    AURORA, IL 60504-8122                       ########
###############################################################################
#######     HISTORY:       10/8/2015 FIRST RELEASE                     ########
###############################################################################



import sys
import uuid
import os
import datetime
import argparse
import requests
import json
import time
import serial

from functools import wraps

from configManager import ConfigManager
credentials = ConfigManager()


############################# Configuration ##########################
port = "/dev/tty.usbserial-FT99JMNX" #Please Change COM Port Here
baudrate = 9600
######################################################################

delay = 0.5


userName = credentials.configData[ConfigManager.USERNAME_KEY]
#print userName
password = credentials.configData[ConfigManager.PASSWORD_KEY]
#print password
pilot = credentials.configData[ConfigManager.PILOT_KEY]
#print pilot
vendor = str(credentials.configData[ConfigManager.VENDOR_KEY])
#print vendor
AC_Dev = credentials.configData[ConfigManager.AC_DEV]
#print AC_Dev
AC_Prod = credentials.configData[ConfigManager.AC_PROD]
#print AC_Prod
DC_Dev = credentials.configData[ConfigManager.DC_DEV]
#print DC_Dev
DC_Prod = credentials.configData[ConfigManager.DC_PROD]
#print DC_Prod
base_URL = credentials.configData[ConfigManager.PORTAL_URL_KEY]
#print base_URL
baseAPI_URL = credentials.configData[ConfigManager.ADMIN_URL_KEY] + "/provision/manage/model/"
#print baseAPI_URL
API_Token = credentials.configData[ConfigManager.API_TOKEN_KEY]
#print API_Token
serialNumber = str(uuid.uuid4()).translate(None, ''.join("-")).upper()
#print serialNumber
cryptoKey = os.urandom(16).encode('hex').upper()
#print cryptoKey
accessToken = os.urandom(16).encode('hex').upper()
#print accessToken


f = open("./config/wifi.txt","r")
ssid = f.readline().replace("\n", "")
wifiPW = f.readline()
f.close
#print ssid
#print wifiPW

with open("./output/result_serialization.txt", "w") as text_file:
    text_file.write("FAIL")
ser = serial.Serial(port)
ser.baudrate = baudrate
print ""
print "Starting Serialization Process..."
print ""
print "Please connect Clover(power on), connect N40 to Ground, and connect the battery..."
substring = "Fac"
substring1 = "F"
substring2 = "Fa"
#substring = "Factory Set"
string = ""
while True:

	while ser.inWaiting() == 0:
		pass
	string = ser.read(ser.inWaiting())
	#print string
	if substring in string:
	    raw_input("Remove N40 from Ground and Press ENTER...")
	    break
	if substring1 in string:
	    substring = "ac"
	if substring2 in string:
		substring = "c"
ser.write("RM\r") #Get rid of junk in the buffer
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
modelVoid = ser.read(ser.inWaiting())

print "Reading Model... from PIC"
ser.write("RM\r")
time.sleep(delay)
while ser.inWaiting() == 0:
	pass
model = ser.read(ser.inWaiting()).rstrip('\r\n')
model = model + 'V2'
print "\tModel =  " + model
#RM gets DC10-500    model number

print "Writing Vendor to PIC and Read Back..."
print "\n"
ser.write("WV," + vendor + '\r')
time.sleep(delay)
ser.write("RV\r")
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
vendor_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tVendor(sent to PIC) = " + vendor
print "\tVendor(read back) = " + vendor_rb + "\n"


if vendor == "jssdev":
	if model[:2] == "AC":
		portalID = AC_Dev
	elif model[:2] == "DC":
		portalID = DC_Dev
elif vendor == "cloud_onelink_firstalert":
	if model[:2] == "AC":
		portalID = AC_Prod
	elif model[:2] == "DC":
		portalID = DC_Prod
else:
	portalID = ""
#RV gets cloud_onelink_firstalert    vendor
# or if model = AC, portalID = AC_Dev / Prod

print "\tPortal = " + portalID + "\n"


def getHeaders():
    return {"X-Exosite-Token": API_Token, "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}

def getUrl(Model):
	return baseAPI_URL + Model + "/"

def getFormData(Serial, Info):
	return "sn=" + Serial + "&extra=" + Info

def getRequest(Model, Serial, Extra):
    req = requests.post(getUrl(Model), headers=getHeaders(), data=getFormData(Serial, Extra))
    return req

date = str(datetime.datetime.today())

extraList = {"Date":date}

extra=json.dumps(extraList)
print "Provisioning the Device on Cloud..."
while True:
    try:
        response = getRequest(model, serialNumber, extra)
    except requests.exceptions.ConnectionError as e:
        raw_input("Error: No Internet Connection. Press any key to leave program...")
        exit()
    if response.status_code != 409:
        break
    serialNumber = str(uuid.uuid4()).translate(None, ''.join("-")).upper()


def addDeviceToUser():
    url = base_URL + "/api/portals/v1/portals/" + portalID + "/devices"
    headers = { "Content-Type": "application/x-www-form-urlencoded"}
    dataString = {"model": model, "vendor": vendor, "sn": serialNumber, "type": "vendor"}
    return requests.post(url, headers=headers, data=json.dumps(dataString), auth=requests.auth.HTTPBasicAuth(userName, password))


if response.status_code != 205:
    print "Failed to provision Serial Number!!! (" + str(response.status_code) + ")"
    raw_input("Press any key to exit")
    exit()
else:
    print "\tProvision Success (" + str(response.status_code) + ")\n"
    print "Creating Device in the Portal...\n"
    resp = addDeviceToUser().status_code
    if resp != 201:
        print "Forbidden from Creating Device to Exosite Portal!!! (" + str(resp) + ")"
        raw_input("Press any key to leave program...")
        exit()
    else:
        print "\tDevice Added to Portal (" + str(resp) + ")\n"

    print "Writing Serial Number to PIC and Read back..."
    ser.write("WS," + serialNumber + '\r')
    time.sleep(delay)
    ser.write("RS\r")
    time.sleep(delay)
    while ser.inWaiting() == 0:
        pass
    serialNumber_rb = ser.read(ser.inWaiting()).rstrip('\n\r')
    print "\tSerial Number(read back) = " + serialNumber_rb + "\n"

    print "Writing Cryptokey to PIC and Read back..."
    ser.write("WK," + cryptoKey + '\r')
    time.sleep(delay)
    ser.write("RK\n\r")
    time.sleep(delay)
    while ser.inWaiting() == 0:
        pass
    cryptoKey_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
    print "\tCryptoKey(read back) = " + cryptoKey_rb + "\n"

    print "Writing Access Token to PIC and Read back..."
    ser.write("WA," + accessToken + '\r')
    time.sleep(delay)
    ser.write("RA\r")
    time.sleep(delay)
    while ser.inWaiting() == 0:
        pass
    accessToken_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
    print "\tAccess Token(read back) = " + accessToken_rb + "\n"

    print "Writing SSID to PIC and Read back..."
    ser.write("WI," + ssid + '\r')
    time.sleep(delay)
    ser.write("RI\r")
    time.sleep(delay)
    while ser.inWaiting() == 0:
        pass
    ssid_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
    print "\tWifi SSID(read back) = " + ssid_rb + "\n"

    print "Writing WiFi Password to PIC and Read back..."
    ser.write("WP," + wifiPW + '\r')
    time.sleep(delay)
    ser.write("RP\r")
    time.sleep(delay)
    while ser.inWaiting() == 0:
        pass
    wifiPW_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
    print "\tWifi Password(read back) = " + wifiPW_rb + "\n"
    with open("./output/result_serialization.txt", "w") as text_file:
        text_file.write("PASS")
    if os.path.exists("./output/count_serialization.txt"):
        fo = open("./output/count_serialization.txt", "r")
        line = fo.readline()
        fo.close()
        count = (int(float(line)))
        count = count + 1
        fo = open("./output/count_serialization.txt", "w")
        fo.write(str(count))
        fo.close()
    else:
        fo = open("./output/count_serialization.txt", "w")
        fo.write("1")
        fo.close()

ser.close()
print "Serialization Completed"
raw_input("Press Enter to leave program...")
