# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for ChronoMate Desktop.

  Windows : single portable dist/ChronoMate.exe
  macOS   : dist/ChronoMate.app
  Linux   : dist/chronomate/ (onedir, wrapped into .deb/.rpm/.tar.gz by the release workflow)

Run `python packaging/make_icons.py` first, then
`pyinstaller packaging/chronomate.spec --noconfirm` from the repository root.
"""

import os
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
ICONS = ROOT / "packaging" / "build-icons"
VERSION = os.environ.get("CHRONOMATE_VERSION", "1.0.0")

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

icon = None
if IS_WIN:
    icon = str(ICONS / "chronomate.ico")
elif IS_MAC:
    icon = str(ICONS / "chronomate.icns")

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / "assets" / "logo.png"), "assets"),
           (str(ROOT / "assets" / "sounds"), "assets/sounds")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if IS_WIN:
    # One portable executable
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="ChronoMate",
        console=False,
        icon=icon,
        upx=False,
    )
else:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="chronomate",
        console=False,
        icon=icon,
        upx=False,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="chronomate", upx=False)

    if IS_MAC:
        app = BUNDLE(
            coll,
            name="ChronoMate.app",
            icon=icon,
            bundle_identifier="com.ghostwarriorcommando.chronomate",
            info_plist={
                "CFBundleName": "ChronoMate",
                "CFBundleDisplayName": "ChronoMate Desktop",
                "CFBundleShortVersionString": VERSION,
                "CFBundleVersion": VERSION,
                "NSHighResolutionCapable": True,
                "LSMinimumSystemVersion": "11.0",
            },
        )
