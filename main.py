import sys
import os
import logging
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMainWindow
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer
import config

# 初始化日志
logging.basicConfig(level=logging.INFO)


def main():
    app = QApplication(sys.argv)

    # 1. 立即显示闪屏 (不要等任何初始化)
    # 建议在 assets 下放一张 splash.png 图片
    splash_path = os.path.join(config.INTERNAL_DIR, "assets", "splash.png")

    # 如果没图片，可以先用颜色块占位测试
    pixmap = QPixmap(splash_path) if os.path.exists(splash_path) else QPixmap(600, 400)
    if not os.path.exists(splash_path): pixmap.fill(Qt.lightGray)

    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.show()

    # 在闪屏上显示文字提示
    def update_msg(text):
        splash.showMessage(f" {text}...", Qt.AlignBottom | Qt.AlignLeft, Qt.white)
        app.processEvents()  # 强制让界面刷新，不卡死

    update_msg("正在启动 VisionSearch Pro")

    # 2. 开始执行耗时的初始化逻辑
    try:
        # 加载 DINOv2 模型
        update_msg("正在加载 AI 推理模型 (DINOv2)")
        from model_manager import model_image
        model_image.load_model(config.MODEL_DIR, config.MODEL_NAME)

        # 加载数据库与索引
        update_msg("正在初始化向量索引 (FAISS)")
        from database import db_manager
        from index_manager import index_manager
        index_manager.load_from_db(db_manager)

        # 加载主界面
        update_msg("正在构建用户界面")
        from main_app import MainApp  # 建议把 MainApp 类移到单独文件，或者留在下面
        gui = MainApp()

    except Exception as e:
        logging.error(f"启动失败: {str(e)}")
        splash.showMessage(f"错误: {str(e)}", Qt.AlignCenter, Qt.red)
        # 给用户留 3 秒看清楚报错再退出
        QTimer.singleShot(3000, lambda: sys.exit(1))
        return

    # 3. 初始化完成，切换窗口
    gui.show()
    splash.finish(gui)  # 当主窗口显示后，关闭闪屏
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()