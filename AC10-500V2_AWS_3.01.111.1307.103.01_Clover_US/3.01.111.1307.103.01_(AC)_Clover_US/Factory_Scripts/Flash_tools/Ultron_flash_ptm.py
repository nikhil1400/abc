
###############################################################################
#######     TITLE "Project Clover Radio Board Programming Script"      ########
#######     SUBTITLE "COPYRIGHT 2015 BRK BRANDS, INC., FIRST ALERT"    ########
###############################################################################
#######     MODEL:         AC10-500 DC10-500                           ########
###############################################################################
#######     PROJECT:       ONELINK WiFi Smoke and CO Alarm             ########
#######     FILENAME:      factory_radio_ptm.py                        ########
#######     DATE:          10/8/2015                                   ########
#######     FILE VERSION:  VERSION 1.0                                 ########
#######     SW1 RELEASE:   SW1-0241-000E1 SCRIPT, PRGRM BLE WIFI RADIOS########
#######     AUTHOR:        CHIA-HUA "CHARLIE" LIN                      ########
#######     COMPANY:       BRK BRANDS, INC., FIRST ALERT, INC.         ########
#######                    3901 LIBERTY STREET ROAD                    ########
#######                    AURORA, IL 60504-8122                       ########
###############################################################################
#######     HISTORY:       10/8/2015 FIRST RELEASE                     ########
###############################################################################

import subprocess

##############################   Configuration   ##############################
Num_flasher = 2                   #Number of devices being programmed
#Flasher_list = [164103223, 694000129]        #List all Segger Flasher SN connected 
XDS_list = ['COM9', 'XDS-06EB12201489A']              #LIST all COM ports used for the CC2640 programmer
fo = open("./output/program_log_PTM.txt", "w")   #Output log file location
si = subprocess.STARTUPINFO()
si.dwFlags = subprocess.STARTF_USESTDHANDLES | subprocess.STARTF_USESHOWWINDOW
###################   Program CC2640 PTM  #################################
for i in range(Num_flasher):
    print "Programming CC2640[" + str(i+1) + "]..."
    resp = subprocess.Popen(['C:\\Program Files (x86)\\Texas Instruments\\SmartRF Tools\\Flash Programmer 2\\bin\\srfprog.exe',
                            '-t', 'soc(%s, CC2640)'%XDS_list[i], '-e', '-p', '-v', 'rb',
                            '-f', '.\\PTM_firmware\\Merged_cc2640_PTM.hex'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, startupinfo=si)
    output, error = resp.communicate()
    fo.write("CC2640")
    fo.write("[%d] "%(i+1))
    if error == "":
        print "CC2640 PASS"
        fo.write("PASS\n")
    else:
        print "CC2640 FAIL"
        fo.write("FAIL\n")

fo.close()

###################   Program CU300 PTM   #################################
print "Programming CU300..."
resp = subprocess.call(['Flash_CU300_PTM.bat'])
#raw_input("Process finished. Press Enter to quit... ")

