import os
import sys
import json
import re
import subprocess
import threading
import time
import socket
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog, colorchooser

# Importar helpers (asegúrate de tener setup_tools.py y adb_commands.py en el proyecto)
try:
    import setup_tools
except Exception as e:
    setup_tools = None
    print("Aviso: setup_tools no disponible:", e)

try:
    import adb_commands as adb
except Exception:
    adb = None

# ----------------------
# Config / Globals
# ----------------------
PROJECT_ROOT = os.getcwd()
PERFILES_FILE = os.path.join(PROJECT_ROOT, "devices.json")
perfiles = {}

_scrcpy_proc = None
_screenrec_proc = None

# Intentar asegurar herramientas (solo en Windows, no bloquear si falla)
if setup_tools:
    try:
        setup_tools.ensure_tools()
    except Exception as e:
        print("setup_tools.ensure_tools() fallo:", e)

# ----------------------
# Configuración persistente
# ----------------------
CONFIG_FILE = "config.json"
config = {
    "theme": "light",   # "light" o "dark"
    "show_log": True    # mostrar/ocultar consola
}

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {"theme": "light", "show_log": True}

def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print("Error guardando config:", e)

def apply_theme(root):
    theme = config.get("theme", "light")
    colors = THEMES[theme]

    style = ttk.Style()
    try:
        style.theme_use("default")  # forzar base simple
    except Exception:
        pass

    # Fondo base
    root.configure(bg=colors["bg"])

    # ttk styles
    style.configure("TFrame", background=colors["bg"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
    style.configure("TButton", background=colors["button_bg"], foreground=colors["button_fg"])
    style.map("TButton",
              background=[("active", colors["accent"])],
              foreground=[("active", "#ffffff")])
    style.configure("TNotebook", background=colors["bg"])
    style.configure("TNotebook.Tab", background=colors["button_bg"], foreground=colors["fg"])
    style.map("TNotebook.Tab",
              background=[("selected", colors["accent"])],
              foreground=[("selected", "#ffffff")])

    # Aplicar recursivamente a todos los widgets tk (no ttk)
    def _apply_bg_recursive(widget):
        try:
            cls = widget.winfo_class()
            if cls in ("Frame", "Label", "Canvas"):
                widget.configure(bg=colors["bg"])
            elif cls == "Text":
                widget.configure(bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"])
            elif cls == "Listbox":
                widget.configure(bg=colors["button_bg"], fg=colors["fg"],
                                 selectbackground=colors["accent"], selectforeground="#ffffff")
        except Exception:
            pass
        for child in widget.winfo_children():
            _apply_bg_recursive(child)

    _apply_bg_recursive(root)

    # Consola inferior (si existe)
    if "text_log" in globals():
        text_log.configure(bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"])

    # consola inferior
    if "text_log" in globals():
        text_log.configure(bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"])

def toggle_log():
    config["show_log"] = not config.get("show_log", True)
    save_config()
    if config["show_log"]:
        if bottom_frame not in paned.panes():
            paned.add(bottom_frame, minsize=140)
    else:
        if bottom_frame in paned.panes():
            paned.forget(bottom_frame)

def _apply_bg_recursive(widget, bg, fg):
    try:
        if isinstance(widget, (tk.Frame, tk.Listbox)):
            widget.configure(bg=bg)
        if isinstance(widget, tk.Text) and widget != globals().get("text_log"):
            widget.configure(bg=bg, fg=fg, insertbackground=fg)
    except Exception:
        pass
    for child in widget.winfo_children():
        _apply_bg_recursive(child, bg, fg)

def toggle_theme(root):
    config["theme"] = "dark" if config.get("theme") == "light" else "light"
    save_config()
    apply_theme(root)

# ----------------------
# Paleta de temas (tipo Discord)
# ----------------------
THEMES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#000000",
        "button_bg": "#f0f0f0",
        "button_fg": "#000000",
        "accent": "#0057d9"
    },
    "dark": {
        "bg": "#2b2d31",        # gris principal Discord
        "fg": "#dcddde",        # texto claro
        "button_bg": "#36393f", # botones y tabs
        "button_fg": "#ffffff",
        "accent": "#5865f2"     # azul Discord
    }
}

# ----------------------
# Utilidades: perfiles
# ----------------------

def load_profiles():
    global perfiles
    if os.path.exists(PERFILES_FILE):
        try:
            with open(PERFILES_FILE, "r", encoding="utf-8") as f:
                perfiles = json.load(f)
        except Exception:
            perfiles = {}
    else:
        perfiles = {}


def save_profiles():
    try:
        with open(PERFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(perfiles, f, indent=4, ensure_ascii=False)
    except Exception as e:
        gui_log(f"Error guardando perfiles: {e}", level="error")


def _get_local_ipv4_and_prefix():
    """Intentar obtener la IPv4 local y asumir /24 si no se puede calcular máscara."""
    try:
        # Método sencillo: crear socket y leer la IP local usada para salir a Internet
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip, 24
    except Exception:
        return None, 24

def _run_angryip_scan(range_start, range_end, export_file):
    """Intentar llamar a Angry IP Scanner desde CLI con feeder+exporter.
    Se prueban nombres habituales del ejecutable."""
    executables = ["ipscan", "ipscan.exe", "angryip", "angryip.exe"]
    for exe in executables:
        try:
            # -f:range <start> <end>  -o <file>
            cmd = [exe, f"-f:range", range_start, range_end, "-o", export_file]
            # No esperamos salida compleja, solo ejecutamos (puede abrir GUI en algunas versiones).
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            # si no hay error grave asumimos que escribió el archivo
            if proc.returncode == 0 or os.path.exists(export_file):
                return True
        except Exception:
            continue
    return False

def _ping_sweep_cold(range_base):
    """Hacer un ping sweep en Windows para poblar la ARP cache.
       Se hace en hilos para no tardar demasiado."""
    threads = []
    def p(ip):
        try:
            # Windows: ping -n 1 -w 200 (200 ms timeout)
            subprocess.run(["ping", "-n", "1", "-w", "200", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    for i in range(1, 255):
        ip = f"{range_base}.{i}"
        t = threading.Thread(target=p, args=(ip,), daemon=True)
        t.start()
        threads.append(t)
        # evitar crear 254 hilos instantáneos; ligero throttling
        if len(threads) % 50 == 0:
            time.sleep(0.05)

    # esperar un poco a que terminen (no bloqueante excesivo)
    for t in threads:
        t.join(timeout=0.2)

def find_ip_from_mac(mac):
    """Intento robusto: si la red oculta IPs, primero intento escanear (Angry IP Scanner o ping sweep),
    luego parseo arp -a y devuelvo la IP si coincide la MAC."""
    if not mac:
        return None

    # Normalizar MAC a minúsculas con guiones (Windows suele mostrar con guiones)
    mac_norm = mac.lower().replace(":", "-").replace(".", "-").replace(" ", "-")

    # 1) Intentar escanear con Angry IP Scanner si está instalado
    local_ip, prefix = _get_local_ipv4_and_prefix()
    if local_ip:
        # asumir /24 (192.168.x.1 - 192.168.x.254)
        parts = local_ip.split(".")
        if len(parts) >= 3:
            base = ".".join(parts[0:3])
            range_start = f"{base}.1"
            range_end = f"{base}.254"
            export_tmp = os.path.join(PROJECT_ROOT, "angry_scan_result.txt")
            try:
                ok = _run_angryip_scan(range_start, range_end, export_tmp)
                if ok and os.path.exists(export_tmp):
                    # opcional: podrías parsear el export_tmp y devolver IP directamente si contiene MACs
                    try:
                        with open(export_tmp, "r", encoding="utf-8", errors="ignore") as f:
                            data = f.read().lower()
                            mac_search = mac_norm.replace("-", "-")
                            if mac_search in data:
                                # buscar ip en la misma línea
                                for line in data.splitlines():
                                    if mac_search in line:
                                        # asumir que la IP es la primera columna
                                        parts = line.split()
                                        if parts:
                                            return parts[0]
                    except Exception:
                        pass
            except Exception:
                pass

            # 2) Si no hay Angry IP Scanner o no arrojó resultados, hacer ping sweep para poblar ARP
            _ping_sweep_cold(base)

    # 3) Finalmente parsear arp -a (Windows)
    try:
        out = subprocess.getoutput("arp -a")
    except Exception as e:
        gui_log(f"No se pudo ejecutar arp -a: {e}", level="error")
        return None

    for line in out.splitlines():
        low = line.lower()
        # normalizar separadores en la línea para comparar
        if mac_norm in low or mac.lower().replace("-", ":") in low:
            parts = line.split()
            if parts:
                # formato esperable en Windows: IP  MAC  tipo
                ip_candidate = parts[0]
                # validar que parece IP
                if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip_candidate):
                    return ip_candidate

    return None

def add_profile(name, mac, port=5555, ip=None, notes=None, color=None):
    perfiles[name] = {"mac": mac, "port": port, "ip": ip, "notes": notes, "color": color}
    save_profiles()
    refresh_profiles_list()
    gui_log(f"Perfil guardado: {name}")


def edit_profile(name):
    if not name or name not in perfiles:
        gui_log(f"Perfil '{name}' no existe", level="error")
        return
    perfil = perfiles[name]
    new_mac = simpledialog.askstring("Editar perfil", "MAC address:", initialvalue=perfil.get("mac", ""))
    if not new_mac:
        return
    new_port = simpledialog.askinteger("Editar perfil", "Puerto:", initialvalue=perfil.get("port", 5555))
    new_ip = simpledialog.askstring("Editar perfil", "IP fija (opcional):", initialvalue=perfil.get("ip", ""))
    new_notes = simpledialog.askstring("Editar perfil", "Notas:", initialvalue=perfil.get("notes", ""))
    new_color = simpledialog.askstring("Editar perfil", "Color (ej: #ff0000):", initialvalue=perfil.get("color", ""))
    perfiles[name] = {"mac": new_mac, "port": new_port, "ip": new_ip, "notes": new_notes, "color": new_color}
    save_profiles()
    refresh_profiles_list()
    gui_log(f"Perfil '{name}' editado")


def delete_profile(name):
    if not name or name not in perfiles:
        gui_log(f"Perfil '{name}' no existe", level="error")
        return
    if messagebox.askyesno("Borrar perfil", f"¿Seguro que quieres borrar el perfil '{name}'?"):
        perfiles.pop(name)
        save_profiles()
        refresh_profiles_list()
        gui_log(f"Perfil '{name}' borrado")


def connect_profile(name):
    if not name or name not in perfiles:
        gui_log(f"Perfil '{name}' no existe", level="error")
        return
    perfil = perfiles[name]
    ip = perfil.get("ip")
    if not ip:
        ip = find_ip_from_mac(perfil.get("mac", ""))
    if not ip:
        gui_log(f"No se encontró IP para {perfil.get('mac')}", level="error")
        return
    port = perfil.get("port", 5555)
    run_in_thread(lambda: exec_adb(["connect", f"{ip}:{port}"]))

def disconnect_profile(name):
    """Desconecta el perfil (adb disconnect ip:port)."""
    if not name or name not in perfiles:
        gui_log(f"Perfil '{name}' no existe", level="error")
        return
    perfil = perfiles[name]
    ip = perfil.get("ip")
    if not ip:
        ip = find_ip_from_mac(perfil.get("mac", ""))
    if not ip:
        gui_log(f"No se encontró IP para {perfil.get('mac')}", level="error")
        return
    port = perfil.get("port", 5555)
    run_in_thread(lambda: exec_adb(["disconnect", f"{ip}:{port}"]))
    gui_log(f"Desconectando {name} ({ip}:{port})", level="info")

# ----------------------
# Exec helpers & logging
# ----------------------

def gui_log(msg, level="info"):
    """Inserta msg en la consola GUI de forma segura desde hilos.
    level: 'info' | 'error' | 'cmd'
    """
    if 'root' in globals() and isinstance(root, tk.Tk):
        try:
            root.after(0, lambda: _append_log(msg, level))
        except Exception:
            print(msg)
    else:
        print(msg)

def _append_log(msg, level="info"):
    if not getattr(text_log, "winfo_exists", lambda: True)():
        print(msg)
        return

    theme = config.get("theme", "light")
    tag = level

    # Solo configurar el tag si no existe todavía
    if tag not in text_log.tag_names():
        if theme == "light":
            if tag == "info":
                text_log.tag_config(tag, foreground="green")
            elif tag == "error":
                text_log.tag_config(tag, foreground="red")
            else:
                text_log.tag_config(tag, foreground="blue")
        else:  # dark
            if tag == "info":
                text_log.tag_config(tag, foreground="lime")
            elif tag == "error":
                text_log.tag_config(tag, foreground="red")
            else:
                text_log.tag_config(tag, foreground="cyan")

    text_log.insert(tk.END, msg + "\n", tag)
    text_log.see(tk.END)

def exec_adb(args):
    """Ejecuta adb <args...> y vuelca stdout/stderr en la consola. Puede llamarse desde hilo."""
    if isinstance(args, str):
        args = args.split()
    cmd = ["adb"] + args
    gui_log(f">> {' '.join(cmd)}", level="cmd")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.stdout:
            gui_log(proc.stdout.strip(), level="info")
        if proc.stderr:
            gui_log(proc.stderr.strip(), level="error")
        return proc.returncode
    except Exception as e:
        gui_log(f"Error ejecutando adb: {e}", level="error")
        return -1


def exec_cmd(cmd_list):
    """Ejecuta un comando externo (scrcpy, cmd) y vuelca salida en consola."""
    if isinstance(cmd_list, str):
        cmd_list = cmd_list.split()
    gui_log(f">> {' '.join(cmd_list)}", level="cmd")
    try:
        proc = subprocess.run(cmd_list, capture_output=True, text=True, shell=False)
        if proc.stdout:
            gui_log(proc.stdout.strip(), level="info")
        if proc.stderr:
            gui_log(proc.stderr.strip(), level="error")
        return proc.returncode
    except Exception as e:
        gui_log(f"Error ejecutando comando: {e}", level="error")
        return -1


def run_in_thread(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t

# ----------------------
# Funciones avanzadas
# ----------------------

def start_scrcpy():
    global _scrcpy_proc
    if _scrcpy_proc and getattr(_scrcpy_proc, 'poll', lambda: None)() is None:
        gui_log("scrcpy ya está en ejecución", level="error")
        return
    try:
        _scrcpy_proc = subprocess.Popen(["scrcpy"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        gui_log("scrcpy iniciado", level="info")
        # lanzar hilo que lea stderr y stdout si se desea (opcional)
    except Exception as e:
        gui_log(f"No se pudo iniciar scrcpy: {e}", level="error")


def stop_scrcpy():
    global _scrcpy_proc
    if not _scrcpy_proc:
        gui_log("scrcpy no está en ejecución", level="error")
        return
    try:
        _scrcpy_proc.terminate()
        _scrcpy_proc.wait(timeout=5)
    except Exception:
        try:
            _scrcpy_proc.kill()
        except Exception:
            pass
    _scrcpy_proc = None
    gui_log("scrcpy detenido", level="info")


def install_apk():
    apk = filedialog.askopenfilename(title="Selecciona APK", filetypes=[("APK files", "*.apk")])
    if not apk:
        return
    run_in_thread(lambda: exec_adb(["install", "-r", apk]))


def uninstall_app():
    pkg = simpledialog.askstring("Uninstall", "Nombre del paquete (p.ej. com.example.app):")
    if not pkg:
        return
    run_in_thread(lambda: exec_adb(["uninstall", pkg]))


def reboot_device():
    run_in_thread(lambda: exec_adb(["reboot"]))


def adb_devices():
    run_in_thread(lambda: exec_adb(["devices", "-l"]))


def adb_disconnect_all():
    run_in_thread(lambda: exec_adb(["disconnect"]))


def dump_logcat():
    run_in_thread(lambda: exec_adb(["logcat", "-d"]))


def get_device_info():
    run_in_thread(lambda: exec_adb(["shell", "getprop"]))

# screenrecord helper: inicia recording en dispositivo
def start_screenrecord():
    global _screenrec_proc
    if _screenrec_proc and getattr(_screenrec_proc, 'poll', lambda: None)() is None:
        gui_log("screenrecord ya en ejecución", level="error")
        return
    try:
        # ejecuta adb shell screenrecord en un proceso separado
        _screenrec_proc = subprocess.Popen(["adb", "shell", "screenrecord", "/sdcard/record.mp4"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        gui_log("screenrecord iniciado en dispositivo (/sdcard/record.mp4)", level="info")
    except Exception as e:
        gui_log(f"No se pudo iniciar screenrecord: {e}", level="error")


def stop_screenrecord_and_pull():
    global _screenrec_proc
    if not _screenrec_proc:
        gui_log("No hay screenrecord en ejecución", level="error")
        return
    try:
        _screenrec_proc.terminate()
        _screenrec_proc.wait(timeout=5)
    except Exception:
        try:
            _screenrec_proc.kill()
        except Exception:
            pass
    _screenrec_proc = None
    local = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 files", "*.mp4")], title="Guardar grabación como")
    if not local:
        gui_log("Cancelado pull de grabación", level="error")
        return
    run_in_thread(lambda: exec_adb(["pull", "/sdcard/record.mp4", local]))


def pull_file():
    remote = simpledialog.askstring("Pull", "Ruta en dispositivo (p.ej. /sdcard/file.txt):")
    if not remote:
        return
    local = filedialog.asksaveasfilename(title="Guardar como", initialfile=os.path.basename(remote))
    if not local:
        return
    run_in_thread(lambda: exec_adb(["pull", remote, local]))


def push_file():
    local = filedialog.askopenfilename(title="Selecciona fichero local")
    if not local:
        return
    remote = simpledialog.askstring("Push", "Ruta destino en dispositivo (p.ej. /sdcard/file.txt):")
    if not remote:
        return
    run_in_thread(lambda: exec_adb(["push", local, remote]))


def open_shell_window():
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["cmd.exe", "/k", "adb shell"])  # Windows
        else:
            # abrir una nueva terminal en unix-like (no garantizado)
            subprocess.Popen(["xterm", "-e", "adb shell"])  # puede fallar si xterm no existe
        gui_log("Abierta ventana de shell (nueva)", level="info")
    except Exception as e:
        gui_log(f"No se pudo abrir shell: {e}", level="error")

# ----------------------
# Construcción GUI
# ----------------------
root = tk.Tk()
root.title("SCRCPY Python GUI")
root.geometry("1000x720")

load_config()

# Menú principal
menubar = tk.Menu(root)
config_menu = tk.Menu(menubar, tearoff=0)
config_menu.add_command(label="Cambiar tema (claro/oscuro)", command=lambda: toggle_theme(root))
config_menu.add_command(label="Mostrar/Ocultar consola", command=toggle_log)
menubar.add_cascade(label="Configuración", menu=config_menu)
root.config(menu=menubar)

# PanedWindow vertical para splitter (arrastrable)
paned = tk.PanedWindow(root, orient=tk.VERTICAL)
paned.pack(fill=tk.BOTH, expand=True)

# Top frame: notebook
top_frame = tk.Frame(paned)
paned.add(top_frame, minsize=350)

notebook = ttk.Notebook(top_frame)
notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

# --- Tabs ---
tab_perfiles = ttk.Frame(notebook)
tab_comandos = ttk.Frame(notebook)
tab_batch = ttk.Frame(notebook)
notebook.add(tab_perfiles, text="Perfiles")
notebook.add(tab_comandos, text="Comandos")
notebook.add(tab_batch, text="Batch")

# ----------------------
# Pestaña Perfiles
# ----------------------

# Layout con grid responsive (left/right)
per_left = ttk.Frame(tab_perfiles, padding=8)
per_left.grid(row=0, column=0, sticky="nsew")
per_right = ttk.Frame(tab_perfiles, padding=8)
per_right.grid(row=0, column=1, sticky="nsew")

# Configurar expansión del contenedor de la pestaña
tab_perfiles.rowconfigure(0, weight=1)
tab_perfiles.columnconfigure(0, weight=3)  # lista ocupa más
tab_perfiles.columnconfigure(1, weight=1)  # panel derecho ocupa menos

# -----------------
# LEFT: listbox con scrollbar (grid responsive)
# -----------------
list_frame = ttk.Frame(per_left)
list_frame.grid(row=0, column=0, sticky="nsew")

profile_listbox = tk.Listbox(list_frame, activestyle="dotbox")
profile_listbox.grid(row=0, column=0, sticky="nsew")

profile_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=profile_listbox.yview)
profile_scroll.grid(row=0, column=1, sticky="ns")

profile_listbox.config(yscrollcommand=profile_scroll.set)

# Expansión interna del list_frame / per_left
list_frame.rowconfigure(0, weight=1)
list_frame.columnconfigure(0, weight=1)
per_left.rowconfigure(0, weight=1)
per_left.columnconfigure(0, weight=1)

# -----------------
# RIGHT: detalle + botones (usamos grid para que escale)
# -----------------
detail_label = ttk.Label(per_right, text="Detalles del perfil", font=(None, 10, "bold"))
detail_label.grid(row=0, column=0, sticky="nw", pady=(0,6))

detail_text = tk.Text(per_right, width=30, height=10, state=tk.DISABLED, wrap=tk.WORD)
detail_text.grid(row=1, column=0, sticky="nsew", pady=(0,12))

# Frame para botones (apilados verticalmente, se expanden en ancho)
button_frame = ttk.Frame(per_right)
button_frame.grid(row=2, column=0, sticky="ew")
button_frame.columnconfigure(0, weight=1)

btn_add = ttk.Button(button_frame, text="Añadir", command=lambda: prompt_add_profile())
btn_edit = ttk.Button(button_frame, text="Editar", command=lambda: edit_profile(get_selected_profile()))
btn_delete = ttk.Button(button_frame, text="Borrar", command=lambda: delete_profile(get_selected_profile()))
btn_connect = ttk.Button(button_frame, text="Conectar", command=lambda: connect_profile(get_selected_profile()))
btn_disconnect = ttk.Button(button_frame, text="Desconectar", command=lambda: disconnect_profile(get_selected_profile()))
btn_export = ttk.Button(button_frame, text="Exportar", command=lambda: export_profiles())
btn_import = ttk.Button(button_frame, text="Importar", command=lambda: import_profiles())

# Poner los botones en vertical dentro del button_frame
for i, w in enumerate((btn_add, btn_edit, btn_delete, btn_connect, btn_disconnect, btn_export, btn_import)):
    w.grid(row=i, column=0, sticky="ew", pady=6, padx=0)

# Hacer que el detalle (texto) se expanda verticalmente y columnas del per_right
per_right.rowconfigure(1, weight=1)   # detail_text crece
per_right.rowconfigure(2, weight=0)   # botones no crecen verticalmente
per_right.columnconfigure(0, weight=1)

# Funciones de UI para perfiles

def prompt_add_profile():
    name = simpledialog.askstring("Nuevo perfil", "Nombre del perfil:")
    if not name:
        return
    if name in perfiles:
        if not messagebox.askyesno("Confirmar", "Ya existe un perfil con ese nombre. Reemplazar?"):
            return
    mac = simpledialog.askstring("Nuevo perfil", "MAC address:")
    if not mac:
        return
    port = simpledialog.askinteger("Nuevo perfil", "Puerto:", initialvalue=5555)
    ip = simpledialog.askstring("Nuevo perfil", "IP fija (opcional):")
    notes = simpledialog.askstring("Nuevo perfil", "Notas (opcional):")
    add_profile(name, mac, port, ip, notes)


def get_selected_profile():
    sel = profile_listbox.curselection()
    if not sel:
        return None
    return profile_listbox.get(sel[0])


def refresh_profiles_list():
    profile_listbox.delete(0, tk.END)
    for name in perfiles:
        profile_listbox.insert(tk.END, name)
    # actualizar detalle cuando cambie selection
    try:
        profile_listbox.bind('<<ListboxSelect>>', lambda e: show_profile_details())
    except Exception:
        pass


def show_profile_details():
    name = get_selected_profile()
    if not name:
        detail_text.config(state=tk.NORMAL)
        detail_text.delete(1.0, tk.END)
        detail_text.config(state=tk.DISABLED)
        return
    p = perfiles.get(name, {})
    txt = f"Nombre: {name}\nMAC: {p.get('mac')}\nIP: {p.get('ip')}\nPuerto: {p.get('port')}\nNotas: {p.get('notes', '')}\n"
    detail_text.config(state=tk.NORMAL)
    detail_text.delete(1.0, tk.END)
    detail_text.insert(tk.END, txt)
    detail_text.config(state=tk.DISABLED)

# ----------------------
# Pestaña Comandos
# ----------------------

cmds_outer = ttk.Frame(tab_comandos, padding=12)
cmds_outer.grid(row=0, column=0, sticky="nsew")

# Frame con grid para botones
cmds_grid = ttk.Frame(cmds_outer, padding=12)
cmds_grid.grid(row=0, column=0, sticky="nsew")

# Configurar expansión de la pestaña y contenedores
tab_comandos.rowconfigure(0, weight=1)
tab_comandos.columnconfigure(0, weight=1)

cmds_outer.rowconfigure(0, weight=1)
cmds_outer.columnconfigure(0, weight=1)

# -----------------
# Definir comandos
# -----------------
commands = [
    ("Home", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "3"]))),
    ("Power", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "26"]))),
    ("Vol +", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "24"]))),
    ("Vol -", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "25"]))),
    ("Screenshot", lambda: run_in_thread(lambda: exec_adb(["shell", "screencap", "-p", "/sdcard/screen.png"]) or exec_adb(["pull", "/sdcard/screen.png", os.path.join(PROJECT_ROOT, "screenshot.png")] ))),
    ("Spotify", lambda: run_in_thread(lambda: exec_adb(["shell", "monkey", "-p", "com.spotify.music", "-c", "android.intent.category.LAUNCHER", "1"]))),
    ("YouTube", lambda: run_in_thread(lambda: exec_adb(["shell", "monkey", "-p", "com.google.android.youtube", "-c", "android.intent.category.LAUNCHER", "1"]))),
    ("Crazy taps", lambda: run_in_thread(lambda: [exec_adb(["shell", "input", "tap", "500", "1000"]) for _ in range(8)])),
    ("ADB devices", lambda: run_in_thread(adb_devices)),
    ("Disconnect all", lambda: run_in_thread(adb_disconnect_all)),
    ("Reboot", lambda: run_in_thread(reboot_device)),
    ("Install APK", lambda: run_in_thread(install_apk)),
    ("Uninstall app", lambda: run_in_thread(uninstall_app)),
    ("Start scrcpy", lambda: run_in_thread(start_scrcpy)),
    ("Stop scrcpy", lambda: run_in_thread(stop_scrcpy)),
    ("Start screenrecord", lambda: run_in_thread(start_screenrecord)),
    ("Stop screenrecord & pull", lambda: run_in_thread(stop_screenrecord_and_pull)),
    ("Pull file", lambda: run_in_thread(pull_file)),
    ("Push file", lambda: run_in_thread(push_file)),
    ("Get device info", lambda: run_in_thread(get_device_info)),
    ("Dump logcat (one-shot)", lambda: run_in_thread(dump_logcat)),
    ("Open shell (new window)", lambda: run_in_thread(open_shell_window)),
]

# -----------------
# Crear botones en cuadrícula
# -----------------
cols = 3
for i, (label, cb) in enumerate(commands):
    r = i // cols
    c = i % cols
    btn = ttk.Button(cmds_grid, text=label, command=cb)
    btn.grid(row=r, column=c, padx=16, pady=8, ipadx=10, ipady=8, sticky="nsew")

# Hacer que las columnas se expandan (responsive en ancho)
for c in range(cols):
    cmds_grid.columnconfigure(c, weight=1)

# 👉 Truco: filas con weight=1 pero altura mínima fija
total_rows = (len(commands) + cols - 1) // cols
for r in range(total_rows):
    cmds_grid.rowconfigure(r, weight=1, minsize=50)

# ----------------------
# Pestaña Batch
# ----------------------

batch_frame = ttk.Frame(tab_batch, padding=12)
batch_frame.grid(row=0, column=0, sticky="nsew")

# Configurar expansión
tab_batch.rowconfigure(0, weight=1)
tab_batch.columnconfigure(0, weight=1)

batch_frame.rowconfigure(2, weight=1)   # para que el espacio inferior crezca
batch_frame.columnconfigure(0, weight=1)
batch_frame.columnconfigure(1, weight=0)
batch_frame.columnconfigure(2, weight=0)

batch_var = tk.StringVar()
batch_combobox = ttk.Combobox(batch_frame, textvariable=batch_var, state="readonly", width=60)
batch_combobox.grid(row=0, column=0, padx=6, pady=6, sticky="ew")

btn_refresh_batch = ttk.Button(batch_frame, text="Refrescar", command=lambda: refresh_batch_files())
btn_refresh_batch.grid(row=0, column=1, padx=6)

btn_run_batch = ttk.Button(batch_frame, text="Ejecutar", command=lambda: run_batch())
btn_run_batch.grid(row=0, column=2, padx=6)

# Por si quieres ver ruta completa
batch_note = ttk.Label(batch_frame, text="Busca .bat en la carpeta del proyecto (root)")
batch_note.grid(row=1, column=0, columnspan=3, pady=(6,0), sticky="w")

# ----------------------
# Consola inferior (splitter) 
# ----------------------

# Bottom frame debe colgar también de paned
bottom_frame = tk.Frame(paned)   # ✅ corregido
paned.add(bottom_frame, minsize=140)

text_log = tk.Text(bottom_frame, height=14, bg="#0b0b0b", fg="#b8ffb8", insertbackground="#ffffff")
text_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

scroll_log = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=text_log.yview)
scroll_log.pack(side=tk.RIGHT, fill=tk.Y)
text_log.config(yscrollcommand=scroll_log.set)

status = ttk.Label(root, text="Perfiles • Comandos • Batch — Consola abajo (arrastra el splitter para cambiar tamaño)")
status.pack(side=tk.BOTTOM, fill=tk.X)

# ----------------------
# Batch helpers
# ----------------------

def refresh_batch_files():
    try:
        files = [f for f in os.listdir(PROJECT_ROOT) if f.lower().endswith('.bat')]
    except Exception:
        files = []
    batch_combobox['values'] = files
    if files:
        batch_combobox.current(0)


def run_batch():
    file = batch_var.get()
    if not file:
        gui_log("No hay batch seleccionado", level="error")
        return
    path = os.path.join(PROJECT_ROOT, file)
    if not os.path.exists(path):
        gui_log("El batch seleccionado no existe", level="error")
        return
    gui_log(f"▶️ Ejecutando batch: {file}", level="cmd")

    def worker():
        # Ejecutar .bat con shell=True en Windows
        try:
            proc = subprocess.Popen(path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate()
            if out:
                gui_log(out.strip(), level="info")
            if err:
                gui_log(err.strip(), level="error")
        except Exception as e:
            gui_log(f"Error ejecutando batch: {e}", level="error")

    run_in_thread(worker)

# ----------------------
# Inicialización final
# ----------------------
load_profiles()
refresh_profiles_list()
refresh_batch_files()
apply_theme(root)

# Lanzar la app
root.mainloop()
