@echo off
:LOOP
adb shell input tap 100 500
adb shell input tap 500 100
adb shell input tap 300 800
timeout /t 1 >nul
goto LOOP
