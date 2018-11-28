import json
from Crypto.Cipher import AES
import base64
import os

def encryption(privateInfo):
        BLOCK_SIZE = 32
        PADDING = '*'
        pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
        EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))

        cipher = AES.new(pad(passphrase))
        encoded = EncodeAES(cipher, privateInfo)
        return encoded

#passphrase = raw_input("Please input a passphrase, note you will need this to run the scripts later")
passphrase = "123"
#build the dictionary of credential information
credentials = {}
credentials['username'] = raw_input("Please Input a Username: ")
credentials['password'] = raw_input("Please input your password: ")
credentials['api_token'] = raw_input("Please input your API token: ")

while True:
        option = raw_input("Is this config for pilot run? (Y/N)? ")
        #standby = raw_input("I'll just hold onto this for you ")
        #break
        
        
        if option == "Y":
                credentials['pilot'] = "1"
                credentials['vendor'] = "jssdev"
                credentials['admin_base_url'] = "https://jssdev.m2.exosite.com"
                credentials['portal_base_url'] = "https://jssdev.exosite.com"
                
                credentials['AC_DEV'] = raw_input("Input AC10-500 Dev Portal ID: ")
                credentials['DC_DEV'] = raw_input("Input DC10-500 Dev Portal ID: ")
                credentials['GLO_DEV'] = raw_input("Input GLOCO-500 Dev Portal ID: ")
                
                credentials['AC_PROD'] = ""
                credentials['DC_PROD'] = ""
                break
                
        elif option == "N":
                credentials['pilot'] = "0"
                credentials['vendor'] = "cloud_onelink_firstalert"
                credentials['admin_base_url'] = "https://m2.exosite.com"
                #credentials['admin_base_url'] = "https://cloud_onelink_firstalert.m2.exosite.com"
                credentials['portal_base_url'] = "https://cloud.onelink.firstalert.com"
                
                #option_AC_PROD =  raw_input("Input AC10-500 Product Portal")
                credentials['AC_PROD'] = raw_input("Input AC10-500 Product Portal ID: ")
                 
                #option_DC_PROD = raw_input("Input DC10-500 PROD Portal")
                credentials['DC_PROD'] = raw_input("Input DC10-500 product Portal ID: ")
                
                credentials['AC_DEV'] = ""
                credentials['DC_DEV'] = ""
                break
        

        else:
                print "Invalid Answer"


print "Encrypting data......."
#convert the dictionary to string, then encrypt
encryptedInfo = encryption(json.dumps(credentials))

print "Writing data to file config.json"
#write the encrypted info to a file
f = open('./config/config.json', 'w')
f.write(encryptedInfo)
f.close()

print "Success, config.json created" 