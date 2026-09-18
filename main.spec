# -*- mode: python ; coding: utf-8 -*-

import os
import site
import subprocess
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

# Validate the actual bundled runtime against this build's JPype before packaging.
project_dir = Path(SPECPATH)
os.chdir(project_dir)
java_dll = project_dir / 'runtime/jre17/bin/server/jvm.dll'
release_file = project_dir / 'runtime/jre17/release'
if not java_dll.is_file() or not release_file.is_file():
    raise RuntimeError('A complete Java 17 runtime is required in runtime/jre17')
release = dict(line.split('=', 1) for line in release_file.read_text().splitlines() if '=' in line)
if not release.get('JAVA_VERSION', '').strip('"').startswith('17.'):
    raise RuntimeError('runtime/jre17 must contain Java 17')
subprocess.run([sys.executable, '-c',
                'import jpype, sys; jpype.startJVM(sys.argv[1]); '
                'print("Build runtime validated:", jpype.getJVMVersion()); jpype.shutdownJVM()',
                str(java_dll)], check=True)

os.environ["BMOD_PYINSTALLER_ANALYSIS"] = "1"
site.getusersitepackages = lambda: ""

block_cipher = None

# Bundle certifi CA bundle so SSL (e.g. GitHub API) works on all machines
certifi_datas = collect_data_files('certifi')
app_datas = certifi_datas + [
    ('ui/ui_sources', 'ui/ui_sources'),
    ('tools', 'tools'),
    ('runtime/jre17', 'runtime/jre17'),
    ('splash.png', '.'),
    ('license.txt', '.'),
    ('core/core/ffdec/ffdec_lib.jar', 'core/core/ffdec'),
    ('core/core/ffdec/cmykjpeg.jar', 'core/core/ffdec'),
    ('core/core/ffdec/jl1.0.1.jar', 'core/core/ffdec'),
    ('core/core/ffdec/playerglobal32_0.swc', 'core/core/ffdec'),
    ('core/core/ffdec/lib', 'core/core/ffdec/lib'),
]

a = Analysis(['run.py'],
             binaries=[],
             datas=app_datas,
             hiddenimports=['win32api', 'win32con', 'win32timezone', 'jpype', 'jpype._jvmfinder',
                            'pyi_splash', 'certifi', 'requests', 'psutil',
                            'multiprocessing.popen_spawn_win32'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['tkinter', '_tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
splash = Splash('splash.png',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=(153, 231),
                text_font="Exo",
                text_size=13,
                text_color='#92B7D1')
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          Tree("core/core", "core/core", excludes=["*.pyc", "*.pyo"]),
          [],
          splash,
          splash.binaries,
          name='Brawlhalla Mod Creator 2025 Beta',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=['vcruntime140.dll', 'ucrtbase.dll'],
          runtime_tmpdir=None,
          version='version.spec',
          console=False,
          uac_admin=False,
          icon='ui/ui_sources/resources/icons/App.ico')
