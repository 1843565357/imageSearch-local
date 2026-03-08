import os
import shutil
import uuid
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QFileDialog, QLabel, QCheckBox,
                             QComboBox, QLineEdit, QProgressDialog, QInputDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

# 导入配置与单例
from src.config.config import STORAGE_DIR
from src.core.database import db_manager
from src.core.index_manager import index_manager
from src.core.model_manager import model_image


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
        self.current_page = 1
        self.page_size = 20
        self.total_count = 0
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

        btn_batch_desc = QPushButton("批量添加描述")
        btn_batch_desc.setObjectName("PrimaryBtn")
        btn_batch_desc.clicked.connect(self.batch_add_description)

        btn_refresh = QPushButton("刷新列表")
        btn_refresh.setObjectName("PrimaryBtn")
        btn_refresh.clicked.connect(self.refresh_table)

        tool_bar.addWidget(btn_add)
        tool_bar.addWidget(btn_batch_del)
        tool_bar.addWidget(btn_batch_desc)
        tool_bar.addWidget(btn_refresh)
        tool_bar.addStretch()
        layout.addLayout(tool_bar)

        # --- 统计信息显示 ---
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        self.stats_label = QLabel("统计信息加载中...")
        self.stats_label.setObjectName("StatsLabel")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

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

        # --- 分页控件 ---
        pagination_layout = QHBoxLayout()
        pagination_layout.setSpacing(10)

        # 上一页按钮
        self.btn_prev = QPushButton("上一页")
        self.btn_prev.setObjectName("PrimaryBtn")
        self.btn_prev.clicked.connect(self.go_prev_page)
        self.btn_prev.setEnabled(False)

        # 下一页按钮
        self.btn_next = QPushButton("下一页")
        self.btn_next.setObjectName("PrimaryBtn")
        self.btn_next.clicked.connect(self.go_next_page)
        self.btn_next.setEnabled(False)

        # 页码显示
        self.page_label = QLabel("第 1 页 / 共 1 页")
        self.page_label.setStyleSheet("color: #34495E; font-size: 14px;")

        # 跳转到页码
        self.goto_label = QLabel("跳转到:")
        self.goto_input = QLineEdit()
        self.goto_input.setFixedWidth(60)
        self.goto_input.setPlaceholderText("页码")
        self.goto_input.returnPressed.connect(self.go_to_page_input)

        # 每页显示数量选择
        self.page_size_label = QLabel("每页显示:")
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["10", "20", "50", "100"])
        self.page_size_combo.setCurrentText(str(self.page_size))
        self.page_size_combo.currentTextChanged.connect(self.change_page_size)

        # 总记录数显示
        self.total_label = QLabel("总记录: 0")
        self.total_label.setStyleSheet("color: #7F8C8D; font-size: 14px;")

        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addWidget(self.page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.goto_label)
        pagination_layout.addWidget(self.goto_input)
        pagination_layout.addWidget(self.page_size_label)
        pagination_layout.addWidget(self.page_size_combo)
        pagination_layout.addWidget(self.total_label)

        layout.addLayout(pagination_layout)

    def refresh_table(self):
        """刷新表格数据（分页版本）"""
        self.table.blockSignals(True)  # 防止填充数据时触发 itemChanged 信号
        self.table.setRowCount(0)

        # 获取总记录数和统计信息
        self.total_count = self.db.get_total_count()
        stats = self.db.get_statistics()

        # 更新统计信息显示
        self.update_statistics(stats)

        # 计算总页数
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        # 确保当前页在有效范围内
        if self.current_page > total_pages:
            self.current_page = total_pages
        if self.current_page < 1 and total_pages > 0:
            self.current_page = 1

        # 计算分页参数
        offset = (self.current_page - 1) * self.page_size
        limit = self.page_size

        # 获取当前页数据
        rows = self.db.get_images_page(offset, limit)
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
        # 更新分页控件状态
        self.update_pagination()

    def update_statistics(self, stats):
        """更新统计信息显示"""
        total = stats["total"]
        with_desc = stats["with_description"]
        with_vector = stats["with_vector"]
        desc_rate = stats["description_rate"]
        vector_rate = stats["vector_rate"]

        stats_text = f"📊 总记录: {total} | 📝 有描述: {with_desc} ({desc_rate:.1%}) | 🔢 有向量: {with_vector} ({vector_rate:.1%})"
        if total > 0:
            latest = stats["latest_time"]
            earliest = stats["earliest_time"]
            stats_text += f" | 📅 时间范围: {earliest} 至 {latest}"

        self.stats_label.setText(stats_text)

    def update_pagination(self):
        """更新分页控件状态"""
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)

        # 更新页码显示
        self.page_label.setText(f"第 {self.current_page} 页 / 共 {total_pages} 页")

        # 更新总记录数显示
        self.total_label.setText(f"总记录: {self.total_count}")

        # 更新按钮状态
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)

        # 清空跳转输入框
        self.goto_input.clear()

    def go_prev_page(self):
        """转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_table()

    def go_next_page(self):
        """转到下一页"""
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page += 1
            self.refresh_table()

    def go_to_page_input(self):
        """跳转到输入框指定的页码"""
        try:
            page_num = int(self.goto_input.text().strip())
            if page_num < 1:
                return
            total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
            if page_num > total_pages:
                page_num = total_pages
            self.current_page = page_num
            self.refresh_table()
        except ValueError:
            self.goto_input.clear()

    def change_page_size(self, new_size):
        """更改每页显示数量"""
        try:
            new_size = int(new_size)
            if new_size != self.page_size:
                self.page_size = new_size
                self.current_page = 1  # 重置到第一页
                self.refresh_table()
        except ValueError:
            pass

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

            # 创建进度对话框
            self.progress_dialog = QProgressDialog("正在处理图片入库...", "取消", 0, len(paths), self)
            self.progress_dialog.setWindowTitle("图片入库进度")
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setMinimumDuration(0)  # 立即显示
            self.progress_dialog.setValue(0)

            # 创建工作线程
            self.worker = AddDataWorker(paths, self.db)
            self.worker.finished.connect(self.on_add_finished)
            self.worker.progress.connect(self.update_progress)

            # 连接取消按钮
            self.progress_dialog.canceled.connect(self.worker.terminate)

            self.worker.start()

    def update_progress(self, value):
        """更新进度对话框"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.setValue(value)

    def on_add_finished(self):
        # 关闭进度对话框
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            del self.progress_dialog

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

    def batch_add_description(self):
        """批量添加描述"""
        selected_ids = []
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    db_id = self.table.item(row, 0).data(Qt.UserRole)
                    selected_ids.append(db_id)

        if not selected_ids:
            QMessageBox.warning(self, "警告", "请先勾选要添加描述的记录")
            return

        # 弹出输入对话框获取描述文本
        description, ok = QInputDialog.getText(self, "批量添加描述",
                                               f"将为 {len(selected_ids)} 个选中项添加描述：",
                                               QLineEdit.Normal, "")
        if not ok or not description.strip():
            return

        # 构建 ID 到行号的映射
        id_to_row = {}
        for row in range(self.table.rowCount()):
            db_id = self.table.item(row, 0).data(Qt.UserRole)
            id_to_row[db_id] = row

        # 批量更新数据库和表格项
        for db_id in selected_ids:
            self.db.update_description(db_id, description.strip())
            # 更新表格项（如果当前页显示）
            if db_id in id_to_row:
                desc_item = self.table.item(id_to_row[db_id], 2)
                if desc_item:
                    desc_item.setText(description.strip())

        self.refresh_table()  # 刷新表格以更新统计信息
        QMessageBox.information(self, "成功", f"已为 {len(selected_ids)} 个选中项添加描述")