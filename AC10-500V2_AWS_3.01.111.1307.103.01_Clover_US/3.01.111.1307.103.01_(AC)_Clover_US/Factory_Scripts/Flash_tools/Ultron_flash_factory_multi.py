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

from Naked.toolshed.shell import execute_js
import sys
import csv
import subprocess
import os

import serial
import time
import threading
import sys
import boto3
import subprocess
import random
import string
import json
import uuid
from uuid import uuid4
from botocore.exceptions import ClientError

##############################   Configuration   ##############################
Num_flasher = 4
flash_cc2640 = "y"
flash_cu300 = "y"
XDS_list = ["COM4"]   
ver_CC2640 = "2.13.07"
ver_cu300 = "103"           
log_file = "./output/program_log.txt"    
JFlash_path = "C:\\Program Files (x86)\\SEGGER\\JLink_V632\\JFlash.exe"
Flash_Programmer_2_path = "C:\\Program Files (x86)\\Texas Instruments\\SmartRF Tools\\Flash Programmer 2\\bin\\srfprog.exe"
Serialization_config_path = "../Serialization_tools/config"
ParingSerialCodes = "../Serialization_tools/config/ParingSerialCodes"
BleVersion_config_path = "../Serialization_tools/config/BLEVersion"
BLEVERSION = ver_CC2640[2] + ver_CC2640[3] + ver_CC2640[4] + ver_CC2640[5] + ver_CC2640[6]
BLEVERSION = BLEVERSION.replace('.', '')
fo = open(BleVersion_config_path, "w")
fo.write(BLEVERSION)
fo.close()

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

def aws_script(serial_num, hardwareType):
    client = boto3.client('iot',
        aws_access_key_id = aws_id,
        aws_secret_access_key = aws_key,
        region_name = reg)

    try:
        response1 = client.list_thing_principals(
            thingName = serial_num)

        for each in response1['principals']:
            cert = each.split('/')
            cert = cert[1]
            response2 = client.update_certificate(
                certificateId = cert,
                newStatus = 'INACTIVE')
            try:
                response2 = client.detach_principal_policy(
                    policyName = 'ThingBasedPolicy',
                    principal = each)
            except:
                try:
                    response2 = client.detach_principal_policy(
                        policyName = 'ThingBasedPolicy',
                        principal = each)
                except:
                    print("Policy Not Found.")

            response2 = client.detach_thing_principal(
                thingName = serial_num,
                principal = each)
            response2 = client.delete_certificate(
                certificateId = cert)
                #forceDelete = True)

        response2 = client.delete_thing(
            thingName = serial_num)
        print("Old device deleted from AWS Cloud.")
    except Exception as e:
        #print()
        #print(e)
        #print()
        print("Multiple/New Device Cert will generated on AWS")

    response_thing = client.create_thing(
        thingName = serial_num,
        thingTypeName = hardwareType,
        attributePayload = {'attributes' : {
                'hardwareVersion' : "3",
                'modelId' : "1042135",
                'pairingCode' : str(pins[i])
            }
            }
        )
    print("Device Created on AWS Cloud.")

    response_key_certificate = client.create_keys_and_certificate(
        setAsActive = True)
    response_policy = client.attach_principal_policy(
        policyName = "ThingBasedPolicy",
        principal = response_key_certificate['certificateArn'])
    response_principal = client.attach_thing_principal(
        thingName = serial_num,
        principal = response_key_certificate['certificateArn'])

    data = {"state" :
        {
            "desired" : {
                "otaFirmwareVersion" : "",
                "otaCheck" : False
            },
            "reported" : {
                "otaFirmwareVersion" : "",
                "otaCheck" : False
            }
        }
    }

    return response_key_certificate['certificatePem'], response_key_certificate['keyPair']['PrivateKey'], response_key_certificate['certificateArn']

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


#####################     Initialize the factory log     ######################
if not os.path.exists("./output/"):
    os.makedirs("./output/")
if not os.path.exists("./output/"):
    print ("directorio output no creado")
    sys.exit(9)
fo = open(log_file, "w")
fo.write("Device not programmed!!")
fo.close()

#####################     Check AWS Account     ######################
print_string = "Production Environment: {:s}".format(productionStage)

check = check_aws_account(productionStage)
if (check == "1"):
	sys.exit()

#####################   Generate Homekit Pairing PIN   #######################

success = execute_js('homekit-pingen-Charlie.js %d' % Num_flasher)
if success:
    print("Homekit Pairing PINs generated")
else:
    print("Homekit Pairing PINs generation failed!!")
    sys.exit()
    
#####################   Read Homekit PIN from the file   #####################
pins = []
if not os.path.exists("./temp/"):
    os.makedirs("./temp/")
fo = open("./temp/HKPins.txt", "r")
print "Loading Homekit Pairing codes from file: ", fo.name
for i in range(Num_flasher):
    line = fo.readline()
    line = line.translate(None, ''.join("\n"))
    print "Read Line: %s" % line
    pins.append(line)
fo.close
print pins
#####################   Generate .CSV file   ##################################
csv_file = open("./temp/product.csv", "wb")
try:
    writer = csv.writer(csv_file)
    writer.writerow(('app_hk.num_acc', 'app_hk.num_serv', 'app_hk.num_char', 'app_hk.prov_pin', 'system.proto_uart_baudrate',
                     'system.proto_uart_flow_control', 'system.proto_uart_id', 'system.debug_uart_id', 'system.ble_uart_id',
                     'system.ble_uart_baudrate', 'system.pm_ext_gpio', 'system.pm_ext_gpio_level', 'temporary.pin', 'wlan.region_code',
		     'ble.cid', 'ble.name', 'ble.ail', 'jarden.vendorid', 'hap.acc_info.manufacturer', 'hap.acc_info.model',
		     'hap.acc_info.name', 'hap.acc_info.serial_no', 'hap.acc_info.fw_rev', 'hap.services', 'acc_info.uuid',
		     'acc_info.sid', 'acc_info.char', 'acc_info.name.uuid', 'acc_info.name.property', 'acc_info.name.iid',
		     'acc_info.manufacturer.uuid', 'acc_info.manufacturer.property', 'acc_info.manufacturer.iid', 'acc_info.model.uuid',
                     'acc_info.model.property', 'acc_info.model.iid', 'acc_info.serial_no.uuid', 'acc_info.serial_no.property',
                     'acc_info.serial_no.iid', 'acc_info.identify.uuid', 'acc_info.identify.property', 'acc_info.identify.iid',
                     'acc_info.fw_rev.uuid', 'acc_info.fw_rev.property', 'acc_info.fw_rev.iid', 'acc_info.prop.uuid', 'acc_info.prop.property',
                     'acc_info.prop.iid', 'acc_info.srv_inst.uuid', 'acc_info.srv_inst.property', 'acc_info.srv_inst.iid',

                     'pairing.uuid', 'pairing.sid', 'pairing.char', 'pairing.pair_setup.uuid', 'pairing.pair_setup.property',
                     'pairing.pair_setup.iid', 'pairing.pair_verify.uuid', 'pairing.pair_verify.property', 'pairing.pair_verify.iid',
                     'pairing.features.uuid', 'pairing.features.property', 'pairing.features.iid', 'pairing.pairings.uuid',
                     'pairing.pairings.property', 'pairing.pairings.iid', 'pairing.srv_inst.uuid', 'pairing.srv_inst.property',
                     'pairing.srv_inst.iid', 'proto_info.uuid', 'proto_info.sid', 'proto_info.char', 'proto_info.version.uuid',
                     'proto_info.version.property', 'proto_info.version.iid', 'proto_info.srv_inst.uuid', 'proto_info.srv_inst.property',
                     'proto_info.srv_inst.iid', 'fwupg_verification_key',
                     'fwupg_encrypt_decrypt_key', 'fwupg_ota_url', 'fwupg_xapi_key', 'homekit.pin'))
    for i in range(Num_flasher):
		serialNumber = str(uuid.uuid4()).translate(None, ''.join("-")).upper()
		serialNumber_aws = serialNumber.ljust(24)[:24].strip()
		serialNumber  = serialNumber_aws
		hardwareType = "PrimeJrHardwire"
		writer.writerow(('3', '10', '55', 'ed8b4ccf9c1876f233ff0dc5c5d2b76a2b3cae87', '9600',
                         'none', '0', '1', '2',
                         '115200', '11', '0', pins[i], 'US',
                         '10', 'LightBulb-010203', '2D', 'jssdev', 'FirstAlert', 'AC10',
                         'Onelink Alarm', serialNumber, '2.0', 'acc_info:pairing:proto_info:smoke:co:onelink:firmware:battery:nightlight', '3E',
                         '1', 'name:manufacturer:model:serial_no:identify:fw_rev:prop:srv_inst', '23', '2', '2',
                         '20', '2', '3', '21',
                         '2', '4', '30', '2',
                         '5', '14', '8', '6',
                         '52', '2', '7', 'A6', '26',
                         '50', 'E604E95DA759481787D3AA005083A0D1', '2', '51',
                         
                         '55', '9', 'pair_setup:pair_verify:features:pairings:srv_inst', '4c', 'a',
                         '10', '4e', 'a', '11',
                         '4f', '2', '12', '50',
                         'a', '13', 'E604E95DA759481787D3AA005083A0D1', '2',
                         '52', 'A2', '53', 'version:srv_inst', '37',
                         '2', '54', 'E604E95DA759481787D3AA005083A0D1', '2',
                         '55', ':f5dd917b920128f4a0ede8e41108c10d1267466794165a73d918747c2f8ca70d',
                         ':9222e4c5c23e96f702d39568646357071e432f847d31c4f19a90c8807932680f',ota_url, ota_xapi_key, pins[i]))

		print "Creating the Device on Cloud..."
		aws_certification, aws_private_key, aws_certName = aws_script(serialNumber_aws,hardwareType)
		#print("Serial number:" + serialNumber_aws)
		#print("Certificate:" + aws_certification)
		#print("PrivateKey:" + aws_private_key)
		fo = open('./temp/CloverCert-%d.bin' % (i+1), "w")
		fo.write(aws_certification + aws_private_key)
		fo.close()
		print("Generated AWS Certificate file: " + './temp/CloverCert-%d.bin' % (i+1))
		
		fo = open(ParingSerialCodes +'/%s.txt' % pins[i], "w")
		fo.write(pins[i] + ':' + serialNumber)
		fo.close()
		print("Generated Serial Number config file: " + ParingSerialCodes +'/serialNo-%d.txt' % (i+1))

		with open(ParingSerialCodes + '/%s.txt' % pins[i]) as fp:
		    for line in fp:
			print line

finally:
    csv_file.close()
    print("csv file created")
######################   Generate mfg.bin   ####################################
success = execute_js('mfg-creator.js --db temp/product.csv --cfg product.config --outdir temp/')
if success:
    print("mfg files generated")
else:
    print("mfg files generation failed!!")
    sys.exit(1)

###################   Merge mfg.bin and fatory.bin   #########################
'''
si = subprocess.STARTUPINFO()
si.dwFlags = subprocess.STARTF_USESTDHANDLES | subprocess.STARTF_USESHOWWINDOW
for i in range(Num_flasher):
    print "loop ."
    resp = subprocess.call([JFlash_path, '-open.\\..\\CU300_bin_merger\\bin_%s\\factory_%s.bin,0x00000000'%(ver_cu300, ver_cu300),
                            '-merge.\\temp\\mfg-%d.bin,0x6000' % (i+1), '-merge.\\temp\\CloverCert-%d.bin,0x1D3000' % (i+1), '-saveas.\\output\\final-%s.bin,0x0,0x1D9000' % (i+1),
                            '-exit'], startupinfo=si)
    if resp == 0:
        print "final image-" + str(i+1) + " created"

    else:
        print "final image-" + str(i+1) + " generation failed!"
        print "bin files merging failed!!"
        sys.exit()
print "saliendo de merge routine"
#####################   Program CC2640   #################################
print "entrando a program cc2640"
if flash_cc2640 == "y":
    bin_CC2640 = '.\\..\\CC2640_fw\\cc2640_merged_' + ver_CC2640.replace('.', '_') + '.hex'
    print bin_CC2640
    fo = open(log_file, "w")
    print 'entrando en loop'
    for i in range(Num_flasher):
        print "Programming CC2640[" + str(i+1) + "]...",
        print Flash_Programmer_2_path
        resp = subprocess.Popen([Flash_Programmer_2_path,
                                 '-t', 'soc(%s, CC2640)'%XDS_list[i], '-e', '-p', '-v', 'rb',
                                 '-f', bin_CC2640], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, startupinfo=si)
        output, error = resp.communicate()
        fo.write("CC2640 ")
        fo.write("[%d] "%(i+1))
        if error == "":
            print "PASS"
            fo.write("PASS\n")
        else:
            print "FAIL"
            print "ERROR: " + error
            fo.write("FAIL\n")
    fo.close()
        
#####################   Program CU300 #################################
if flash_cu300 == "y":
    resp = subprocess.call(['Flash_CU300.bat'])
    if resp == 1:
        print "CU300 PASS"
    else:
        print "CU300 FAIL"
 
'''
