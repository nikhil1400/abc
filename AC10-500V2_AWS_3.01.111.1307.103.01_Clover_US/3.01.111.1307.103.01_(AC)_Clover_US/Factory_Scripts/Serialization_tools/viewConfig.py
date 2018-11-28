from Crypto.Cipher import AES
import os
import base64


def decrypt(key,data):
	BLOCK_SIZE = 32
	PADDING = "*"
	DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
	pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
	cipher = AES.new(pad(key))
	decoded = DecodeAES(cipher, data)
	print decoded

try:
	file_data = open('./config/config.json', 'r')	
except IOError:
	print "Error you need generate a config.json and have it in the same directory as this script"
else:
	data = file_data.read()
	key = raw_input("PASSWORD:")
	decrypt(key, data)
	file_data.close()
raw_input("Press any key to quit...")
