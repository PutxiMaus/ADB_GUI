@echo off
rem Enviar la imagen al dispositivo Android a /data/local/tmp/
echo Enviando imagen a /data/local/tmp...
adb push "C:\Users\jsole\Downloads\thumbnail_image.png" /data/local/tmp/
if %errorlevel% neq 0 (
    echo Error al enviar la imagen. Comprueba si el dispositivo esta conectado y prueba de nuevo.
    pause
    exit /b
)

rem Actualizar la base de datos de medios para que Android reconozca el archivo
echo Actualizando base de datos de medios...
adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file:///data/local/tmp/thumbnail_image.png"
if %errorlevel% neq 0 (
    echo Error al actualizar la base de datos de medios. Asegúrate de que el dispositivo esté conectado y de que la ruta sea correcta.
    pause
    exit /b
)

rem Intentar abrir la imagen en el dispositivo desde /data/local/tmp/
echo Intentando abrir la imagen...
adb shell am start -a android.intent.action.VIEW -d "file:///data/local/tmp/thumbnail_image.png" -t "image/*"
if %errorlevel% neq 0 (
    echo Error al abrir la imagen. Asegúrate de que la ruta y el archivo son correctos.
    pause
    exit /b
)

echo Imagen enviada y abierta correctamente.
pause
