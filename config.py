import os
import sys
import json

# --- 1. 基础路径定位 (这部分保持不动) ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    INTERNAL_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INTERNAL_DIR = BASE_DIR

CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")

# --- 2. 配置读写逻辑 ---
DEFAULT_CONFIG = {
    "model_dir": os.path.join(BASE_DIR, "models"),
    "model_name": "dinov2_vitb14",
    "db_folder": os.path.join(BASE_DIR, "database"),
    "storage_dir": os.path.join(BASE_DIR, "images")
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG


def save_config(config_data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)


# --- 3. 核心：定义全局变量并导出 ---
# 这些变量名必须存在，否则其他文件会报 AttributeError
MODEL_DIR = ""
MODEL_NAME = ""
DB_FOLDER = ""
STORAGE_DIR = ""
DB_NAME = "image.db"
STYLE_PATH = os.path.join(INTERNAL_DIR, "assets", "style.qss")


def update_vars():
    """刷新内存中的全局变量，让其他文件能实时拿到新路径"""
    global MODEL_DIR, MODEL_NAME, DB_FOLDER, STORAGE_DIR
    cfg = load_config()
    MODEL_DIR = cfg["model_dir"]
    MODEL_NAME = cfg["model_name"]
    DB_FOLDER = cfg["db_folder"]
    STORAGE_DIR = cfg["storage_dir"]

    # 顺便确保新路径文件夹存在
    for folder in [MODEL_DIR, DB_FOLDER, STORAGE_DIR]:
        if not os.path.exists(folder): os.makedirs(folder)


# 启动程序时，立刻初始化一次变量
update_vars()