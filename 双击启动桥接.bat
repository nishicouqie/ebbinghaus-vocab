@echo off
title edge-tts bridge (keep this window open)
cd /d "%~dp0"
set PY=
python -V >nul 2>nul
if not errorlevel 1 set PY=python
if defined PY goto found
py -V >nul 2>nul
if not errorlevel 1 set PY=py
:found
if not defined PY goto nopy
if not exist "edge-tts-bridge.py" goto nofile
%PY% "edge-tts-bridge.py"
pause
exit /b 0
:nopy
echo Python not found. Install Python from python.org and check "Add to PATH".
pause
exit /b 1
:nofile
echo edge-tts-bridge.py not found. Put it in the same folder as this launcher (download both from the web page).
pause
exit /b 1