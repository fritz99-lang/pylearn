# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for PyLearn.

Build:  pyinstaller pylearn.spec
Output:
  Windows: dist/PyLearn/PyLearn.exe
  macOS:   dist/PyLearn.app
  Linux:   dist/PyLearn/PyLearn
"""

import sys
from pathlib import Path

block_cipher = None

# Project root (where this spec file lives)
ROOT = Path(SPECPATH)

# --- Platform-conditional icon ---
if sys.platform == "win32":
    app_icon = str(ROOT / "assets" / "pylearn.ico")
elif sys.platform == "darwin":
    icns_path = ROOT / "assets" / "pylearn.icns"
    app_icon = str(icns_path) if icns_path.exists() else None
else:
    app_icon = None

a = Analysis(
    [str(ROOT / "src" / "pylearn" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(ROOT / "config" / "books.json.example"), "config"),
        (str(ROOT / "config" / "app_config.json.example"), "config"),
        (str(ROOT / "config" / "editor_config.json.example"), "config"),
    ],
    hiddenimports=[
        # PyMuPDF
        "fitz",
        "pymupdf",
        # QScintilla
        "PyQt6.Qsci",
        # Pygments lexers used by the renderer
        "pygments.lexers.python",
        "pygments.lexers.c_cpp",
        "pygments.formatters.html",
        "pygments.styles",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Unused Qt modules — saves ~50-100 MB
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.QtQuickWidgets",
        "PyQt6.QtWebEngine",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebChannel",
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtBluetooth",
        "PyQt6.QtNfc",
        "PyQt6.QtPositioning",
        "PyQt6.QtRemoteObjects",
        "PyQt6.QtSensors",
        "PyQt6.QtSerialPort",
        "PyQt6.QtTest",
        "PyQt6.Qt3DCore",
        "PyQt6.Qt3DRender",
        "PyQt6.Qt3DInput",
        "PyQt6.Qt3DLogic",
        "PyQt6.Qt3DExtras",
        "PyQt6.Qt3DAnimation",
        # Other unused stdlib/third-party
        "tkinter",
        "unittest",
        "xmlrpc",
        "pydoc",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PyLearn",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # --windowed: no console window
    disable_windowed_traceback=False,
    argv_emulation=(sys.platform == "darwin"),
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=app_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PyLearn",
)

# --- macOS .app bundle ---
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="PyLearn.app",
        icon=app_icon,
        bundle_identifier="com.natetritle.pylearn",
        info_plist={
            "CFBundleDisplayName": "PyLearn",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
        },
    )
