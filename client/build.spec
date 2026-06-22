# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

icon_path = 'resources/client_icon.ico'
if not os.path.exists(icon_path):
    icon_path = None

shared_root = os.path.join('..', 'shared')


def make_analysis(entry_script, extra_hidden=None):
    hidden = [
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'requests',
        'websocket',
        'psutil',
        'win32serviceutil',
        'win32service',
        'win32event',
        'servicemanager',
        'shared.system_cleanup',
        'services.config_manager',
        'services.watchdog_install',
    ]
    if extra_hidden:
        hidden.extend(extra_hidden)
    return Analysis(
        [entry_script],
        pathex=['.', '..', shared_root],
        binaries=[],
        datas=[
            (shared_root, 'shared'),
            ('config.example.json', '.'),
        ],
        hiddenimports=hidden,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher,
        noarchive=False,
    )


a_client = make_analysis('main.py')
pyz_client = PYZ(a_client.pure, a_client.zipped_data, cipher=block_cipher)
exe_client = EXE(
    pyz_client,
    a_client.scripts,
    [],
    exclude_binaries=True,
    name='CyberCafe Client',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

a_watchdog = make_analysis('services/watchdog_service.py')
pyz_watchdog = PYZ(a_watchdog.pure, a_watchdog.zipped_data, cipher=block_cipher)
exe_watchdog = EXE(
    pyz_watchdog,
    a_watchdog.scripts,
    [],
    exclude_binaries=True,
    name='CyberCafeWatchdog',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

a_cleanup = make_analysis('uninstall_cleanup.py', ['winreg'])
pyz_cleanup = PYZ(a_cleanup.pure, a_cleanup.zipped_data, cipher=block_cipher)
exe_cleanup = EXE(
    pyz_cleanup,
    a_cleanup.scripts,
    [],
    exclude_binaries=True,
    name='CyberCafeCleanup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_client,
    exe_watchdog,
    exe_cleanup,
    a_client.binaries,
    a_client.zipfiles,
    a_client.datas,
    a_watchdog.binaries,
    a_watchdog.zipfiles,
    a_watchdog.datas,
    a_cleanup.binaries,
    a_cleanup.zipfiles,
    a_cleanup.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CyberCafe Client',
)
