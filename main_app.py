import os
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QStackedWidget
from PyQt5.QtCore import Qt
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
        self.setWindowTitle("ImageSearch Pro")
        self.resize(1100, 800)

        # 核心逻辑初始化
        self.db = db_manager
        self.load_stylesheet(STYLE_PATH)

        # UI 布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- 侧边导航栏 (宽版保留文字) ---
        self.nav_widget = QWidget()
        self.nav_widget.setObjectName("NavWidget")
        self.nav_widget.setFixedWidth(200)  # 宽度恢复到 200
        nav_layout = QVBoxLayout(self.nav_widget)
        nav_layout.setContentsMargins(12, 30, 12, 12)  # 增加内边距
        nav_layout.setSpacing(10)

        # 顶部 Logo 区域
        logo_label = QLabel("ImageSearch")
        logo_label.setObjectName("SidebarLogo")
        logo_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        logo_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #6200EE; margin: 0 10px 30px 10px;")
        nav_layout.addWidget(logo_label)

        # 导航按钮 (带图标和文字)
        self.btn_search = self.create_nav_btn("  🚀   图像搜索")
        self.btn_db = self.create_nav_btn("  📂   数据管理")
        self.btn_sets = self.create_nav_btn("  ⚙️   系统设置")

        self.nav_btns = [self.btn_search, self.btn_db, self.btn_sets]
        for btn in self.nav_btns:
            nav_layout.addWidget(btn)

        nav_layout.addStretch()

        # 底部版本号
        version_label = QLabel("v 0.0.1")
        version_label.setStyleSheet("color: #6200EE; font-weight: bold; margin-left: 10px;")
        nav_layout.addWidget(version_label)

        layout.addWidget(self.nav_widget)

        # --- 右侧内容区 ---
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.stack.addWidget(SearchPage())
        self.stack.addWidget(DBManagementPage())
        self.stack.addWidget(SettingsPage())

        # 绑定事件
        self.btn_search.clicked.connect(lambda: self.switch_page(0))
        self.btn_db.clicked.connect(lambda: self.switch_page(1))
        self.btn_sets.clicked.connect(lambda: self.switch_page(2))

        self.switch_page(0)

    def create_nav_btn(self, text):
        btn = QPushButton(text)
        btn.setObjectName("NavBtn")
        btn.setFixedHeight(50)  # 设置一个合适的高度
        btn.setCursor(Qt.PointingHandCursor)
        return btn

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