# --- 3. 主界面类 ---
import os

from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QStackedWidget

from config import MODEL_DIR, MODEL_NAME, STYLE_PATH
from database import db_manager
from index_manager import index_manager
from model_manager import model_image
from view.db_page import DBManagementPage
from view.search_page import SearchPage
from view.settings_page import SettingsPage


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VisionSearch Pro")
        self.resize(1100, 800)

        # 核心逻辑初始化
        model_image.load_model(MODEL_DIR, MODEL_NAME)
        self.db = db_manager
        index_manager.load_from_db(self.db)
        self.load_stylesheet(STYLE_PATH)

        # UI 布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 侧边栏
        self.nav_widget = QWidget()
        self.nav_widget.setObjectName("NavWidget")
        self.nav_widget.setFixedWidth(200)
        nav_layout = QVBoxLayout(self.nav_widget)
        nav_layout.setContentsMargins(12, 40, 12, 12)

        logo = QLabel("VisionSearch")
        logo.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 30px;")
        nav_layout.addWidget(logo)

        self.btn_search = QPushButton("  🔍  图像搜索")
        self.btn_db = QPushButton("  📂  数据管理")
        self.btn_sets = QPushButton("  ⚙️  系统设置")

        self.nav_btns = [self.btn_search, self.btn_db, self.btn_sets]
        for btn in self.nav_btns:
            btn.setObjectName("NavBtn")
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        layout.addWidget(self.nav_widget)

        # 页面容器
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.stack.addWidget(SearchPage())
        self.stack.addWidget(DBManagementPage())
        self.stack.addWidget(SettingsPage())

        self.btn_search.clicked.connect(lambda: self.switch_page(0))
        self.btn_db.clicked.connect(lambda: self.switch_page(1))
        self.btn_sets.clicked.connect(lambda: self.switch_page(2))
        self.switch_page(0)

    def load_stylesheet(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setObjectName("ActiveNav" if i == index else "NavBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)