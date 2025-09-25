import os, sys, subprocess

base = os.path.dirname(__file__)
tools = os.path.join(base, "tools", "platform-tools")
os.environ["PATH"] = tools + os.pathsep + os.environ["PATH"]

subprocess.run([sys.executable, "main.py"])
