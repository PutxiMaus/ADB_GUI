@echo off
echo YEAH

:loop
echo - Girando pantalla...
adb shell settings put system user_rotation 1
adb shell settings put system accelerometer_rotation 0
timeout /t 1 >nul

adb shell settings put system user_rotation 3
timeout /t 1 >nul

adb shell settings put system user_rotation 0
timeout /t 1 >nul

adb shell settings put system user_rotation 2
timeout /t 1 >nul

echo - Cambiando brillo...
for /L %%B in (0,20,255) do (
    adb shell settings put system screen_brightness %%B
    timeout /t 1 >nul
)

echo - Simulando toques aleatorios...
for /L %%X in (1,1,10) do (
    set /a xpos=!random! %% 1080
    set /a ypos=!random! %% 1920
    adb shell input tap !xpos! !ypos!
    timeout /t 1 >nul
)

goto loop
