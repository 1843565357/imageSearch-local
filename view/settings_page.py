from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QFrame, QPushButton
from PyQt5.QtCore import Qt


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(10)

        # 页面标题
        title = QLabel("系统设置")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        layout.addSpacing(20)

        # 设置区域容器（给一组设置加个背景边框）
        settings_container = QFrame()
        settings_container.setObjectName("CardFrame")
        container_layout = QVBoxLayout(settings_container)
        container_layout.setContentsMargins(10, 5, 10, 5)
        container_layout.setSpacing(0)

        # 添加设置条目
        container_layout.addWidget(self.create_setting_item(
            "模型引擎路径", "models/dinov2_vits14_pretrain.pth", "指定 DINOv2 权重文件的本地路径"
        ))
        container_layout.addWidget(self.create_setting_item(
            "FAISS 索引", "data/vector.index", "向量特征库的存储位置"
        ))
        container_layout.addWidget(self.create_setting_item(
            "数据库文件", "data/metadata.db", "用于存储图片路径与 ID 的 SQLite 文件"
        ))

        layout.addWidget(settings_container)

        # 底部操作按钮
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存配置")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.setFixedSize(120, 35)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def create_setting_item(self, label, value, hint):
        """创建一个横向的设置条目部件"""
        item_widget = QWidget()
        item_widget.setObjectName("SettingItem")  # 用于 QSS 定位
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(15, 15, 15, 15)

        # 左侧文字区
        text_v_layout = QVBoxLayout()
        lbl_main = QLabel(label)
        lbl_main.setStyleSheet("font-weight: bold; font-size: 14px; color: #1c1c1e;")
        lbl_hint = QLabel(hint)
        lbl_hint.setStyleSheet("color: #8e8e93; font-size: 12px;")
        text_v_layout.addWidget(lbl_main)
        text_v_layout.addWidget(lbl_hint)

        # 右侧输入框
        edit = QLineEdit(value)
        edit.setFixedWidth(300)
        edit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        item_layout.addLayout(text_v_layout)
        item_layout.addStretch()
        item_layout.addWidget(edit)

        return item_widget