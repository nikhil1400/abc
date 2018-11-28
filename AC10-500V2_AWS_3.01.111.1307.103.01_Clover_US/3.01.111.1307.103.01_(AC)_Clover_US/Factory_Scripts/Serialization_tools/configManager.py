from Crypto.Cipher import AES
import os
import base64
import json
import sys


class ConfigManager:
	USERNAME_KEY = "username"
	PASSWORD_KEY = "password"
	ADMIN_URL_KEY = "admin_base_url"
	PORTAL_URL_KEY = "portal_base_url"
	API_TOKEN_KEY = "api_token"
	VENDOR_KEY = "vendor"
	PILOT_KEY = "pilot"
	
	AC_PROD = "AC_PROD"
	DC_PROD = "DC_PROD"
	AC_DEV = "AC_DEV"
	DC_DEV = "DC_DEV"
	GLO_DEV = "GLO_DEV"


	def __init__(self):
		#key = raw_input("Password: ")
		key = "123"
		self.configData = self.getConfigDictionary(key)

	#This method decrypts the AES data with specified key
	def decrypt(self,key,data):
		BLOCK_SIZE = 32
		PADDING = "*"
		DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
		pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
		cipher = AES.new(pad(key))
		return DecodeAES(cipher, data)
		
	#Fault tolerant file read.  If config.json is not
	#found application will fail gracefully
	def readFile(self):
		data = ''
		try:
			file_data = open('./config/config.json', 'r')
		except IOError:
			print 'You need to generate a config.json file, or make sure your config file is in the config directory'
			#abort the program
			sys.exit()
		else:
			data = file_data.read()
		return data


	def getConfigDictionary(self,key):
		data = self.readFile()
		credString = self.decrypt(key, data)
		creds = {}
		try:
			creds = json.loads(credString)
		except ValueError:
			print "Could not parse json, most likely wrong password"
			sys.exit()
		else:
			return creds