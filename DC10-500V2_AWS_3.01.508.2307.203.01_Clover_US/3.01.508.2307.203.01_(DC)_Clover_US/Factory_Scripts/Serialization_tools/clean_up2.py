###############################################################################
#######     TITLE "Project Clover Radio Board Programming Script"      ########
#######     SUBTITLE "COPYRIGHT 2015 BRK BRANDS, INC., FIRST ALERT"    ########
###############################################################################
#######     MODEL:         AC10-500 DC10-500                           ########
###############################################################################
#######     PROJECT:       ONELINK WiFi Smoke and CO Alarm             ########
#######     FILENAME:      clean_up.py                            ########
#######     DATE:          10/16/2015                                   ########
#######     FILE VERSION:  VERSION 1.0                                 ########
#######     SW1 RELEASE:   SW1-0242-000E1 SCRIPT, PRGRM BLE WIFI RADIOS########
#######     AUTHOR:        CHIA-HUA "CHARLIE" LIN                      ########
#######     COMPANY:       BRK BRANDS, INC., FIRST ALERT, INC.         ########
#######                    3901 LIBERTY STREET ROAD                    ########
#######                    AURORA, IL 60504-8122                       ########
###############################################################################
#######     HISTORY:       10/8/2015 FIRST RELEASE                     ########
#######                    10/16/2015 Reduced delay bewteen commands,  ########
#######                               detects CLRD for target removal  ########
###############################################################################

import argparse
import requests
import uuid
import serial
import time
import json
import urllib
import httplib

from configManager import ConfigManager
credentials = ConfigManager()

BASE_API_URL = credentials.configData[ConfigManager.ADMIN_URL_KEY]+"/provision/manage/model/"
API_TOKEN = credentials.configData[ConfigManager.API_TOKEN_KEY]

BASE_URL = credentials.configData[ConfigManager.PORTAL_URL_KEY]

USERNAME = credentials.configData[ConfigManager.USERNAME_KEY]
PASS = credentials.configData[ConfigManager.PASSWORD_KEY]

ser = serial.Serial("/dev/tty.usbserial-FT99JMNX") #Please Change COM Port Here

#ser = serial.Serial("/dev/tty.usbserial-FTF6CS19") #Opens Serial Port
ser.baudrate = 9600
#print ser.portstr       # check which port was used

delay = 0.5

with open("./output/result_clean_up.txt", "w") as text_file:
    text_file.write("FAIL")
print ""
print "Starting Clean Up Process..."
print ""
print "Please connect Clover(power on), connect N40 to Ground, and connect battery and the radio board..."
substring = "Fac"
substring1 = "F"
substring2 = "Fa"
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
ser.write("RM\n\r")#Get rid of junk in the buffer
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
modelVoid = ser.read(ser.inWaiting())

print "Reading Model from PIC..."
ser.write("RM\r")
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
model = ser.read(ser.inWaiting()).rstrip('\r\n')
model = model + 'V2'
print "\tModel = " + model + "\n"

model_prefix = ''.join(model.split())[:-5].upper()

print "Reading Serial Number from PIC..."
ser.write("RS\r")
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
serialNumber = str(ser.read(ser.inWaiting()).upper().rstrip('\r\n'))
print "\tSerial Number = " + serialNumber + "\n"

print "Reading CU300 Mac Address from PIC..."
ser.write("DM\r")
time.sleep(delay)
while ser.inWaiting() == 0:
   pass
mac = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tCU300 Mac Address = " + mac + "\n"

mac_last4 = ''.join(mac.split())[8:].upper()

print "Reading HAP Pairing Code from PIC..."
ser.write("DP\r")
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
pair = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tHAP Pairing Code = " + pair + "\n"

name = serialNumber
print "\tName in Portal = " + name + "\n"

print "Reading CryptoKey from PIC..."
ser.write("RK\r")
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
crypto = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tCryptoKey = " + crypto + "\n"

print "Reading Access Token from PIC..."
ser.write("RA\r")
time.sleep(delay)
while ser.inWaiting() == 0:
    pass
accessToken = ser.read(ser.inWaiting()).rstrip('\r\n')
print "\tAccess Token = " + accessToken + "\n"

# print "Reading Advertised name from PIC..."
# ser.write("RN\r")
# time.sleep(delay)
# while ser.inWaiting() == 0:
#     pass
# advertisedName = ser.read(ser.inWaiting()).rstrip('\r\n')
# print "\tAdvertised Name = " + advertisedName + "\n"

def getUrlForRIDCall(Model, SN):
    string_1 = BASE_API_URL + Model + '/' + SN
    return string_1

def name_device(rid):
    url = BASE_URL + "/api/portals/v1/devices/" + rid
    headers = { "Content-Type": "application/x-www-form-urlencoded"}
    data1 = {"info": {"description":{"name":name}}}
    data2 = json.dumps(data1)
    return requests.put(url, headers=headers, data=data2, auth=requests.auth.HTTPBasicAuth(USERNAME, PASS), timeout = 10)

def get_device(rid):
    url = BASE_URL + "/api/portals/v1/devices/" + rid
    headers = { "Content-Type": "application/x-www-form-urlencoded"}
    data1 = {}
    data2 = json.dumps(data1)
    return requests.get(url, headers=headers, data=data2, auth=requests.auth.HTTPBasicAuth(USERNAME, PASS), timeout = 10)

headers = {"X-Exosite-Token": API_TOKEN}
try:
    response = requests.get(getUrlForRIDCall(model, serialNumber), headers=headers)
except requests.exceptions.ConnectionError as e:
    print("Error: No Internet Connection. Press any key to leave program...")
    exit()
if response.status_code == 404:
    with open("./output/result_clean_up.txt", "w") as text_file:
        text_file.write("FAIL")
    print "Serial number not registered"
else:
    resp = response.text
    status = resp.split(",")[0]
    print status
    if status == "notactivated":
        with open("./output/result_clean_up.txt", "w") as text_file:
            text_file.write("FAIL")

    RID = resp.split(",")[1]
    print "\tDevice RID = " + RID + "\n"
    print "Updating Name in Exosite Portal ... "
    try:
        resp_rename = name_device(RID).status_code
    except requests.exceptions.ConnectionError as e:
        print("Error: No Internet Connection. Press any key to leave program...")
        exit()
    print "\t" + str(resp_rename)
    if resp_rename!= 200:
        raw_input("Script terminated....Failed to rename device on the Cloud.")
        exit()
    resp_getCIK = get_device(RID)
    info = json.loads(resp_getCIK.text)
    cik = info["info"]["key"]
    print "\tDevice CIK = " + cik + "\n"

    server = 'm2.exosite.com'
    http_port = 80

    url = '/api:v1/stack/alias?device_ckey&device_access_token'
    headers = {'Accept':'application/x-www-form-urlencoded; charset=utf-8','X-Exosite-CIK':cik}
    conn = httplib.HTTPConnection(server,http_port)
    conn.request("GET",url,"",headers)
    response = conn.getresponse();
    data = response.read()
    conn.close()

    print response.status

    if response.status == 204:
        with open("./output/result_clean_up.txt", "w") as text_file:
            text_file.write("FAIL")

        print "ERROR: CryptoKEY and Access Token Not Uploaded!!!"
    elif response.status == 200:
        flag1 = 0
        flag2 = 0
        str1 = urllib.unquote(data)
        print str1
        device_access_token = str1.split("&")[0]
        if device_access_token == "":
            with open("./output/result_clean_up.txt", "w") as text_file:
                text_file.write("FAIL")
            print "Error: Access Token Does Not Exist!!!"
        else:
            token = device_access_token.split("=")[1]
            if token == accessToken:
                print "\tAccess Token Matching: " + token
                flag1 = 1
            else:
                with open("./output/result_clean_up.txt", "w") as text_file:
                    text_file.write("FAIL")
                print "Error: Non Matching Access Token!!!"

        device_ckey = str1.split("&")[1]
        if device_ckey == "":
            with open("./output/result_clean_up.txt", "w") as text_file:
                text_file.write("FAIL")
            print "Error: CryptoKey Does Not Exist!!!"
        else:
            ckey = device_ckey.split("=")[1]
            if ckey == crypto:
                print "\tCryptoKey Matching: " + ckey + "\n"
                flag2 = 1
            else:
                with open("./output/result_clean_up.txt", "w") as text_file:
                    text_file.write("FAIL")
                print "Error: Non Matching CryptoKey!!!"

        if (flag1 == 1) and (flag2 == 1):
            print "Deleting Factory Event Log..."
            #RPC API FLUSH
            url = '/onep:v1/rpc/process'
            headers = {'Host': 'm2.exosite.com:80', 'Content-Type':'application/json; charset=utf-8'}
            body = json.dumps({'auth':{'cik': cik}, 'calls': [{'procedure': 'flush', 'arguments': [{'alias': 'device_event_log'}], 'id': 1}]})
            #print body
            conn = httplib.HTTPConnection(server,http_port)
            conn.request("POST",url,body,headers)
            response = conn.getresponse()
            data = json.loads(response.read())
            conn.close()
            if response.status == 200 and data[0]['status'] == "ok":
                print "Event Log Flushed"
            else:
                print "Event Log not Flushed"
            with open("./output/result_clean_up.txt", "w") as text_file:
                text_file.write("PASS")
            print "Resetting Target..."
            ser.write("RR\r")
            time.sleep(delay)
            raw_input("Clean-up Completed. Please Remove The Target From The Fixture.")


            #substring = "CLR"
            #substring1 = "C"
            #substring2 = "CL"
            #string = ""
            #while True:
            #    while ser.inWaiting() == 0:
            #        pass
            #    string = ser.read(ser.inWaiting())
            #    #print string
            #    if substring in string:
            #        raw_input("Clean-up Completed. Please Remove The Target From The Fixture.")
            #        break
            #    if substring1 in string:
            #        substring = "LR"
            #    if substring2 in string:
            #        substring = "R"

    else:
        with open("./output/result_clean_up.txt", "w") as text_file:
            text_file.write("FAIL")
        print "ERROR: Connot Access Exosite Portal!!!(Serial Number May Not Be Correct)"

ser.close()
#raw_input("Press Enter to leave program")
