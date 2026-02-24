# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

# 1. 路径配置
env_path = r'E:\enviroment\Anaconda_envs\envs\Image-App'
env_bin = os.path.join(env_path, 'Library', 'bin')
project_root = os.getcwd()

datas = [('database', 'database'), ('assets/style.qss', 'assets')]
binaries = []
hiddenimports = ['numpy.core._multiarray_umath']

# 2. 收集零件
for lib in ['torch', 'torchvision', 'faiss', 'numpy', 'PyQt5']:
    tmp_ret = collect_all(lib)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# 3. 核心补丁
needed_dlls = ['libiomp5md.dll', 'mkl_rt.2.dll', 'mkl_core.2.dll', 'mkl_intel_thread.2.dll', 'python310.dll']
for dll in needed_dlls:
    src = os.path.join(env_bin, dll) if os.path.exists(os.path.join(env_bin, dll)) else os.path.join(env_path, dll)
    if os.path.exists(src):
        binaries.append((src, '.'))

a = Analysis(
    ['main.py'],
    pathex=[env_bin, os.path.join(env_path, 'Lib', 'site-packages')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    # 优化点 1：排除掉占位置的大型无关模块
    excludes=['matplotlib', 'notebook', 'scipy', 'pandas', 'IPython', 'tensorboard', 'jedi', 'tkinter', 'tests'],
    noarchive=False,
)

# 删掉 GPU 相关 DLL
blacklist = [
    'nvrtc', 'cuda', 'cudnn', 'cublas', 'curand', 'cusolver', 'cusparse', 'cufft', # GPU 相关
    'mkl_avx512', 'mkl_vml_avx512',
    'libxml2', 'libxslt', 'icu'
]

a.binaries = [x for x in a.binaries if not any(b in os.path.basename(x[1]).lower() for b in blacklist)]
a.datas = [x for x in a.datas if not any(b in x[0].lower() for b in blacklist)]
# =========================================================

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ImageSearch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=None,           # 如果你有 ico 图标可以加在这里
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=False,
    name='ImageSearch',
)