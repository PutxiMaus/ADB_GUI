@echo off
setlocal enabledelayedexpansion

:: URL del vídeo de YouTube (cambia esto si quieres)
set VIDEO_URL=https://www.youtube.com/watch?v=dQw4w9WgXcQ

:: Coordenadas (ajústalas a la resolución de tu móvil)
set SALTAR_X=1200
set SALTAR_Y=180
set FULLSCREEN_X=1900
set FULLSCREEN_Y=1000

:LOOP
echo Abriendo vídeo en YouTube...
adb shell am start -a android.intent.action.VIEW -d %VIDEO_URL%

echo Esperando que cargue el vídeo...
timeout /t 7 >nul

echo Intentando saltar anuncio...
adb shell input tap %SALTAR_X% %SALTAR_Y%
timeout /t 1 >nul

echo Poniendo en pantalla completa...
adb shell input tap %FULLSCREEN_X% %FULLSCREEN_Y%

echo Esperando 30 segundos de reproducción...
timeout /t 30 >nul

echo Cerrando vídeo...
adb shell input keyevent 4

timeout /t 90 >nul
goto LOOP
