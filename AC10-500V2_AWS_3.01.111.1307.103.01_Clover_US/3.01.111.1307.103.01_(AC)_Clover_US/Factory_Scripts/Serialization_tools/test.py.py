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
import re

ver_CC2640 = "2.13.60"
BLEVERSION = ver_CC2640[2] + ver_CC2640[3] + ver_CC2640[4] + ver_CC2640[5] + ver_CC2640[6]
BLEVERSION = BLEVERSION.replace('.', '')
print BLEVERSION