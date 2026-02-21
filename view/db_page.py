import os
import shutil
import uuid

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QFileDialog, QLabel, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from config import DB_NAME, DB_FOLDER, STORAGE_DIR
from database import DatabaseManager
import time

from index_manager import index_manager
from model_manager import model_image
from util.FeatureUtils import process_feature_vector


# 模拟 DINOv2 提取特征的口子
def extract_dinov2_features(image_path):
    vector = model_image.extract_feature(image_path)
    data_vector = process_feature_vector(vector)
    return data_vector

# 异步入库线程
class AddDataWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, paths, db):
        super().__init__()
        self.paths = paths  # 这里的 paths 是用户选中的原始路径列表
        self.db = db

    def run(self):
        for i, old_path in enumerate(self.paths):
            try:
                # 1. 准备新路径并拷贝文件 (同你之前的逻辑)
                file_ext = os.path.splitext(old_path)[1].lower()
                new_filename = f"{uuid.uuid4()}{file_ext}"
                new_path = os.path.join(STORAGE_DIR, new_filename)
                shutil.copy2(old_path, new_path)

                # 2. 使用单例提取特征
                # 注意：确保这里调用的是 model_image.extract_feature
                vector = model_image.extract_feature(new_path)

                if vector is not None:
                    # 3. 存入数据库并获取该记录的自增 ID
                    # 必须拿到 ID，因为 FAISS 需要这个 ID 来对应数据库记录
                    new_db_id = self.db.add_image(new_path, vector)

                    # 4. 【新增】同步更新 FAISS 索引
                    # 假设你在初始化 Worker 时把 index_manager 传进来了
                    if new_db_id:
                        print("更新index索引")
                        index_manager.add_single(new_db_id, vector)

                # 5. 更新进度
                self.progress.emit(i + 1)

            except Exception as e:
                print(f"处理第 {i + 1} 张图片出错: {e}")
                continue

        self.finished.emit()


class DBManagementPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager(db_folder=DB_FOLDER, db_name=DB_NAME)  # 初始化数据库类
        self.init_ui()
        self.refresh_table()  # 启动时加载数据

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("数据库管理")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # 操作栏
        tool_bar = QHBoxLayout()
        btn_add = QPushButton("新增图片入库")
        btn_add.setObjectName("PrimaryBtn")
        btn_del = QPushButton("删除选中")
        btn_refresh = QPushButton("刷新列表")

        btn_add.clicked.connect(self.add_data)
        btn_del.clicked.connect(self.delete_data)
        btn_refresh.clicked.connect(self.refresh_table)

        tool_bar.addWidget(btn_add)
        tool_bar.addWidget(btn_del)
        tool_bar.addWidget(btn_refresh)
        tool_bar.addStretch()
        layout.addLayout(tool_bar)

        # 数据表格美化
        self.table = QTableWidget(0, 3)
        self.table.setObjectName("CardFrame")  # 套用之前的卡片样式
        self.table.setHorizontalHeaderLabels(["ID", "图片路径", "入库时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不允许直接双击修改
        layout.addWidget(self.table)

    def refresh_table(self):
        """从 SQLite 加载数据并刷新 UI"""
        self.table.setRowCount(0)
        rows = self.db.get_all_images()
        for row_data in rows:
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)
            # row_data 结构: (id, path, created_at)
            for col, value in enumerate(row_data):
                self.table.setItem(row_pos, col, QTableWidgetItem(str(value)))

    def add_data(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择入库图片", "", "Images (*.png *.jpg *.jpeg)")
        if paths:
            # 启动异步线程处理，防止界面卡住
            self.worker = AddDataWorker(paths, self.db)
            self.worker.finished.connect(self.on_add_finished)
            self.worker.start()
            # 简单反馈
            self.table.setEnabled(False)
            print(f"开始入库 {len(paths)} 张图片...")

    def on_add_finished(self):
        self.table.setEnabled(True)
        self.refresh_table()
        QMessageBox.information(self, "完成", "图片特征提取并入库成功！")

    def delete_data(self):
        row = self.table.currentRow()
        if row >= 0:
            db_id = int(self.table.item(row, 0).text())
            reply = QMessageBox.question(self, '确认', f'确定要删除 ID 为 {db_id} 的记录吗？',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                # 1. 从数据库删除并获取物理路径 (用于清理硬盘)
                # 建议修改 database.py 让 delete_image 返回路径
                image_path = self.db.delete_image(db_id)

                # 2. 从 FAISS 索引中移除 (核心步骤)
                # 这里的 index_manager 是你的单例对象
                from index_manager import index_manager
                index_manager.remove_single(db_id)

                # 3. 物理删除磁盘文件 (可选，但推荐)
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                        print(f"📁 已清理物理文件: {image_path}")
                    except Exception as e:
                        print(f"❌ 物理文件删除失败: {e}")

                # 4. 刷新 UI
                self.refresh_table()
                QMessageBox.information(self, "成功", f"ID {db_id} 已完全移除")
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")