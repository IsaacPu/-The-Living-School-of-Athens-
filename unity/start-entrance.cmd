@echo off
setlocal
cd /d "%~dp0"
if not exist "Builds\Entrance\AthensEntrance.exe" (
  echo Entrance Player not built. Run scripts\environment\build-entrance.ps1 from the worktree root.
  pause
  exit /b 1
)
if not exist "..\qa\environment\entrance\interactive" mkdir "..\qa\environment\entrance\interactive"
start "" "Builds\Entrance\AthensEntrance.exe" -force-d3d11 -screen-fullscreen 0 -screen-width 1440 -screen-height 1080 -logFile "%~dp0..\qa\environment\entrance\interactive\player.log"
endlocal
