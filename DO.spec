# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Distortion Observer
Build: pyinstaller DO.spec
"""

block_cipher = None

a = Analysis(
    ['do_launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/icon.ico', 'assets'),
    ],
    hiddenimports=[
        # DO Core
        'DO',
        'DO.core',
        'DO.core.kernel',
        'DO.core.models',
        'DO.core.causal',
        'DO.core.distortion',
        'DO.core.health',
        'DO.core.flow',
        'DO.core.timeline',
        'DO.core.bus',
        'DO.core.flow_bus',
        'DO.core.analyzer',
        # DO View
        'DO.view',
        'DO.view.workspace',
        'DO.view.canvas_2d',
        'DO.view.canvas_3d',
        'DO.view.colors',
        'DO.view.top_bar',
        'DO.view.timeline_bar',
        'DO.view.flow_layer',
        'DO.view.insight_panel',
        # DO Boundary
        'DO.boundary',
        'DO.boundary.server',
        'DO.boundary.kernel_api',
        'DO.boundary.timeline_api',
        'DO.boundary.analyzer_api',
        'DO.boundary.storage',
        # stdlib
        'tkinter',
        'tkinter.ttk',
        'http.server',
        'urllib.parse',
        'threading',
        'json',
        'math',
        'random',
        'time',
        'dataclasses',
        'pathlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
        'pytest',
        'IPython',
        'notebook',
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
    name='DistortionObserver',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DistortionObserver',
)
