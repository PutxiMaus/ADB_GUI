# SCRCPY Python GUI (0pantallas_python_project)

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
- `adb` (Android Platform Tools) y `scrcpy` en PATH o en `tools/`. `setup_tools.py` intenta ayudar a asegurarlos.
- Windows: comandos `ping -n` y `arp -a` son usados por el módulo de detección de red.

## Instalación y ejecución rápida

```bash
# clona el repo
git clone https://github.com/<tu_usuario>/<tu_repo>.git
cd <tu_repo>

# opcional: entorno virtual
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt  # si existe

# intentar asegurar herramientas (adb/scrcpy/ipscan)
python -c "import setup_tools, os; setup_tools.ensure_tools(os.getcwd())"

# ejecutar la app
python main.py
```

## Notas de privacidad / seguridad

- **No** incluyas `devices.json` con MACs/IP reales en el repo público. Usa `devices.json.example`.
- Escanear redes puede estar prohibido en entornos corporativos: usa IPScan/ping-sweep solo donde tengas permiso.

## Contribuir

Lee `CONTRIBUTING.md`.

