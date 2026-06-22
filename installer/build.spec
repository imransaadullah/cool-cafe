# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for CyberCafe unified graphical installer."""

import os
from pathlib import Path

block_cipher = None
spec_dir = Path(SPECPATH).resolve()
repo = spec_dir.parent
payload = repo / "deploy" / "installer" / "payload"

datas = []
if payload.is_dir():
    for role in ("local_server", "global_server", "client"):
        src = payload / role
        if src.is_dir():
            datas.append((str(src), os.path.join("payload", role)))

a = Analysis(
    [str(spec_dir / "main.py")],
    pathex=[str(repo)],
    binaries=[],
    datas=datas,
    hiddenimports=["installer.gui.main", "installer.services.install_engine", "installer.services.payload"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CyberCafe Setup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
