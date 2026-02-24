import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox,
                             QHBoxLayout, QFrame, QPushButton, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt
import config


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.inputs = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 5, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignTop)

        # 1. 页面标题
        layout.addSpacing(20)
        title = QLabel("系统设置")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        layout.addSpacing(10)

        # 2. 设置区域容器
        cfg = config.load_config()
        self.container = QFrame()
        self.container.setObjectName("CardFrame")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(0)

        # --- 设置项定义 ---
        # 路径类：传入对应的回调函数处理确认逻辑
        container_layout.addWidget(self.create_setting_item(
            "model_dir", "模型引擎路径", cfg["model_dir"], "修改后请手动转移权重文件",
            is_path=True, callback=self.on_model_path_changed
        ))

        model_options = ["dinov2_vits14", "dinov2_vitb14", "dinov2_vitl14", "dinov2_vitg14"]
        container_layout.addWidget(self.create_setting_item(
            "model_name", "模型引擎选择", cfg["model_name"], "切换规模将导致现有索引失效",
            options=model_options, callback=self.on_model_name_changed
        ))

        container_layout.addWidget(self.create_setting_item(
            "storage_dir", "图片存储目录", cfg["storage_dir"], "修改后请手动转移图片文件",
            is_path=True, callback=self.on_storage_dir_changed
        ))

        container_layout.addWidget(self.create_setting_item(
            "db_folder", "数据库文件夹", cfg["db_folder"], "存储 SQLite 元数据文件的位置",
            is_path=True, callback=self.on_db_path_changed
        ))

        layout.addWidget(self.container)
        layout.addStretch()  # 撑起底部，去掉原有的保存按钮布局

    # =========================================================
    # 【业务逻辑：先确认，后执行】
    # =========================================================

    def on_model_path_changed(self, new_path):
        """处理模型路径变更"""
        if new_path == config.MODEL_DIR: return

        res = QMessageBox.question(self, "确认修改路径",
                                   "确定更改模型路径吗？\n\n⚠️ 注意：请确保已手动将旧路径下的模型文件转移到新位置。")
        if res == QMessageBox.Yes:
            self.apply_change("model_dir", new_path)
            # 这里可以补全：model_image.load_model(...)

    def on_model_name_changed(self, model_name):
        """处理模型规模切换"""
        if model_name == config.MODEL_NAME: return

        res = QMessageBox.warning(self, "确认切换引擎",
                                  f"确定切换至 {model_name}？\n\n⚠️ 风险：不同规格的模型特征不通用，可能需要重新扫描数据库。")
        if res == QMessageBox.Yes:
            self.apply_change("model_name", model_name)
        else:
            # 取消则将下拉框恢复显示为当前值
            self.inputs["model_name"].setCurrentText(config.MODEL_NAME)

    def on_storage_dir_changed(self, new_path):
        """处理图片存储目录变更"""
        if new_path == config.STORAGE_DIR: return

        res = QMessageBox.question(self, "确认修改", "确定更改图片存储目录？\n建议手动迁移现有图片数据。")
        if res == QMessageBox.Yes:
            self.apply_change("storage_dir", new_path)

    def on_db_path_changed(self, new_path):
        """处理数据库路径变更"""
        if new_path == config.DB_FOLDER: return

        res = QMessageBox.question(self, "确认修改", "确定更改数据库文件夹？\n需手动迁移 .db 和 .index 文件。")
        if res == QMessageBox.Yes:
            self.apply_change("db_folder", new_path)

    def apply_change(self, key, value):
        """执行实际的保存和内存同步"""
        # 1. 更新 UI (针对路径选择的情况)
        if not isinstance(self.inputs[key], QComboBox):
            self.inputs[key].setText(value)

        # 2. 物理保存与内存刷新
        new_data = {k: (v.currentText() if isinstance(v, QComboBox) else v.text())
                    for k, v in self.inputs.items()}
        config.save_config(new_data)
        config.update_vars()
        print(f"配置已更新: {key} -> {value}")

    # =========================================================
    # 辅助工具函数
    # =========================================================

    def create_setting_item(self, key, label, value, hint, options=None, is_path=False, callback=None):
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(20, 20, 20, 20)

        # 文字区
        text_v = QVBoxLayout()
        lbl_main = QLabel(label);
        lbl_main.setStyleSheet("font-weight: bold; font-size: 15px;")
        lbl_hint = QLabel(hint);
        lbl_hint.setStyleSheet("color: #8E8E93; font-size: 12px;")
        text_v.addWidget(lbl_main);
        text_v.addWidget(lbl_hint)
        item_layout.addLayout(text_v);
        item_layout.addStretch()

        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)

        if options:
            input_widget = QComboBox()
            input_widget.addItems(options)
            input_widget.setCurrentText(str(value))
            # 使用 activated 确保只有用户点击选择时才触发
            input_widget.activated[str].connect(callback)
            input_widget.setFixedWidth(350)
            input_layout.addWidget(input_widget)
        else:
            input_widget = QLineEdit(str(value))
            if is_path:
                input_widget.setFixedWidth(280)
                btn = QPushButton("浏览")
                # 浏览点击后，先不改文字，直接把新路径传给回调处理弹窗
                btn.clicked.connect(lambda: self._handle_browse(input_widget, callback))
                input_layout.addWidget(input_widget)
                input_layout.addWidget(btn)
            else:
                input_widget.setFixedWidth(350)
                input_layout.addWidget(input_widget)

            # 手动输入路径后回车或失去焦点触发
            input_widget.editingFinished.connect(lambda: callback(input_widget.text()))

        self.inputs[key] = input_widget
        item_layout.addWidget(input_container)
        return item_widget

    def _handle_browse(self, line_edit, callback):
        path = QFileDialog.getExistingDirectory(self, "选择目录", line_edit.text())
        if path:
            callback(os.path.normpath(path))