# SCRCPY Python GUI

Interfaz gráfica en Python/Tkinter para gestionar conexiones ADB, lanzar `scrcpy` y ejecutar comandos auxiliares.
Punto de entrada: `main.py`.

**Autor:** PutxiMaus

## Estructura principal

- `main.py` — aplicación principal (Tkinter).
- `setup_tools.py` — utilitario que intenta asegurar `adb`, `scrcpy` y (opcional) Angry IP Scanner.
- `adb_commands.py` — helpers ADB usados por la app.
- `devices.json` — perfiles guardados (NO subir con datos reales).
- `bat_sources/` — scripts .bat auxiliares (ejecutados por la app).
- `tools/` — carpeta opcional para colocar `platform-tools`, `scrcpy`, `ipscan` (portable).

## Requisitos

- Python 3.10+ (probado con 3.13 en Windows).
- Java 21
- Windows: comandos `ping -n` y `arp -a` son usados por el módulo de detección de red.


- **No** incluyas `devices.json` con MACs/IP reales en el repo público. Usa `devices.json.example`.
- Escanear redes puede estar prohibido en entornos corporativos: usa IPScan/ping-sweep solo donde tengas permiso.

## Contribuir

Lee `CONTRIBUTING.md`.

