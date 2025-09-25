@echo off
setlocal enabledelayedexpansion

:: MAC que quieres buscar
set "TARGET_MAC=38-54-39-6a-da-97"
set "ENCONTRADA=0"

echo Buscando IP con MAC: %TARGET_MAC%
echo.
echo IP:               MAC:
echo -------------------------------

:: Escanear ambos rangos
call :scan_rango 14.10.10.
call :scan_rango 14.10.10.

:: Si no se encontró
if "%ENCONTRADA%"=="0" (
    echo.
    echo No se encontró la MAC especificada.
    pause
    exit /b
)

:CONECTAR
echo.
echo Conectando con ADB a %IP_ENCONTRADA%...
adb connect %IP_ENCONTRADA% >nul
timeout /t 2 >nul
start "" scrcpy
exit

:: ---------- FUNCIONES ------------

:scan_rango
set "BASE=%~1"
for /L %%i in (1,1,254) do (
    set "IP=%BASE%%%i"
    ping -n 1 -w 100 !IP! >nul

    for /f "tokens=1,2" %%a in ('arp -a ^| findstr !IP!') do (
        set "CURRENT_IP=%%a"
        set "CURRENT_MAC=%%b"
        call :print_alineado
        if /I "%%b"=="%TARGET_MAC%" (
            set "ENCONTRADA=1"
            set "IP_ENCONTRADA=%%a"
            goto :CONECTAR
        )
    )
)
exit /b

:print_alineado
:: Añadir espacios hasta 17 caracteres
set "LINE=IP: !CURRENT_IP!"
set "LINE=!LINE!                  "
set "LINE=!LINE:~0,20!"
echo !LINE!MAC: !CURRENT_MAC!
exit /b
