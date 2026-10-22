@echo off
setlocal
set "ATHENS_SAMPLE_LOG=%~dp0..\qa\environment\manual"
if not exist "%ATHENS_SAMPLE_LOG%" mkdir "%ATHENS_SAMPLE_LOG%"
if not exist "%~dp0Builds\P0\AthensProduction.exe" (
  echo Build missing. Run production/scripts/environment/build.ps1 first.
  exit /b 1
)
start "Athens Production P0" "%~dp0Builds\P0\AthensProduction.exe" -logFile "%ATHENS_SAMPLE_LOG%\player-latest.log"
endlocal
