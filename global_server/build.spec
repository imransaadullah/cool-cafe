# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
shared_root = os.path.join('..', 'shared')
prisma_root = os.path.join('..', 'prisma')

common_datas = [
    (shared_root, 'shared'),
    (prisma_root, 'prisma'),
    ('../.env.example', '.'),
]

common_hidden = [
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan', 'uvicorn.lifespan.on',
    'starlette', 'fastapi', 'pydantic', 'pydantic_settings',
    'prisma', 'prisma.models', 'prisma.engine', 'prisma.engine.query',
    'httpx', 'jose', 'passlib', 'bcrypt',
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'PyQt6.QtNetwork',
    'shared.config', 'shared.database', 'shared.utils.auth', 'shared.qt_single_instance',
    'global_server.app.main',
    'global_server.app.routes.auth', 'global_server.app.routes.branches',
    'global_server.app.routes.sync', 'global_server.app.routes.dashboard',
    'global_server.app.services.sync_processor',
    'global_server.services.install_config', 'global_server.services.setup_runner',
    'global_server.ui.setup_wizard',
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
    pyz_manager, a_manager.scripts, [],
    exclude_binaries=True,
    name='CyberCafe Global Server',
    debug=False, strip=False, upx=True, console=False,
    disable_windowed_traceback=False, argv_emulation=False,
)

coll = COLLECT(
    exe_manager,
    a_manager.binaries, a_manager.zipfiles, a_manager.datas,
    strip=False, upx=True, upx_exclude=[],
    name='CyberCafe Global Server',
)
