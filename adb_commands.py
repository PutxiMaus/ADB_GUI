import subprocess

def run_adb(cmd):
    """Ejecuta un comando adb y devuelve salida (stdout + stderr)."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        result = subprocess.run(["adb"] + cmd, capture_output=True, text=True)
        output = result.stdout.strip()
        errors = result.stderr.strip()
        return (output + ("\n" + errors if errors else "")).strip()
    except Exception as e:
        return f"Error ejecutando adb: {e}"

# --- Comandos básicos ---
def home():
    return run_adb(["shell", "input", "keyevent", "3"])  # KEYCODE_HOME

def power():
    return run_adb(["shell", "input", "keyevent", "26"])  # KEYCODE_POWER

def volume_up():
    return run_adb(["shell", "input", "keyevent", "24"])  # KEYCODE_VOLUME_UP

def volume_down():
    return run_adb(["shell", "input", "keyevent", "25"])  # KEYCODE_VOLUME_DOWN

def screenshot(save_path="screenshot.png"):
    device_path = "/sdcard/screen.png"
    run_adb(["shell", "screencap", "-p", device_path])
    run_adb(["pull", device_path, save_path])
    return f"📸 Captura guardada en {save_path}"

def close_app(package_name):
    return run_adb(["shell", "am", "force-stop", package_name])

def open_app(package_name):
    return run_adb(["shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"])

def send_text(text):
    return run_adb(["shell", "input", "text", text.replace(" ", "%s")])  # reemplazo espacio por %s

def tap(x, y):
    return run_adb(["shell", "input", "tap", str(x), str(y)])

def swipe(x1, y1, x2, y2, duration=300):
    return run_adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])

# --- Extras ---
def show_notifications():
    return run_adb(["shell", "cmd", "statusbar", "expand-notifications"])

def spotify():
    return open_app("com.spotify.music")

def youtube():
    return open_app("com.google.android.youtube")

def crazy_taps(times=10):
    """Hace taps rápidos en la pantalla como el crazy.bat."""
    for i in range(times):
        run_adb(["shell", "input", "tap", "500", "1000"])
    return f"🤪 {times} taps ejecutados"

def subir_bajar_volumen(veces=3):
    """Sube y baja el volumen varias veces (como subeybaja.bat)."""
    for _ in range(veces):
        run_adb(["shell", "input", "keyevent", "24"])  # subir
        run_adb(["shell", "input", "keyevent", "25"])  # bajar
    return f"🔊 Volumen subido y bajado {veces} veces"

def power_loop(veces=3):
    """Pulsa power varias veces (como Power - loop.bat)."""
    for _ in range(veces):
        run_adb(["shell", "input", "keyevent", "26"])
    return f"⚡ Botón Power pulsado {veces} veces"

def youtube_loop(veces=3):
    """Abre YouTube varias veces (como YT - loop.bat)."""
    for _ in range(veces):
        open_app("com.google.android.youtube")
    return f"▶️ YouTube abierto {veces} veces"
