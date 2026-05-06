# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for CalendarTaskAI.

Builds two executables in a single onedir bundle so users get both a
silent GUI launcher and a working CLI in the same folder:

  dist/CalendarTaskAI/CalendarTaskAI.exe       <- no console (tray app)
  dist/CalendarTaskAI/CalendarTaskAI-cli.exe   <- with console (CLI)
  dist/CalendarTaskAI/_internal/...            <- shared deps

Both exe wrappers point at the same `main.py` entry; `main.py` already
routes between GUI and CLI based on `sys.argv`. The only difference
between the two is whether Windows attaches a console at launch.

Run with:
  pyinstaller CalendarTaskAI.spec --clean
"""

block_cipher = None


# Hidden imports: PyInstaller's static analysis misses these because they
# are imported indirectly (via __import__, importlib, or platform shims).
# pystray._win32          - pystray's runtime backend selection
# PIL._tkinter_finder     - PIL/Pillow's Tk integration probe
# google.genai            - the SDK has lazy submodule registration
# winreg                  - stdlib but sometimes flagged as missing
HIDDEN_IMPORTS = [
    "pystray._win32",
    "PIL._tkinter_finder",
    "google.genai",
    "winreg",
]


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Skip dev test framework. `tests/` is our directory but it's not a
    # Python package and PyInstaller's static analysis never picks it up
    # from main.py's import graph, so listing it here would be a no-op.
    excludes=["pytest", "_pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


# GUI exe: no console window. Tray app, hotkey, floating Tk window only.
exe_gui = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CalendarTaskAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)


# CLI exe: same code, but launches with a console attached so click
# commands (`add`, `today`, `list`, `backup`, `restore`, etc.) print
# to stdout / stderr normally.
exe_cli = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CalendarTaskAI-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
)


# Shared onedir bundle. Both exes link against the same _internal folder
# of dependencies so the total install is roughly the size of one app.
coll = COLLECT(
    exe_gui,
    exe_cli,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CalendarTaskAI",
)
