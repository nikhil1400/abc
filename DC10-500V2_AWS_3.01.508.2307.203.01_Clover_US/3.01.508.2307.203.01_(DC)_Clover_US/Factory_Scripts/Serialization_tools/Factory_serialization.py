###############################################################################
#######     TITLE "Project Clover 3.0 Radio Board Programming Script"  ########
#######     SUBTITLE "COPYRIGHT 2018 BRK BRANDS, INC., FIRST ALERT"    ########
###############################################################################
#######     MODEL:         AC10-500(A)(1042135) DC10-500(1042136)      ########
###############################################################################
#######     PROJECT:       ONELINK WiFi Smoke and CO Alarm             ########
#######     FILENAME:      CU300_flash.py                              ########
#######     DATE:          17/11/2018                                  ########
#######     FILE VERSION:  VERSION 1                                   ########
#######     SW1 RELEASE:                                               ########
#######     AUTHOR:        Nikhil				                       ########
#######     COMPANY:       BRK BRANDS, INC., FIRST ALERT, INC.         ########
#######                    3901 LIBERTY STREET ROAD                    ########
#######                    AURORA, IL 60504-8122                       ########
###############################################################################
#######     HISTORY:       17 Nov 2018 PPR2		                       ########
#######                                                                ########
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
#port = "/dev/tty.usbserial-FTHKI0HT" #Please Change COM Port Here
#baudrate = 9600
######################################################################

delay = 0.5
#---------------------------------------------------------------
# Agregar esta lineas a programa proviniente de Aurora
#---------------------------------------------------------------
#   Serial port function with timeout and error management
#---------------------------------------------------------------
def  serial_read(timenlap,code_error):
    timevar1 = time.time()+timenlap
    while not ser.inWaiting() and timevar1 > time.time():
        pass
    if not ser.inWaiting():
        ser.close()
        print "timeout puerto serie"
        ser.close()
        sys.exit(code_error)

#---------------------------------------------------------------        
parser = argparse.ArgumentParser(description='clean-up')
parser.add_argument('-c', help='com port', required=True)
arguments = parser.parse_args()
#---------------------------------------------------------------

try:
    ser = serial.Serial(arguments.c, timeout=1)
except serial.SerialException:
    print "error en puerto serie"
    
    sys.exit(1);  #serial port not available, error

ser.baudrate = 9600


print "SCRIPT SERIALIZATION" + '\n\r'
print "COM used = "+arguments.c

#---------------------------------------------------------------
#---------------------------------------------------------------

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
#serialNumber = str(uuid.uuid4()).translate(None, ''.join("-")).upper() # Serial number is don't care
serialNumber = "FFFFFFFF"
print serialNumber
cryptoKey = os.urandom(16).encode('hex').upper()
print cryptoKey
accessToken = os.urandom(16).encode('hex').upper()
print accessToken

f = open("./config/wifi.txt","r")
ssid = f.readline().replace("\n", "")
wifiPW = f.readline()
f.close
#print ssid
#print wifiPW
BleVersion_config_path = "../Serialization_tools/config/BLEVersion"
BLEVERSION = open(BleVersion_config_path,"r")
BLEVERSION = BLEVERSION.readline()
print BLEVERSION

with open("./output/result_serialization.txt", "w") as text_file:
    text_file.write("FAIL")

#--------------------------------------------------------------------------------------
#       Read FIRMWARE VERSION from PIC
#--------------------------------------------------------------------------------------
ser.write("RF\r")
time.sleep(delay)
while ser.inWaiting() == 0:
	pass
FWVersion = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\Old Firmware Version =  " + FWVersion
FWVersion = FWVersion[:9] + BLEVERSION + FWVersion[13:]
ser.write("WF," + FWVersion + '\r')
time.sleep(delay)
print "\FIRMWARE VERSION=  " + FWVersion
#--------------------------------------------------------------------------------------
#       Read Modelo from PIC
#--------------------------------------------------------------------------------------
print "Reading Model... from PIC"
printModel = '1042136'
ser.write("WM," + printModel + '\r')
time.sleep(delay)
ser.write("RM\r")
time.sleep(0.4)
serial_read(5.0,2.0)    #error 2 no puede leer modelo
model = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tModel = " + model + "\n"

#--------------------------------------------------------------------------------------
print "Writing Vendor to PIC and Read Back..."
print "\n"
ser.write("WV," + vendor + '\r')
time.sleep(delay)
ser.write("RV\r")
time.sleep(delay)
serial_read(5.0,3.0)    #error 3 no puede leer vendor PIC
vendor_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tVendor(sent to PIC) = " + vendor
print "\tVendor(read back) = " + vendor_rb + "\n"

#--------------------------------------------------------------------------------------
if vendor == "jssdev":
	if model == "1042135":
		portalID = AC_Dev
	elif model == "1042136":
		portalID = DC_Dev
elif vendor == "cloud_onelink_firstalert":
	if model == "1042135":
		portalID = AC_Prod
	elif model == "1042136":
		portalID = DC_Prod
else:
	portalID = ""
#RV gets cloud_onelink_firstalert    vendor
# or if model = AC, portalID = AC_Dev / Prod

print "\tPortal = " + portalID + "\n"

date = str(datetime.datetime.today())

extraList = {"Date":date}

extra=json.dumps(extraList)

#--------------------------------------------------------------------------------------
print "Writing Serial Number to PIC and Read back..."
ser.write("WS," + serialNumber + '\r')
time.sleep(delay)
ser.write("RS\r")
time.sleep(delay)
serial_read(5.0,7.0)    #error 7 no puede numero de serie de PIC
serialNumber_rb = ser.read(ser.inWaiting()).rstrip('\n\r')
print "\tSerial Number(read back) = " + serialNumber_rb + "\n"
#---------------------------------------------------------------------------------------------------------
print "Writing Cryptokey to PIC and Read back..."
ser.write("WK," + cryptoKey + '\r')
time.sleep(delay)
ser.write("RK\n\r")
time.sleep(delay)
serial_read(5.0,8.0)    #error 8 no puede leer Cryptokey de PIC
cryptoKey_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tCryptoKey(read back) = " + cryptoKey_rb + "\n"
#---------------------------------------------------------------------------------------------------------
print "Writing Access Token to PIC and Read back..."
ser.write("WA," + accessToken + '\r')
time.sleep(delay)
ser.write("RA\r")
time.sleep(delay)
serial_read(5.0,9.0)    #error 9 no puede leer Access Token PIC
accessToken_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tAccess Token(read back) = " + accessToken_rb + "\n"
#---------------------------------------------------------------------------------------------------------
print "Writing SSID to PIC and Read back..."
ser.write("WI," + ssid + '\r')
time.sleep(delay)
ser.write("RI\r")
time.sleep(delay)
serial_read(5.0,10.0)    #error 10, no puede leer SSID de PIC
ssid_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
#print "\tWifi SSID read back ok = "  + ssid_rb
print ssid_rb + "\n"
#---------------------------------------------------------------------------------------------------------
print "Writing WiFi Password to PIC and Read back..."
ser.write("WP," + wifiPW + '\r')
time.sleep(delay)
ser.write("RP\r")
time.sleep(delay)
serial_read(5.0,11.0)    #error 11, no puede leer WiFi password de PIC
wifiPW_rb = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tWifi Password read back ok" + "\n"
#---------------------------------------------------------------------------------------------------------
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
print "Serialization Completado"
sys.exit(0)
#raw_input("Press Enter to leave program...")
