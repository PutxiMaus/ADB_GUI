# ADB+SCRCPY Python GUI 

Interfaz gráfica en Python/Tkinter para gestionar conexiones ADB, lanzar `scrcpy` y ejecutar comandos auxiliares.
Punto de entrada: `main.py`.

**Autor:** PutxiMaus

## Estructura principal

- `main.py` — aplicación principal (Tkinter).
- `setup_tools.py` — utilitario que intenta asegurar `adb`, `scrcpy` y (opcional) Angry IP Scanner.
- `adb_commands.py` — helpers ADB usados por la app.
- `devices.json` — perfiles guardados.
- `bat_sources/` — scripts .bat auxiliares (ejecutados por la app).
- `tools/` — carpeta opcional para colocar `platform-tools`, `scrcpy`, `ipscan` (portable).

## Requisitos

- Python 3.10+ (probado con 3.13 en Windows).
- `adb` (Android Platform Tools) y `scrcpy` en PATH o en `tools/`. `setup_tools.py` intenta ayudar a asegurarlos.
- Windows: comandos `ping -n` y `arp -a` son usados por el módulo de detección de red.

## Instalación y ejecución rápida

Descarga el ZIP
Descomprime el ZIP
Ejecuta main.py

## Contribuir

Lee `CONTRIBUTING.md`.

