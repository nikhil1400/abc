import zipfile
import sys
import subprocess
import os
from Naked.toolshed.shell import execute_js

fw = raw_input("Please input CU300 firmware version: ")
jflash_ver = raw_input("Please input jFlash version (e.g. V500i): ")
#print str(sys.argv)
#zip = zipfile.ZipFile(str(sys.argv[1]))
zip_file = "build_" + fw + ".zip"
try:
    zip = zipfile.ZipFile(zip_file)
    zip.extractall(r'.\source')
except:
    print("Can't find zip file: %s" %zip_file)
    sys.exit()
####################   Generate layout.bin   ####################################
cmd1 = 'gen_layout.js --inf source/merge_files/layout_mw300_rd.txt --outf source/merge_files/layout.bin'
#print cmd1
success = execute_js(cmd1)
if success:
    print("layout.bin generated")
else:
    print("layout.bin generation failed!!")
    sys.exit()

####################   Generate wifi.bin   ####################################
cmd2 = 'gen_wifi_fw.js --inf source/merge_files/mw30x_uapsta_14.76.36.p103.bin --outf source/merge_files/wifi.bin'
#print cmd2
success = execute_js(cmd2)
if success:
    print("wifi.bin generated")
else:
    sys.exit("wifi.bin generation failed!!")

###################   Rename ftfs   #########################
try:
    os.remove("source/merge_files/serial_mwm_ftfs.bin")
except:
    pass
    #print("serial_mwm_ftfs.bin does not exist")
os.rename("source/merge_files/serial_mwm.ftfs", "source/merge_files/serial_mwm_ftfs.bin")
###################   Merge binary files   #########################
resp = subprocess.call(['C:\\Program Files (x86)\\SEGGER\\JLink_%s\\JFlash.exe'%jflash_ver,
                        '-open.\\source\\merge_files\\boot2.bin,0x0000',
                        '-merge.\\source\\merge_files\\layout.bin,0x4000',
                        '-merge.\\source\\merge_files\\layout.bin,0x5000',
                        '-merge.\\source\\merge_files\\serial_mwm.bin,0xA000',
                        '-merge.\\source\\merge_files\\serial_mwm.bin,0x83000',
                        '-merge.\\source\\merge_files\\wifi.bin,0xFC000',
                        '-merge.\\source\\merge_files\\ed25519-data.bin,0x13D000',
                        '-merge.\\source\\merge_files\\serial_mwm_ftfs.bin,0x143000',
                        '-saveas.\\bin_%s\\factory_%s.bin,0x0,0x1D9000'%(fw, fw),
                        '-exit'])
if resp == 0:
    print "factory_%s.bin created."%fw
else:
    print "binary files merging failed!"
    sys.exit("binary files merging failed!!")

