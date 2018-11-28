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

import argparse
import requests
import uuid
import serial
import time
import json
import urllib
import httplib
import sys


delay = 0.4

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
        sys.exit(code_error)

#---------------------------------------------------------------

parser = argparse.ArgumentParser(description='clean-up')
parser.add_argument('-c', help='com port', required=True)
arguments = parser.parse_args()

print "SCRIPT CLEANUP SEGUNDA ESTACION MODELO DOMESTICO CLOVER V2.0" + '\n\r'

print "COM used = "+arguments.c

from configManager import ConfigManager
credentials = ConfigManager()

BASE_API_URL = credentials.configData[ConfigManager.ADMIN_URL_KEY]+"/provision/manage/model/"
API_TOKEN = credentials.configData[ConfigManager.API_TOKEN_KEY]

BASE_URL = credentials.configData[ConfigManager.PORTAL_URL_KEY]

USERNAME = credentials.configData[ConfigManager.USERNAME_KEY]
PASS = credentials.configData[ConfigManager.PASSWORD_KEY]

try:
    ser = serial.Serial(arguments.c, timeout=1) #Please Change COM Port Here
except SerialException:
    print "error en puerto serie"
    sys.exit(30);  #serial port not available, error

ser.baudrate = 9600

with open("./output/result_clean_up.txt", "w") as text_file:
    text_file.write("FAIL")
    
print ""
print "Starting Clean Up Process..."

ser.write("RM\n\r")#Get rid of junk in the buffer
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
modelVoid = ser.read(ser.inWaiting())

#--------------------------------------------------------------------------------------
#       Read Modelo from PIC\
#--------------------------------------------------------------------------------------
print "Reading Model from PIC..."
ser.write("RM\r")
time.sleep(0.4)
serial_read(5.0,10.0)
model = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tModel = " + model + "\n"
#----------------------------------------------

#--------------------------------------------------------------------------------------
# Check for mistake in selecting the wrong model in the PC between DOMESTIC AND CANADA versions
#---------------------------------------------------------------------------------------
#if model != m1 and model != m2 :
# print "Modelo equivocado, deber ser modelo DOMESTICO\n\r"
# sys.exit(31)        #modelo equivocado          

model_prefix = ''.join(model.split())[:-5].upper()

#---------------------------------------------------------------------
#           Read the serial number from PIC
#---------------------------------------------------------------------
print "Reading Serial Number from PIC..."
ser.write("RS\r")
time.sleep(delay)
serial_read(5.0,11)
serialNumber = str(ser.read(ser.inWaiting()).upper().rstrip('\r\n'))
print "\tSerial Number from PIC= " + serialNumber + "\n"


#print "Reading CU300 Mac Address from PIC..."
#ser.write("DM\r")
#time.sleep(delay)
#while ser.inWaiting() == 0:
#    pass
#mac = ser.read(ser.inWaiting()).rstrip('\r\n')
#print "\tCU300 Mac Address = " + mac + "\n"

#mac_last4 = ''.join(mac.split())[8:].upper()


time.sleep(0.5)
print "Reseting Target..."
ser.write("RR\r")
time.sleep(0.5)

substring = "C"
substring1 = "C"
substring2 = "CL"
string = ""

timenlap = 50.0

timevar1 = time.time()+timenlap

while timevar1 > time.time():
    string = ser.read(ser.inWaiting())
    #print time.time()
    #print string
    if substring in string:
        print("Clean-up completado. Por favor remueva unidad de la fixtura")
        ser.close()
        sys.exit(0)
        
    if substring1 in string:
        substrinG = "LR"
             
    if substring2 in string:
        substring = "R"
   
ser.close()
sys.exit(35)
