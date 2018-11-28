@ECHO OFF
REM ECHO Open a project and data file and exit
start /min /wait "J-Flash" "C:\Program Files (x86)\SEGGER\JLink_V500i\JFlash.exe" -usb%1 -openprj.\MW300_Segger\Marvell_MW300_ExtQSPI.jflash -open.\PTM_firmware\Merged_CU300_PTM.bin,0x1F000000 -auto -exit

IF ERRORLEVEL 1 goto ERROR
goto END
:ERROR
ECHO %ERRORLEVEL%
ECHO J-Flash: Error! SN: %1
@echo CU300[%2] FAIL %ERRORLEVEL%>> .\output\program_log_PTM.txt
exit
:END
ECHO J-Flash: Succeed!
@echo CU300[%2] PASS >> .\output\program_log_PTM.txt
exit
Note: