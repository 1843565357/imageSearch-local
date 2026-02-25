import os
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFrame, QFileDialog, QScrollArea, QGridLayout, QLineEdit)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath

# 导入你的核心逻辑
from database import db_manager
from index_manager import index_manager
from model_manager import model_image
from util.feature_utils import process_feature_vector


# --- 自定义结果卡片组件 ---
class ResultCard(QFrame):
    def __init__(self, image_path, score, description=None, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setObjectName("ResultCardFrame")
        # 增加高度以容纳描述标签
        self.setFixedSize(170, 290)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)

        # 1. 图片展示区
        self.image_label = QLabel()
        self.image_label.setFixedHeight(150)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.set_rounded_image(image_path)

        # 2. 描述标签 (胶囊样式)
        desc_text = description if description and description.strip() else "无描述"
        self.desc_tag = QLabel(desc_text)
        self.desc_tag.setAlignment(Qt.AlignCenter)
        # 这里的样式模仿了 image_1349de.png 的蓝色药丸风格
        self.desc_tag.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: #3498DB;
                border: 1.5px solid #3498DB;
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 10px;
                font-weight: bold;
            }
        """)

        # 3. 绝对路径展示框
        self.path_edit = QLineEdit(self.image_path)
        self.path_edit.setReadOnly(True)
        self.path_edit.setAlignment(Qt.AlignCenter)
        self.path_edit.setToolTip(self.image_path)
        self.path_edit.setStyleSheet("border: none; background: transparent; color: #34495E; font-size: 11px;")

        # 4. 相似度
        self.score_label = QLabel(f"匹配度: {score:.2%}")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setStyleSheet("""
                    color: #9B59B6;       
                    font-size: 11px;
                    font-weight: bold;   
                """)

        layout.addWidget(self.image_label)
        layout.addWidget(self.desc_tag, alignment=Qt.AlignCenter) # 标签居中
        layout.addWidget(self.path_edit)
        layout.addWidget(self.score_label)
        layout.addStretch()

    # set_rounded_image 方法保持不变
    def set_rounded_image(self, image_path):
        if not os.path.exists(image_path):
            self.image_label.setText("图片丢失")
            return
        pix = QPixmap(image_path)
        # 对应高度调整为 160
        target_size = QSize(160, 160)
        scaled = pix.scaled(target_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

        final = QPixmap(target_size)
        final.fill(Qt.transparent)
        painter = QPainter(final)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, 160, 160, 8, 8)
        painter.setClipPath(path)
        painter.drawPixmap((160 - scaled.width()) // 2, (160 - scaled.height()) // 2, scaled)
        painter.end()
        self.image_label.setPixmap(final)


# --- 主搜索页面 ---
class SearchPage(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        # 调整顶部边距为 5，让标题上移
        main_layout.setContentsMargins(30, 5, 30, 30)
        main_layout.setSpacing(25)
        # 设置顶部对齐
        main_layout.setAlignment(Qt.AlignTop)

        # 1. 标题
        title = QLabel("图像检索控制台")
        title.setObjectName("PageTitle")
        # 标题上方的额外间距，可根据需要调整
        main_layout.addSpacing(20)
        main_layout.addWidget(title)

        # 2. 上传/预览区域
        self.top_box = QWidget()
        top_layout = QVBoxLayout(self.top_box)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 初始上传按钮 (大框)
        self.upload_btn = QPushButton("\n\n☁️\n\n点击上传图片进行 DINOv2 检索")
        self.upload_btn.setObjectName("UploadAreaBtn")
        self.upload_btn.setFixedHeight(350)  # 调大框体
        self.upload_btn.clicked.connect(self.handle_upload)

        # 选中图片后的预览容器
        self.preview_box = QWidget()
        self.preview_box.setVisible(False)
        preview_layout = QHBoxLayout(self.preview_box)

        # 左侧预览图
        self.preview_img = QLabel()
        self.preview_img.setObjectName("PreviewImageLabel")
        self.preview_img.setFixedSize(160, 160)

        # 右侧信息布局
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(20, 0, 0, 0)  # 与图片保持一定间距
        info_layout.setSpacing(15)  # 标签与按钮之间的垂直间距

        # --- 布局核心改动 ---
        # 顶部弹簧：把标签往下压
        info_layout.addStretch()

        self.name_label = QLabel("文件名")
        self.name_label.setAlignment(Qt.AlignCenter)  # 文字水平居中
        self.name_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2C3E50;")
        info_layout.addWidget(self.name_label)

        # 3. 更换图片按钮
        self.re_btn = QPushButton("更换图片")
        self.re_btn.setObjectName("PrimaryBtn")  # 关联紫色 QSS 样式
        self.re_btn.setFixedSize(140, 40)  # 设定固定大小使其更精致
        self.re_btn.setCursor(Qt.PointingHandCursor)

        self.re_btn.clicked.connect(self.handle_upload)
        # 将按钮在布局中水平居中对齐
        info_layout.addWidget(self.re_btn, alignment=Qt.AlignCenter)

        # 4. 底部弹簧
        info_layout.addStretch()

        preview_layout.addWidget(self.preview_img)
        preview_layout.addLayout(info_layout)

        top_layout.addWidget(self.upload_btn)
        top_layout.addWidget(self.preview_box)
        main_layout.addWidget(self.top_box)

        # 3. 结果展示区 (网格布局)
        self.res_title = QLabel("检索结果")
        self.res_title.setVisible(False)
        self.res_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(self.res_title)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ResultScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setVisible(False)

        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("ResultGridWidget")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.scroll.setWidget(self.grid_widget)
        main_layout.addWidget(self.scroll)

    def handle_upload(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.jpg *.png *.jpeg)")
        if path:
            self.upload_btn.setVisible(False)
            self.preview_box.setVisible(True)
            self.name_label.setText(os.path.basename(path))
            self.preview_img.setPixmap(QPixmap(path).scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.start_feature_extraction(path)

    def start_feature_extraction(self, path):
        raw_vec = model_image.extract_feature(path)
        vector = process_feature_vector(raw_vec)
        distances, ids = index_manager.search(vector, k=12)

        self.clear_grid()
        self.res_title.setVisible(True)
        self.scroll.setVisible(True)

        cols = 4
        found = False
        for i, (dist, img_id) in enumerate(zip(distances, ids)):
            if img_id == -1: continue
            img_path = db_manager.get_path_by_id(img_id)
            if img_path and os.path.exists(img_path):
                found = True
                card = ResultCard(img_path, 1 / (1 + dist))
                self.grid_layout.addWidget(card, i // cols, i % cols)

        if found:
            self.grid_layout.setColumnStretch(cols, 1)
            self.grid_layout.setRowStretch((len(ids) // cols) + 1, 1)

    def clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for i in range(self.grid_layout.columnCount()): self.grid_layout.setColumnStretch(i, 0)
        for i in range(self.grid_layout.rowCount()): self.grid_layout.setRowStretch(i, 0)