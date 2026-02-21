import os

import numpy as np
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame, QListWidget, QFileDialog, QListWidgetItem
from PyQt5.QtCore import Qt, QSize

from database import db_manager
from index_manager import index_manager
from model_manager import model_image
from util.FeatureUtils import process_feature_vector


class SearchPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("图像检索")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # 1. 改进上传卡片
        self.upload_card = QFrame()
        self.upload_card.setObjectName("CardFrame")
        self.upload_card.setFixedHeight(250)  # 稍微调高一点

        card_layout = QVBoxLayout(self.upload_card)

        # 增加一个 QLabel 用于显示预览图
        self.image_display = QLabel("尚未选择图片")
        self.image_display.setAlignment(Qt.AlignCenter)
        self.image_display.setStyleSheet("color: #8e8e93; border: none;")
        card_layout.addWidget(self.image_display)

        self.btn_upload = QPushButton("选择图片")
        self.btn_upload.setObjectName("PrimaryBtn")
        self.btn_upload.setFixedWidth(120)
        card_layout.addWidget(self.btn_upload, 0, Qt.AlignCenter)

        layout.addWidget(self.upload_card)
        layout.addWidget(QLabel("检索结果"))

        # 2. 改进结果列表
        self.result_list = QListWidget()
        self.result_list.setFrameShape(QFrame.NoFrame)
        self.result_list.setViewMode(QListWidget.IconMode)  # 图标模式
        self.result_list.setIconSize(QSize(150, 150))  # 图片预览大小
        self.result_list.setResizeMode(QListWidget.Adjust)  # 自动适应窗口
        self.result_list.setSpacing(15)
        layout.addWidget(self.result_list)

        # 【关键步骤】连接信号与槽：点击按钮时弹出文件选择框
        self.btn_upload.clicked.connect(self.handle_upload)

    def handle_upload(self):
        # 弹出系统文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Image Files (*.jpg *.png *.jpeg *.bmp)"
        )

        if file_path:
            # 3. 预览逻辑
            pixmap = QPixmap(file_path)
            # 缩放预览图
            scaled_pixmap = pixmap.scaled(
                200, 150,  # 预览区域大小
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_display.setPixmap(scaled_pixmap)
            self.image_display.setText("")  # 有图了，清空文字提示

            # 4. 调用检索
            self.start_feature_extraction(file_path)

    def start_feature_extraction(self, path):
        print(f"🚀 开始搜索相似图片: {path}")

        # 1. 提取并处理特征向量
        # 注意：如果 extract_feature 已经包含了 process_feature_vector 的逻辑，可以合二为一
        raw_vector = model_image.extract_feature(path)

        # 2. 【关键修正】调用你写的处理函数进行归一化
        # 确保搜索向量与库内向量的“量纲”一致
        vector = process_feature_vector(raw_vector)

        print(f"向量类型: {type(vector)}")
        print(f"向量形状: {vector.shape}")  # 应该是 (768,) 或 (1, 768)
        print(f"数据类型: {vector.dtype}")  # 应该是 float32
        # 打印前 5 个数值，看看归一化后的量级
        print(f"向量前5位: {vector.flatten()[:5]}")
        # 打印向量的模长（判断是否做了 L2 归一化，归一化后应接近 1.0）
        print(f"向量 L2 范数 (模长): {np.linalg.norm(vector):.4f}")

        # 2. 调用单例 index_manager 进行向量检索 (返回前 10 个)
        distances, ids = index_manager.search(vector, k=10)

        # 3. 清空旧结果
        self.result_list.clear()

        # 4. 遍历搜索结果并展示
        for dist, img_id in zip(distances, ids):
            if img_id == -1: continue

            # 从数据库取路径
            img_path = db_manager.get_path_by_id(img_id)

            # --- 调试打印 ---
            print(f"ID {img_id} 对应的数据库路径: {img_path}")

            # 统一路径格式
            if img_path:
                img_path = os.path.abspath(img_path).replace('/', os.sep).replace('\\', os.sep)

                if os.path.exists(img_path):
                    score = 1 / (1 + dist)
                    item_text = f"相似度: {score:.2%}\n{os.path.basename(img_path)}"
                    item = QListWidgetItem(QIcon(img_path), item_text)
                    self.result_list.addItem(item)
                else:
                    print(f"❌ 文件不存在: {img_path}")

        if self.result_list.count() == 0:
            print("😿 未找到匹配的相似图片")