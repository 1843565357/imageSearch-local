import logging
import os
import shutil
import uuid

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QFileDialog, QLabel, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

from config import DB_NAME, DB_FOLDER, STORAGE_DIR
from database import DatabaseManager, db_manager
import time

from index_manager import index_manager
from model_manager import model_image
from util.feature_utils import process_feature_vector

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
                # 1. 准备新路径并拷贝文件
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
        self.db = db_manager
        self.init_ui()
        self.refresh_table()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title = QLabel("数据库管理")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # 操作栏
        tool_bar = QHBoxLayout()
        tool_bar.setSpacing(15)

        btn_add = QPushButton("新增图片入库")
        btn_add.setObjectName("PrimaryBtn")

        btn_batch_del = QPushButton("批量删除选中")
        btn_batch_del.setObjectName("PrimaryBtn")

        # 刷新列表按钮应用新样式
        btn_refresh = QPushButton("刷新列表")
        btn_refresh.setObjectName("PrimaryBtn")

        btn_add.clicked.connect(self.add_data)
        btn_batch_del.clicked.connect(self.batch_delete_data)
        btn_refresh.clicked.connect(self.refresh_table)

        tool_bar.addWidget(btn_add)
        tool_bar.addWidget(btn_batch_del)
        tool_bar.addWidget(btn_refresh)
        tool_bar.addStretch()
        layout.addLayout(tool_bar)

        # 表格配置：选择 | 预览 | 图片路径 | 入库时间
        self.table = QTableWidget(0, 4)
        self.table.setObjectName("CardFrame")
        self.table.setHorizontalHeaderLabels(["选择", "预览", "图片路径", "入库时间"])

        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 80)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        self.table.verticalHeader().setDefaultSectionSize(80)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        # 【关键改动】绑定单元格点击信号，实现整行触发复选框
        self.table.cellClicked.connect(self.on_cell_clicked)

        layout.addWidget(self.table)

    def refresh_table(self):
        self.table.setRowCount(0)
        rows = self.db.get_all_images()
        for row_data in rows:
            db_id, img_path, created_at = row_data
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)

            # 复选框列
            check_item = QTableWidgetItem()
            check_item.setCheckState(Qt.Unchecked)
            check_item.setData(Qt.UserRole, db_id)
            self.table.setItem(row_pos, 0, check_item)

            # 预览图列
            preview_label = QLabel()
            preview_label.setAlignment(Qt.AlignCenter)
            if os.path.exists(img_path):
                pix = QPixmap(img_path).scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                preview_label.setPixmap(pix)
            self.table.setCellWidget(row_pos, 1, preview_label)

            self.table.setItem(row_pos, 2, QTableWidgetItem(img_path))
            self.table.setItem(row_pos, 3, QTableWidgetItem(str(created_at)))

    def add_data(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "选择入库图片", "", "Images (*.png *.jpg *.jpeg)")
        if paths:
            # 启动异步线程处理，防止界面卡住
            self.worker = AddDataWorker(paths, self.db)
            self.worker.finished.connect(self.on_add_finished)
            self.worker.start()
            # 简单反馈
            self.table.setEnabled(False)

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
                        print(f" 已清理物理文件: {image_path}")
                    except Exception as e:
                        print(f" 物理文件删除失败: {e}")

                # 4. 刷新 UI
                self.refresh_table()
                QMessageBox.information(self, "成功", f"ID {db_id} 已完全移除")
        else:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")

    def on_cell_clicked(self, row, column):
        """点击单元格任意位置，切换第一列复选框状态"""
        check_item = self.table.item(row, 0)
        if check_item:
            # 切换勾选状态
            new_state = Qt.Unchecked if check_item.checkState() == Qt.Checked else Qt.Checked
            check_item.setCheckState(new_state)

    def batch_delete_data(self):
        selected_ids = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item.checkState() == Qt.Checked:
                selected_ids.append(item.data(Qt.UserRole))

        if not selected_ids:
            QMessageBox.warning(self, "警告", "请先勾选要删除的图片")
            return

        if QMessageBox.question(self, '确认', f'确定删除选中的 {len(selected_ids)} 项记录吗？') == QMessageBox.Yes:
            for db_id in selected_ids:
                path = self.db.delete_image(db_id)
                index_manager.remove_single(db_id)
                if path and os.path.exists(path):
                    try: os.remove(path)
                    except: pass
            self.refresh_table()