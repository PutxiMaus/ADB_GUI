# setup_tools.py
# =================
# Asegura herramientas usadas por el proyecto:
#  - adb (platform-tools)
#  - scrcpy
#  - Angry IP Scanner (portable en tools/ipscan o instalado vía winget/choco)
#
# Uso: from setup_tools import ensure_tools; ensure_tools(PROJECT_ROOT)
#
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.parse
import re
import zipfile
import shutil
import json
import time
from pathlib import Path
# Ruta del proyecto = carpeta donde está este main.py
BASE_DIR = Path(__file__).resolve().parent

# Añadir la carpeta del proyecto al PATH solo para este proceso (temporal)
os.environ["PATH"] = str(BASE_DIR) + os.pathsep + os.environ.get("PATH", "")

GITHUB_IPSCAN_RELEASES = "https://github.com/angryip/ipscan/releases/latest"

# ----------------------
# Util helpers
# ----------------------
def _run_cmd(cmd, timeout=60, shell=False):
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=shell)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def _download_url_to_file(url, dest, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        with open(dest, "wb") as f:
            f.write(resp.read())

# ----------------------
# Angry IP Scanner helpers (portable/install)
# ----------------------
def _find_release_asset_url():
    try:
        req = urllib.request.Request(GITHUB_IPSCAN_RELEASES, headers={"User-Agent": "python-urllib"})
        with urllib.request.urlopen(req, timeout=15) as r:
            final_url = r.geturl()
    except Exception:
        final_url = GITHUB_IPSCAN_RELEASES

    try:
        req = urllib.request.Request(final_url, headers={"User-Agent": "python-urllib"})
        with urllib.request.urlopen(req, timeout=20) as r:
            page = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None

    matches = re.findall(r'href=\"([^\"]*(?:ipscan|ipscan-portable)[^\"]*\.(?:zip|exe))\"', page, flags=re.IGNORECASE)
    if not matches:
        matches = re.findall(r'href=\"([^\"]*ipscan[^\"]*\\.(?:zip|exe))\"', page, flags=re.IGNORECASE)
    if not matches:
        return None

    href = matches[0]
    if href.startswith("http"):
        return href
    return urllib.parse.urljoin("https://github.com", href)

def install_angry_ip_scanner(project_root: str) -> (bool, str):
    tools_dir = Path(project_root) / "tools"
    ipscan_dir = tools_dir / "ipscan"
    ipscan_dir.mkdir(parents=True, exist_ok=True)

    # winget
    rc, out, err = _run_cmd(["winget", "--version"])
    if rc == 0:
        rc, out, err = _run_cmd(["winget", "install", "--id", "AngryIP.AngrYipscanner", "-e", "--accept-source-agreements", "--accept-package-agreements"])
        if rc == 0:
            return True, "Instalado via winget"

    # chocolatey
    rc, out, err = _run_cmd(["choco", "--version"])
    if rc == 0:
        rc, out, err = _run_cmd(["choco", "install", "angryip", "-y"])
        if rc == 0:
            return True, "Instalado via chocolatey"

    # descargar release asset
    asset_url = _find_release_asset_url()
    if asset_url:
        try:
            tmpfd, tmppath = tempfile.mkstemp(suffix=os.path.basename(asset_url))
            os.close(tmpfd)
            _download_url_to_file(asset_url, tmppath)
            if tmppath.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(tmppath, 'r') as z:
                        z.extractall(ipscan_dir)
                    os.remove(tmppath)
                    return True, f"Extraído portable en {str(ipscan_dir)}"
                except Exception:
                    pass
            # exe -> mover
            dest = ipscan_dir / 'ipscan.exe'
            try:
                shutil.move(tmppath, str(dest))
                dest.chmod(0o755)
                return True, f"Descargado exe en {str(dest)}"
            except Exception:
                if os.path.exists(tmppath):
                    os.remove(tmppath)
        except Exception as e:
            pass

    return False, "No se pudo asegurar Angry IP Scanner automáticamente"

# ----------------------
# Platform-tools (adb) helpers
# ----------------------
def is_adb_available(project_root: str) -> bool:
    # Preferir adb dentro del proyecto (./tools/platform-tools) si existe
    project_root = Path(project_root)
    candidate = project_root / "tools" / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
    if candidate.exists():
        return True
    # comprobar en PATH (sistema)
    if shutil.which("adb"):
        return True
    return False

def try_install_platform_tools(project_root: str) -> (bool, str):
    project_root = Path(project_root)
    tools_root = project_root / "tools"
    plat_dir = tools_root / "platform-tools"
    # 1) intentar winget/choco (si están) — puede instalar globalmente
    rc, out, err = _run_cmd(["winget", "--version"])
    if rc == 0:
        rc, out, err = _run_cmd(["winget", "install", "--id", "Google.AndroidPlatformTools", "-e"])
        if rc == 0:
            return True, "platform-tools instalado via winget"
    rc, out, err = _run_cmd(["choco", "--version"])
    if rc == 0:
        rc, out, err = _run_cmd(["choco", "install", "platform-tools", "-y"])
        if rc == 0:
            return True, "platform-tools instalado via chocolatey"

    # 2) fallback: descargar platform-tools zip oficial y extraer en tools/platform-tools
    try:
        url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
        tools_root.mkdir(parents=True, exist_ok=True)
        tmpfd, tmppath = tempfile.mkstemp(suffix=".zip")
        os.close(tmpfd)
        _download_url_to_file(url, tmppath, timeout=60)
        try:
            with zipfile.ZipFile(tmppath, 'r') as z:
                # extraer dentro de tools_root; usualmente zip contiene carpeta 'platform-tools'
                z.extractall(tools_root)
            os.remove(tmppath)
            # si la zip extrae 'platform-tools' ya estarás bien; si extrae directamente, moverlo
            if (tools_root / "platform-tools").exists():
                return True, f"platform-tools extraído en {str(tools_root/'platform-tools')}"
            else:
                # intentar detectar carpeta dentro de tools_root
                for child in tools_root.iterdir():
                    if child.is_dir() and "platform-tools" in child.name:
                        return True, f"platform-tools extraído en {str(child)}"
        except Exception as e:
            if os.path.exists(tmppath):
                os.remove(tmppath)
    except Exception as e:
        pass

    return False, "No se instaló platform-tools (intenta colocar platform-tools en ./tools/platform-tools)"

# ----------------------
# scrcpy helpers
# ----------------------
def is_scrcpy_available(project_root: str) -> bool:
    if shutil.which("scrcpy"):
        return True
    exe_name = "scrcpy.exe" if os.name == "nt" else "scrcpy"
    scrcpy_path = Path(project_root) / "tools" / "scrcpy-win64" / exe_name
    if scrcpy_path.exists():
        return True
    return False

def try_install_scrcpy(project_root: str) -> (bool, str):
    project_root = Path(project_root)
    tools_root = project_root / "tools"
    scrcpy_dir = tools_root / "scrcpy-win64"

    # 1) intentar winget/choco
    rc, out, err = _run_cmd(["winget", "--version"])
    if rc == 0:
        rc, out, err = _run_cmd(["winget", "install", "--id", "Genymobile.scrcpy", "-e"])
        if rc == 0:
            return True, "scrcpy instalado via winget"
    rc, out, err = _run_cmd(["choco", "--version"])
    if rc == 0:
        rc, out, err = _run_cmd(["choco", "install", "scrcpy", "-y"])
        if rc == 0:
            return True, "scrcpy instalado via chocolatey"

    # 2) fallback: intentar descargar release portable de GitHub (buscar asset ZIP/7z)
    try:
        # Reusar lógica similar a ipscan: buscar en releases/latest y descargar asset portable
        asset_url = None
        try:
            req = urllib.request.Request("https://github.com/Genymobile/scrcpy/releases/latest", headers={"User-Agent":"python-urllib"})
            with urllib.request.urlopen(req, timeout=15) as r:
                final_url = r.geturl()
        except Exception:
            final_url = "https://github.com/Genymobile/scrcpy/releases/latest"
        try:
            req = urllib.request.Request(final_url, headers={"User-Agent":"python-urllib"})
            with urllib.request.urlopen(req, timeout=20) as r:
                page = r.read().decode("utf-8", errors="ignore")
            matches = re.findall(r'href=\"([^\"]*(?:windows-[^\"]*|scrcpy-win64)[^\"]*\.(?:zip|7z))\"', page, flags=re.IGNORECASE)
            if not matches:
                matches = re.findall(r'href=\"([^\"]*scrcpy[^\"]*\\.(?:zip|7z))\"', page, flags=re.IGNORECASE)
            if matches:
                href = matches[0]
                asset_url = href if href.startswith("http") else urllib.parse.urljoin("https://github.com", href)
        except Exception:
            asset_url = None

        if asset_url:
            tools_root.mkdir(parents=True, exist_ok=True)
            tmpfd, tmppath = tempfile.mkstemp(suffix=os.path.basename(asset_url))
            os.close(tmpfd)
            _download_url_to_file(asset_url, tmppath)
            try:
                # extraer en scrcpy_dir
                scrcpy_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(tmppath, 'r') as z:
                    z.extractall(scrcpy_dir)
                os.remove(tmppath)
                return True, f"scrcpy extraído en {str(scrcpy_dir)}"
            except Exception:
                # podría ser 7z -> no soportado por zipfile; en ese caso, mover exe si existe
                dest = scrcpy_dir / 'scrcpy.exe'
                try:
                    shutil.move(tmppath, str(dest))
                    dest.chmod(0o755)
                    return True, f"scrcpy descargado en {str(dest)}"
                except Exception:
                    if os.path.exists(tmppath):
                        os.remove(tmppath)
    except Exception:
        pass

    return False, "No se instaló scrcpy automáticamente. Coloca scrcpy en ./tools/scrcpy-win64"

# ----------------------
# Añadir tools/* al PATH de la sesión
# ----------------------
def add_tools_to_path(project_root: str):
    project_root = Path(project_root)
    tools_dir = project_root / "tools"
    parts = []
    # Añadir la raíz tools y subcarpetas conocidas
    if tools_dir.exists():
        parts.append(str(tools_dir))
    for name in ("platform-tools", "scrcpy-win64", "ipscan"):
        p = tools_dir / name
        if p.exists():
            parts.append(str(p))
    if parts:
        os.environ["PATH"] = os.pathsep.join(parts) + os.pathsep + os.environ.get("PATH", "")

# ----------------------
# ensure_tools: orquestador
# ----------------------
def ensure_tools(project_root: str = None):
    """
    Intenta asegurar adb, scrcpy y angry ip scanner.
    Devuelve un dict con el estado de cada herramienta y además imprime
    información detallada (versiones / ubicaciones) en stdout.
    Se asegura de usar project_root/tools como destino.
    """
    # determinar project_root y garantizar Path
    if project_root is None:
        project_root = Path(__file__).resolve().parent
    project_root = Path(project_root)

    # --- Forzar uso de tools/ dentro del proyecto ---
    tools_root = project_root / "tools"
    try:
        tools_root.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[!] No se pudo crear {tools_root}: {e}")

    res = {
        "adb": {"ok": False, "msg": ""},
        "scrcpy": {"ok": False, "msg": ""},
        "ipscan": {"ok": False, "msg": ""}
    }

    # Helper local para ejecutar comandos y obtener salida
    def _run_and_capture(cmd):
        try:
            rc, out, err = _run_cmd(cmd)
            return rc, out, err
        except Exception as e:
            return -1, "", str(e)

    print(f"[*] Asegurando herramientas en: {project_root}")
    print(f"[*] tools root = {tools_root}")

    # Preferir candidato adb en tools/platform-tools si existe (debug/info)
    candidate_adb = tools_root / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
    if candidate_adb.exists():
        print(f"[*] adb candidato en: {candidate_adb}")

    # ----------------------
    # ADB
    # ----------------------
    try:
        if is_adb_available(project_root):
            res["adb"]["ok"] = True
            # intentar obtener versión
            rc, out, err = _run_and_capture(["adb", "version"])
            if rc == 0 and out:
                res["adb"]["msg"] = out.splitlines()[0]
            elif err:
                res["adb"]["msg"] = err
            else:
                res["adb"]["msg"] = "adb en PATH o tools/platform-tools"
            print(f"[ADB] OK -> {res['adb']['msg']}")
        else:
            # intentar instalar usando instaladores del sistema (winget/choco)
            ok, msg = try_install_platform_tools(project_root)
            res["adb"]["ok"] = bool(ok)
            res["adb"]["msg"] = msg
            print(f"[ADB] Instalación intentada -> {msg}")

            # si no se instaló via package manager, NO tocar System32:
            # comprobar si hay un zip/local para extraer en tools_root (no implementado aquí)
            # NOTE: mantener la política de no escribir en System32
            if not res["adb"]["ok"]:
                print("[ADB] No instalado por package manager. Asegúrate de colocar platform-tools en ./tools/platform-tools")

            # si ahora está disponible, intentar versión
            if res["adb"]["ok"]:
                rc, out, err = _run_and_capture(["adb", "version"])
                if rc == 0 and out:
                    print(f"[ADB] Versión: {out.splitlines()[0]}")
    except Exception as e:
        res["adb"]["ok"] = False
        res["adb"]["msg"] = f"error: {e}"
        print(f"[ADB] Error comprobando/instalando: {e}")

    # ----------------------
    # scrcpy
    # ----------------------
    try:
        if is_scrcpy_available(project_root):
            res["scrcpy"]["ok"] = True
            rc, out, err = _run_and_capture(["scrcpy", "--version"])
            if rc == 0 and (out or err):
                first = out.splitlines()[0] if out else (err.splitlines()[0] if err else "scrcpy disponible")
                res["scrcpy"]["msg"] = first
            else:
                res["scrcpy"]["msg"] = "scrcpy en PATH o tools/scrcpy-win64"
            print(f"[SCRCPY] OK -> {res['scrcpy']['msg']}")
        else:
            ok, msg = try_install_scrcpy(project_root)
            res["scrcpy"]["ok"] = bool(ok)
            res["scrcpy"]["msg"] = msg
            print(f"[SCRCPY] Instalación intentada -> {msg}")
            if res["scrcpy"]["ok"]:
                rc, out, err = _run_and_capture(["scrcpy", "--version"])
                if rc == 0 and out:
                    print(f"[SCRCPY] Versión: {out.splitlines()[0]}")
    except Exception as e:
        res["scrcpy"]["ok"] = False
        res["scrcpy"]["msg"] = f"error: {e}"
        print(f"[SCRCPY] Error comprobando/instalando: {e}")

    # ----------------------
    # Angry IP Scanner (ipscan)
    # ----------------------
    try:
        ok, msg = install_angry_ip_scanner(project_root)
        res["ipscan"]["ok"] = bool(ok)
        res["ipscan"]["msg"] = str(msg)
        print(f"[IPSCAN] Resultado -> {res['ipscan']['msg']}")
        # si se extrajo en tools/ipscan, listar ejecutable si existe
        if res["ipscan"]["ok"]:
            ipscan_path_candidates = [
                tools_root / "ipscan" / "ipscan.exe",
                tools_root / "ipscan" / "ipscan",
            ]
            for p in ipscan_path_candidates:
                if p.exists():
                    print(f"[IPSCAN] Ejecutable encontrado en: {str(p)}")
                    break
    except Exception as e:
        res["ipscan"]["ok"] = False
        res["ipscan"]["msg"] = f"error: {e}"
        print(f"[IPSCAN] Error comprobando/instalando: {e}")

    # Añadir tools/* al PATH de la sesión
    try:
        add_tools_to_path(project_root)
        print("[*] tools/* añadidos al PATH de la sesión (si existen).")
    except Exception as e:
        print(f"[*] No se pudo añadir tools al PATH: {e}")

    # Debug final: mostrar qué adb se resolvería en PATH y contenido de tools
    try:
        import shutil as _sh
        adb_path = _sh.which("adb")
        print(f"[*] adb resuelto en PATH a: {adb_path}")
        for p in (tools_root, tools_root / "platform-tools"):
            if p.exists():
                print(f"[*] Contenido {p}:")
                for x in sorted(p.iterdir()):
                    print("   ", x.name)
    except Exception:
        pass

    # Resumen final impreso
    print("==== Estado de herramientas ====")
    for k, v in res.items():
        estado = "OK" if v["ok"] else "FALTA"
        print(f"{k.upper():8} -> {estado} | {v['msg']}")
    print("================================")

    return res

# Si ejecutas este fichero directamente para probar:
if __name__ == '__main__':
    proj = os.getcwd()
    print("Asegurando herramientas en:", proj)
    r = ensure_tools(proj)
    print(json.dumps(r, indent=2, ensure_ascii=False))
