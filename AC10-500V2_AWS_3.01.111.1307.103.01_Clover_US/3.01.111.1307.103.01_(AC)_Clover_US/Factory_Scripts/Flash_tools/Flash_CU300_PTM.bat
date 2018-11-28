@ECHO OFF
setlocal
set "lock=%temp%\wait%random%.lock"


start /min "" 9>"%lock%1" StartjFlash_CU300_PTM.bat 164103223
TIMEOUT 1
REM start /min "" 9>"%lock%2" StartjFlash_CU300_PTM.bat 651100174

REM Wait until lock files are released and delete them afterwards
1>nul 2>nul ping /n 3 ::1
for %%N in (1 2) do (
(call ) 9>"%lock%%%N" || goto :Wait
) 2>nul
del "%lock%*"
pause