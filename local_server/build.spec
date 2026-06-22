# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

icon_path = 'resources/server_icon.ico'
if not os.path.exists(icon_path):
    icon_path = None

shared_root = os.path.join('..', 'shared')
prisma_root = os.path.join('..', 'prisma')
dashboard_dist = os.path.join('..', 'dashboard', 'frontend', 'dist')

common_datas = [
    (shared_root, 'shared'),
    (prisma_root, 'prisma'),
    ('../.env.example', '.'),
]
if os.path.isdir(dashboard_dist):
    common_datas.append((dashboard_dist, 'dashboard/dist'))

common_hidden = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'starlette',
    'fastapi',
    'pydantic',
    'pydantic_settings',
    'prisma',
    'prisma.models',
    'prisma.engine',
    'prisma.engine.query',
    'httpx',
    'jose',
    'passlib',
    'bcrypt',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'win32serviceutil',
    'win32service',
    'win32event',
    'servicemanager',
    'shared.config',
    'shared.database',
    'shared.utils.auth',
    'shared.qt_single_instance',
    'local_server.app.main',
    'local_server.app.dashboard_static',
    'local_server.app.routes.auth',
    'local_server.app.routes.pcs',
    'local_server.app.routes.sessions',
    'local_server.app.routes.codes',
    'local_server.app.routes.dashboard',
    'local_server.app.routes.filter_rules',
    'local_server.app.routes.payments',
    'local_server.app.routes.content_filter',
    'local_server.app.routes.webhooks',
    'local_server.app.routes.master_codes',
    'local_server.app.routes.branches',
    'local_server.app.routes.branding',
    'local_server.app.routes.security',
    'local_server.app.services.payment',
    'local_server.app.services.printer',
    'local_server.app.services.content_filter',
    'local_server.app.services.revenue',
    'local_server.app.services.sync_worker',
    'local_server.app.websocket',
    'local_server.app.middleware',
    'local_server.app.auth_deps',
    'local_server.services.install_config',
    'local_server.services.setup_runner',
    'local_server.ui.setup_wizard',
    'psycopg2',
]


def make_analysis(entry_script):
    return Analysis(
        [entry_script],
        pathex=['.', '..', shared_root],
        binaries=[],
        datas=common_datas,
        hiddenimports=common_hidden,
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=block_cipher,
        noarchive=False,
    )


a_manager = make_analysis('server_manager.py')
pyz_manager = PYZ(a_manager.pure, a_manager.zipped_data, cipher=block_cipher)
exe_manager = EXE(
    pyz_manager,
    a_manager.scripts,
    [],
    exclude_binaries=True,
    name='CyberCafe Server',
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

a_service = make_analysis('services/server_service.py')
pyz_service = PYZ(a_service.pure, a_service.zipped_data, cipher=block_cipher)
exe_service = EXE(
    pyz_service,
    a_service.scripts,
    [],
    exclude_binaries=True,
    name='CyberCafeServerService',
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
    exe_manager,
    exe_service,
    a_manager.binaries,
    a_manager.zipfiles,
    a_manager.datas,
    a_service.binaries,
    a_service.zipfiles,
    a_service.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CyberCafe Server',
)
