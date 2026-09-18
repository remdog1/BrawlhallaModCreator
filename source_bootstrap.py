"""Select a project Python without changing Windows file associations."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys


def ensure_source_python():
    if getattr(sys, 'frozen', False):
        return
    root = Path(__file__).resolve().parent
    os.chdir(root)
    required = ('PySide6', 'jpype', 'win32api', 'requests', 'psutil', 'certifi', 'packaging')
    if all(importlib.util.find_spec(name) is not None for name in required):
        return
    candidates = (root.parent / 'build-env/Scripts/python.exe',
                  root / '.venv/Scripts/python.exe')
    probe = 'from PySide6.QtWidgets import QApplication; import jpype, win32api, requests, psutil, certifi, packaging'
    for python in candidates:
        if not python.is_file() or python.resolve() == Path(sys.executable).resolve():
            continue
        try:
            result = subprocess.run([str(python), '-c', probe], capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            raise SystemExit(subprocess.call([str(python), str(root / 'run.py'), *sys.argv[1:]], cwd=root))
    raise RuntimeError('No complete creator Python environment found. Run Start Creator.cmd to see the error, '
                       'or install requirements.txt into a project virtual environment.')
