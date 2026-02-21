# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

# 1. 路径配置
env_path = r'E:\enviroment\Anaconda_envs\envs\Image-App'
env_bin = os.path.join(env_path, 'Library', 'bin')
project_root = os.getcwd()

datas = [('database', 'database'), ('style.qss', '.')]
binaries = []
hiddenimports = ['numpy.core._multiarray_umath']

# 2. 收集零件
for lib in ['torch', 'torchvision', 'faiss', 'numpy', 'PyQt5']:
    tmp_ret = collect_all(lib)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# 3. 核心补丁：保留 c10 命根子，其他的等下切掉
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

# =========================================================
# 优化点 2：物理切除逻辑 (关键瘦身步骤)
# 这里会强行删掉体积巨大的 GPU 相关 DLL
# =========================================================
blacklist = [
    'nvrtc', 'cuda', 'cudnn', 'cublas', 'curand', 'cusolver', 'cusparse', 'cufft', # GPU 相关
    'mkl_avx512', 'mkl_vml_avx512', # 巨大的服务器数学库
    'libxml2', 'libxslt', 'icu'      # 冗余工具
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
    name='VisionSearchPro',
    debug=False,         # 优化点 3：关闭调试
    bootloader_ignore_signals=False,
    strip=True,          # 优化点 4：开启剥离，减小体积
    upx=False,           # ⚠️ Torch 依然不建议开启 UPX
    console=False,       # 优化点 5：关闭黑窗口，恢复前端界面效果
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
    name='VisionSearchPro',
)