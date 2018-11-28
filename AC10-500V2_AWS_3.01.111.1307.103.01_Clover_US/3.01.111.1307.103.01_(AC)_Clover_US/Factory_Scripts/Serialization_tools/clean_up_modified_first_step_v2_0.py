###############################################################################
#######     TITLE "Project Clover 3.0 Radio Board Programming Script"  ########
#######     SUBTITLE "COPYRIGHT 2018 BRK BRANDS, INC., FIRST ALERT"    ########
###############################################################################
#######     MODEL:         AC10-500(A)(1042135) DC10-500(1042136)      ########
###############################################################################
#######     PROJECT:       ONELINK WiFi Smoke and CO Alarm             ########
#######     FILENAME:      CU300_flash.py                              ########
#######     DATE:          18/11/2018                                  ########
#######     FILE VERSION:  VERSION 1                                   ########
#######     SW1 RELEASE:                                               ########
#######     AUTHOR:        Nikhil				                       ########
#######     COMPANY:       BRK BRANDS, INC., FIRST ALERT, INC.         ########
#######                    3901 LIBERTY STREET ROAD                    ########
#######                    AURORA, IL 60504-8122                       ########
###############################################################################
#######     HISTORY:       18 Nov 2018 PPR2		                       ########
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
import shutil

from Naked.toolshed.shell import execute_js
import sys
import csv
import subprocess
import os

import threading
import sys
import boto3
import subprocess
import random
import string
from uuid import uuid4
from botocore.exceptions import ClientError

delay = 0.4

#----------------------------------------------------------------------------------------------

AWS_ACCOUNT = {
    "PRODUCTION" : "968160390857",
    "DEVELOPMENT" : "228238923779",
    "TEST" : "708005179201",
    "STAGING" : "115435987888"
}

#Configure following for AWS account and credentials 
# MODIFY : Comment the unused AWS account and Uncomment which user want to use
productionStage= "STAGING"
reg = "us-east-1"

# Staging
aws_id = "AKIAIP5SP75SUEU3CDUQ"
aws_key = "/IRiKlWHq2buTX+ktcHu1Z9CjBlEG1zXZ9CGYIFf"

# Staging Environment
ota_url="https://ocqeuktse0.execute-api.us-east-1.amazonaws.com/v1/onelink-primejr-firmware-staging"
ota_xapi_key="Qe0riZkMAr1FBWeZFcxPC2GGBMDKrtjn7w0IGesd"

#----------------------------------------------------------------------------------------------
Serialization_config_path = "../Serialization_tools/config"
ParingSerialCodes = "../Serialization_tools/config/ParingSerialCodes"
ValidatedDeviceCodes = "../Serialization_tools/config/ValidatedDeviceCodes"

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


print "SCRIPT CLEANUP PRIMERA ESTACION MODELO DOMESTICO CLOVER V.0" + '\n\r'

print "COM used = "+arguments.c
 
from configManager import ConfigManager
credentials = ConfigManager()

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
#       Read Modelo from PIC
#--------------------------------------------------------------------------------------
print "Reading Model from PIC..."
ser.write("RM\r")
time.sleep(0.4)
serial_read(5.0,10.0)
model = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tModel = " + model + "\n"
#----------------------------------------------

model_prefix = ''.join(model.split())[:-5].upper()

#---------------------------------------------------------------------
#           Read the serial number from PIC
#---------------------------------------------------------------------

print "Reading CU300 Mac Address from PIC..."
ser.write("DM\r") 
time.sleep(0.4)
serial_read(5.0,12)
mac = ser.read(ser.inWaiting()).rstrip('\r\n')
print "CU300 Mac Address = " + mac

#---------------------------------------------------------------------
#   Reading HAP Pairing Code from PIC
#---------------------------------------------------------------------
print "Reading HAP Pairing Code from PIC..."
ser.write("DP\r")
time.sleep(delay)
serial_read(5.0,13)
pair = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tHAP Pairing Code = " + pair + "\n"
if pair is None:
	print("Pairing code is NULL")

latestParingCode = ParingSerialCodes + '/' + pair
with open(ParingSerialCodes + '/' + '/%s.txt' % pair) as fp:
    for line in fp:
	line = line.strip().split(':')
	print line[0]
	print line[1]
	serialNumber = line[1]
	if pair == line[0]:
	    print "Found the serial Number Mapping: " + serialNumber + "\n"
	else:
		print "\n\nSerial number is not found\n\n"
		sys.exit(12)
		
print "Reading Serial Number from PIC..."
ser.write("WS," + serialNumber + '\r')
time.sleep(delay)
ser.write("RS\r")
time.sleep(delay)
serial_read(5.0,11)
serialNumber_rb = ser.read(ser.inWaiting()).rstrip('\n\r')
print "\tSerial Number from PIC= " + serialNumber_rb + "\n"
print "\tSerial Number from File= " + serialNumber + "\n"
serialNumber_aws = serialNumber.ljust(24)[:24].strip()
name = serialNumber
print "\tName in Portal = " + name + "\n"

#---------------------------------------------------------------------
#   Reading CryptoKey from PIC
#---------------------------------------------------------------------
print "Reading CryptoKey from PIC..."
ser.write("RK\r")
time.sleep(delay)
serial_read(5.0,14)
crypto = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tCryptoKey = " + crypto + "\n"

#---------------------------------------------------------------------
#   Reading Access Token from PIC
#---------------------------------------------------------------------
print "Reading Access Token from PIC..."
ser.write("RA\r")
time.sleep(delay)
serial_read(5.0,15)
accessToken = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tAccess Token = " + accessToken + "\n"

#---------------------------------------------------------------------
#       Some functions define
#---------------------------------------------------------------------
def check_aws_account(productionStage):
    ret = "0"
	
    try:
        client = boto3.client('iam',
            aws_access_key_id = aws_id,
            aws_secret_access_key = aws_key,
            region_name = reg)
        response = client.list_users()
        production_name = response['Users'][0]['Arn']
        production_name = production_name.split(':')
        production_name = production_name[4]
		
        if AWS_ACCOUNT[productionStage] != production_name:
            print("Device is not setup in your account.")
            print("Please use reprogram the device with your account.")
            print("Current Account", production_name)
            ret = "1"
    except:
		ret = "1"
		print("AWS Connection failure.")

    return ret

def check_serial(serialNumber):
    ret = "0"
	
    try:
        client = boto3.client('iot',
            aws_access_key_id = aws_id,
            aws_secret_access_key = aws_key,
            region_name = reg)
        response = client.describe_thing(
		    thingName = serialNumber)
    except:
	    ret = "1"
		
    return ret

#-----------------------------------------------------------------------------------
#   Check device is registerd on AWS cloud using serial number and check AWS account
#-----------------------------------------------------------------------------------
print("Checking with Environment: {:s}",format(productionStage))
check = check_aws_account(productionStage)
if (check == "1"):
	with open("./output/result_clean_up.txt", "w") as text_file:
		text_file.write("FAIL")
	print("AWS account Validatation Failed:",check)
	ser.close
	sys.exit(17)
else:
   print("AWS account Validated sucessfully:",check)

check1 = check_serial(serialNumber_aws)
if (check1 == "1"):
	with open("./output/result_clean_up.txt", "w") as text_file:
		text_file.write("FAIL")
	print("Serial number/thingName Validation Failed:",check1)
	ser.close
	sys.exit(18)
else:
	print("Serial number ( AWS thingName) Validated sucessfully:",serialNumber_aws , pair)
	latestParingCode = ParingSerialCodes + '/' + '/%s.txt' % pair
	ValidatedDeviceCodes = ValidatedDeviceCodes + '/%s.txt' % pair
	#shutil.move(latestParingCode, ValidatedDeviceCodes)
	shutil.copyfile(latestParingCode, ValidatedDeviceCodes)  
	print("Serial Number Moved sucessfully in ValidatedDeviceCodes directory folder")
#---------------------------------------------------------------------
#  Delete all logs from  TODO - AWS 
#---------------------------------------------------------------------

#----------------------------------------------------------------------
with open("./output/result_clean_up.txt", "w") as text_file:
                text_file.write("PASS")
print("Clean-up completado. Please Remove The Target From The Fixture.")
ser.close()
sys.exit(0)
conn.close()
raw_input("Press Enter to leave program")
