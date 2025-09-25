@echo off
:LOOP
adb shell input keyevent 26
timeout /t 5 >nul
adb shell input keyevent 26
timeout /t 5 >nul
adb shell input keyevent 26
timeout /t 5 >nul
adb shell input keyevent 26
timeout /t 5 >nul
adb shell input keyevent 26
timeout /t 5 >nul
adb shell input keyevent 26
timeout /t 5 >nul
adb shell input keyevent 26
timeout /t 5 >nul
goto LOOP
