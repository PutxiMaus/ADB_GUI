@echo off
adb shell screencap -p /sdcard/screenshot.png
adb pull /sdcard/screenshot.png C:\ADB\screenshot.png
adb shell rm /sdcard/screenshot.png
echo Captura guardada en C:\ADB\screenshot.png
pause
