:loop
adb shell cmd statusbar expand-notifications
timeout /t 1 >nul
adb shell cmd statusbar collapse
timeout /t 1 >nul
goto loop
