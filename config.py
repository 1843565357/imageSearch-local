import os
import sys

# 获取 EXE 所在的真实目录（而不是临时目录）
if getattr(sys, 'frozen', False):
    # 打包后的环境
    BASE_DIR = os.path.dirname(sys.executable)
    # 内部资源目录（用于加载打包进去的 style.qss）
    INTERNAL_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    # 源代码运行环境
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INTERNAL_DIR = BASE_DIR

# 数据库和图片存放在 EXE 同级目录，保证持久化
DB_FOLDER = os.path.join(BASE_DIR, "database")
DB_NAME = "image.db"
STORAGE_DIR = os.path.join(BASE_DIR, "images")

# 模型建议也放在外部目录，避免打包体积过大
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_NAME = "dinov2_vitb14"

# 动态生成 QSS 路径
STYLE_PATH = os.path.join(INTERNAL_DIR, "style.qss")

# 确保文件夹存在
for folder in [DB_FOLDER, STORAGE_DIR, MODEL_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)