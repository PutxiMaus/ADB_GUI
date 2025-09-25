@echo off
rem Obtén el nombre del paquete de la aplicación en uso
for /f "tokens=2 delims==" %%a in ('adb shell dumpsys activity activities ^| findstr mResumedActivity') do set package=%%a

rem Verifica si se ha encontrado el paquete
if "%package%"=="" (
    echo No se pudo obtener el nombre del paquete.
    pause
    exit /b
)

rem Elimina posibles espacios extras en el nombre del paquete
set package=%package:~1%

rem Cierra la aplicación en uso
adb shell am force-stop %package%

pause
