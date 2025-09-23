# INSTALL — Instrucciones

1. Clona el repositorio:
```
git clone https://github.com/<tu_usuario>/<tu_repo>.git
cd <tu_repo>
```

2. (Opcional) crea y activa entorno virtual:
```
python -m venv .venv
# PowerShell
.\.venv\Scripts\Activate.ps1
```

3. Instala dependencias si hay `requirements.txt`:
```
pip install -r requirements.txt
```

4. Asegura herramientas:
```
python -c "import setup_tools, os; setup_tools.ensure_tools(os.getcwd())"
```

5. Ejecuta:
```
python main.py
```
