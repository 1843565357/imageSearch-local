import os
import shutil
import uuid
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QFileDialog, QLabel, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

# 导入配置与单例
from config import STORAGE_DIR
from database import db_manager
from index_manager import index_manager
from model_manager import model_image


# --- 异步入库线程 ---
class AddDataWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, paths, db):
        super().__init__()
        self.paths = paths
        self.db = db

    def run(self):
        for i, old_path in enumerate(self.paths):
            try:
                # 1. 物理拷贝文件
                file_ext = os.path.splitext(old_path)[1].lower()
                new_filename = f"{uuid.uuid4()}{file_ext}"
                new_path = os.path.join(STORAGE_DIR, new_filename)
                shutil.copy2(old_path, new_path)

                # 2. 提取特征并入库
                vector = model_image.extract_feature(new_path)
                if vector is not None:
                    # 初始描述设为空字符串
                    new_db_id = self.db.add_image(new_path, vector, description="")
                    # 3. 同步更新索引
                    if new_db_id:
                        index_manager.add_single(new_db_id, vector)

                self.progress.emit(i + 1)
            except Exception as e:
                logging.error(f"处理图片失败: {e}")
                continue
        self.finished.emit()


# --- 主管理页面 ---
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

        # 顶部工具栏
        tool_bar = QHBoxLayout()
        tool_bar.setSpacing(15)

        btn_add = QPushButton("新增图片入库")
        btn_add.setObjectName("PrimaryBtn")
        btn_add.clicked.connect(self.add_data)

        btn_batch_del = QPushButton("批量删除选中")
        btn_batch_del.setObjectName("PrimaryBtn")
        btn_batch_del.clicked.connect(self.batch_delete_data)

        btn_refresh = QPushButton("刷新列表")
        btn_refresh.setObjectName("PrimaryBtn")
        btn_refresh.clicked.connect(self.refresh_table)

        tool_bar.addWidget(btn_add)
        tool_bar.addWidget(btn_batch_del)
        tool_bar.addWidget(btn_refresh)
        tool_bar.addStretch()
        layout.addLayout(tool_bar)

        # --- 表格配置 (5列) ---
        # 0:选择 | 1:预览 | 2:描述 | 3:路径 | 4:时间
        self.table = QTableWidget(0, 5)
        self.table.setObjectName("CardFrame")
        self.table.setHorizontalHeaderLabels(["选择", "预览", "描述 (双击修改)", "图片路径", "入库时间"])

        # 列宽与对齐设置
        self.table.setColumnWidth(0, 60)  # 选择列稍微加宽一点以保证居中视觉
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 250)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(80)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        # 信号绑定
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.itemChanged.connect(self.on_item_changed)

        layout.addWidget(self.table)

    def refresh_table(self):
        """刷新表格数据"""
        self.table.blockSignals(True)  # 防止填充数据时触发 itemChanged 信号
        self.table.setRowCount(0)

        # 获取包含描述的所有记录
        rows = self.db.get_all_images()
        for row_data in rows:
            db_id, img_path, description, created_at = row_data
            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)

            # 1. 居中的多选框容器
            check_widget = QWidget()
            check_layout = QHBoxLayout(check_widget)
            checkbox = QCheckBox()
            checkbox.setCheckState(Qt.Unchecked)
            # 使用紫色主题样式
            checkbox.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
            check_layout.addWidget(checkbox)
            check_layout.setAlignment(Qt.AlignCenter)  # 强制居中
            check_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row_pos, 0, check_widget)

            # 在第一列底层 Item 存储 ID，方便 batch_delete 获取
            id_item = QTableWidgetItem()
            id_item.setData(Qt.UserRole, db_id)
            id_item.setFlags(Qt.ItemIsEnabled)  # 禁止编辑文本
            self.table.setItem(row_pos, 0, id_item)

            # 2. 预览图
            preview_label = QLabel()
            preview_label.setAlignment(Qt.AlignCenter)
            if os.path.exists(img_path):
                pix = QPixmap(img_path).scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                preview_label.setPixmap(pix)
            self.table.setCellWidget(row_pos, 1, preview_label)

            # 3. 描述列 (可编辑)
            desc_item = QTableWidgetItem(description if description else "")
            desc_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            self.table.setItem(row_pos, 2, desc_item)

            # 4. 路径与时间 (不可编辑)
            path_item = QTableWidgetItem(img_path)
            path_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_pos, 3, path_item)

            time_item = QTableWidgetItem(str(created_at))
            time_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row_pos, 4, time_item)

        self.table.blockSignals(False)

    def on_cell_clicked(self, row, column):
        """点击处理：第一列切换勾选，第三列进入编辑"""
        if column == 0:
            # 获取第一列的 QCheckBox 容器
            widget = self.table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                checkbox.setChecked(not checkbox.isChecked())
        elif column == 2:
            # 描述列交由 QTableWidget 默认的双击编辑逻辑处理
            pass

    def on_item_changed(self, item):
        """描述编辑完成后，自动保存到数据库"""
        if item.column() == 2:
            row = item.row()
            # 从第一列的 UserRole 获取数据库 ID
            db_id = self.table.item(row, 0).data(Qt.UserRole)
            new_desc = item.text().strip()
            self.db.update_description(db_id, new_desc)  #
            logging.info(f"已更新记录 {db_id} 的描述")

    def add_data(self):
        """选择图片并开启异步入库"""
        paths, _ = QFileDialog.getOpenFileNames(self, "选择图片入库", "", "Images (*.png *.jpg *.jpeg)")
        if paths:
            self.table.setEnabled(False)
            self.worker = AddDataWorker(paths, self.db)
            self.worker.finished.connect(self.on_add_finished)
            self.worker.start()

    def on_add_finished(self):
        self.table.setEnabled(True)
        self.refresh_table()
        QMessageBox.information(self, "完成", "图片特征提取并入库成功！")

    def batch_delete_data(self):
        """批量删除逻辑"""
        selected_ids = []
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    db_id = self.table.item(row, 0).data(Qt.UserRole)
                    selected_ids.append(db_id)

        if not selected_ids:
            QMessageBox.warning(self, "警告", "请先勾选要删除的记录")
            return

        confirm = QMessageBox.question(self, '确认删除', f'确定要永久删除选中的 {len(selected_ids)} 项记录吗？')
        if confirm == QMessageBox.Yes:
            for db_id in selected_ids:
                # 1. 数据库删除并清理物理文件
                path = self.db.delete_image(db_id)
                # 2. 从索引中移除
                index_manager.remove_single(db_id)
                # 3. 物理删除
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

            self.refresh_table()
            QMessageBox.information(self, "成功", "选中记录已成功移除")