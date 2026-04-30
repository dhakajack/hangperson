# PyInstaller spec for building the wxPython desktop app.
#
# Avoid collecting every wxPython submodule: that pulls in deprecated, internal,
# platform-specific modules the app does not use and can produce noisy hidden
# import errors. PyInstaller detects the main wx imports from hangperson_wx.py;
# keep only explicit wx add-ons used by the app.

from pathlib import Path

hiddenimports = ["wx.adv"]

runtime_word_files = [
    (str(path), "data") for path in sorted(Path("data").glob("words_*.txt"))
]

datas = [
    ("assets", "assets"),
    ("data/difficulty", "data/difficulty"),
    ("data/locales", "data/locales"),
] + runtime_word_files

a = Analysis(
    ["hangperson_wx.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Hangperson",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Hangperson",
)

app = BUNDLE(
    coll,
    name="Hangperson.app",
    icon=None,
    bundle_identifier=None,
)
