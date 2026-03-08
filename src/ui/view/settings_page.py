import logging
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox,
                             QHBoxLayout, QFrame, QPushButton, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt

from src.config import config
from src.utils.feature_utils import process_feature_vector
from src.utils.file_utils import copy_directory_contents

logger = logging.getLogger(__name__)

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
            # 1. 物理迁移内容
            success, msg = copy_directory_contents(config.MODEL_DIR, new_path)

            if not success:
                QMessageBox.critical(self, "迁移失败", f"无法移动模型文件，操作已中止。\n{msg}")
                return

            try:
                # 2. 先尝试使用新路径加载模型
                from src.core.model_manager import model_image
                model_image.load_model(new_path, config.MODEL_NAME)

                # 3. 重建索引：如果需要根据新模型重新提取特征
                from src.core.index_manager import index_manager
                from src.core.database import db_manager
                index_manager.load_from_db(db_manager)

                # 4. 所有操作成功后再保存配置并刷新内存变量
                self.apply_change("model_dir", new_path)

                QMessageBox.information(self, "成功", "模型路径已更新，文件迁移完成，引擎已重载。")

            except Exception as e:
                QMessageBox.warning(self, "部分失败", f"配置已保存，但模型加载出错，请检查文件完整性：\n{e}")

    def on_model_name_changed(self, model_name):
        """处理模型规模切换：联动修改索引维度并重扫数据库"""
        if model_name == config.MODEL_NAME:
            return

        res = QMessageBox.warning(
            self, "确认切换引擎",
            f"确定要切换至 {model_name} 吗？\n\n"
            "⚠️ 注意：由于特征维度不兼容，系统将自动重置索引并重新扫描所有图片。这可能需要几分钟时间。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if res == QMessageBox.Yes:
            try:
                # 1. 局部导入管理器
                from src.core.model_manager import model_image
                from src.core.index_manager import index_manager
                from src.config.config import MODEL_DIMENSIONS

                # 2. 核心步骤：重新初始化 FAISS 索引维度
                # 根据新模型获取维度 (例如: 768 -> 1024)
                new_dim = MODEL_DIMENSIONS.get(model_name, 768)
                index_manager.reinit_index(new_dim)

                # 3. 加载新模型权重（使用传入的model_name，而不是config.MODEL_NAME）
                model_image.load_model(config.MODEL_DIR, model_name)

                # 4. 触发数据库重扫与提取
                # 此函数最后会调用 index_manager.load_from_db() 将新向量填入索引
                self.reindex_all_images(target_model_name=model_name)

                # 5. 所有操作成功后再保存配置并刷新内存变量
                self.apply_change("model_name", model_name)

                QMessageBox.information(self, "切换成功", f"模型已切换至 {model_name}，维度已调整为 {new_dim}。")

            except Exception as e:
                import logging
                logging.error(f"引擎切换失败: {e}")
                QMessageBox.critical(self, "错误", f"切换过程中出错：\n{str(e)}")
        else:
            # 用户取消，将下拉框复位
            self.inputs["model_name"].setCurrentText(config.MODEL_NAME)

    def on_storage_dir_changed(self, new_path):
        """处理图片存储目录变更"""
        # 0. 提前记录旧路径，作为数据库更新的参照
        old_path = config.STORAGE_DIR

        # 1. 检查是否有实际变动，避免误触
        if new_path == old_path:
            return

        # 2. 交互确认
        res = QMessageBox.question(
            self, "确认更改存储目录",
            f"确定将图片存储目录修改为：\n{new_path}\n\n系统将自动迁移物理文件并同步数据库路径记录。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if res == QMessageBox.Yes:
            try:
                # --- 步骤 1：物理移动文件 ---
                # 局部导入工具类，确保获取最新环境
                success, msg = copy_directory_contents(old_path, new_path)

                if not success:
                    QMessageBox.critical(self, "迁移失败", f"图片迁移过程中出错：\n{msg}")
                    return

                # --- 步骤 2：刷新数据库路径 ---
                # 核心逻辑：在内存变量正式修改前，利用 old_path 批量替换数据库中的路径前缀
                from src.core.database import db_manager
                updated_count = db_manager.refresh_storage_path(old_path, new_path)

                # --- 步骤 3：保存配置并刷新内存变量 ---
                # apply_change 内部执行 config.save_config 和 config.update_vars()
                # 此时 config.STORAGE_DIR 会正式变为 new_path
                self.apply_change("storage_dir", new_path)

                QMessageBox.information(
                    self, "成功",
                    f"图片存储目录已成功更新！\n\n"
                    f"• 文件迁移：已完成\n"
                    f"• 数据库同步：{updated_count} 条记录已更新"
                )

            except Exception as e:
                import logging
                logging.error(f"存储目录变更异常: {e}")
                QMessageBox.critical(self, "错误", f"操作未能完全执行，请检查日志：\n{str(e)}")

    def on_db_path_changed(self, new_path):
        """处理数据库及索引文件夹变更"""
        old_path = config.DB_FOLDER
        if new_path == old_path:
            return

        res = QMessageBox.question(
            self, "确认迁移数据库",
            f"确定将数据库文件夹修改为：\n{new_path}\n\n系统将尝试自动迁移数据库文件（.db）与向量索引（.index）。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if res == QMessageBox.Yes:
            try:
                # --- 步骤 1：物理移动文件 ---
                # 注意：搬运前请确保没有其他耗时写入操作
                success, msg = copy_directory_contents(old_path, new_path)

                if not success:
                    QMessageBox.critical(self, "迁移失败", f"文件迁移过程中出错：\n{msg}")
                    return

                # --- 步骤 2：刷新数据库单例与索引加载 ---
                # 先尝试使用新路径重新初始化数据库和索引
                from src.core.database import db_manager
                from src.core.index_manager import index_manager

                # 重新初始化数据库连接，使其指向新路径下的文件
                db_manager.__init__(db_folder=new_path)

                # 告诉索引管理器，从新路径加载 FAISS 索引文件
                index_manager.load_from_db(db_manager)

                # --- 步骤 3：所有操作成功后再保存配置并刷新内存变量 ---
                self.apply_change("db_folder", new_path)

                QMessageBox.information(
                    self, "成功",
                    "数据库文件夹已成功迁移！\n新的数据库链接已建立，索引已重新加载。"
                )

            except Exception as e:
                import logging
                logging.error(f"数据库目录变更异常: {e}")
                QMessageBox.critical(self, "错误", f"数据库重载失败，请重启软件：\n{str(e)}")

    def reindex_all_images(self, target_model_name=None):
        """核心逻辑：清空旧向量、提取新特征、批量入库、重载索引
        :param target_model_name: 目标模型名称，用于显示进度信息（可选）
        """
        from src.core.database import db_manager
        from src.core.model_manager import model_image
        from src.core.index_manager import index_manager
        from src.utils.feature_utils import process_feature_vector
        from PyQt5.QtWidgets import QProgressDialog
        from PyQt5.QtCore import Qt

        # 1. 获取所有待处理的图片记录
        images = db_manager.get_all_images()
        if not images:
            logger.info("数据库为空，无需重扫。")
            return

        # 2. 【核心防火墙】开始重扫前，先物理清空数据库所有旧向量
        # 确保 index_manager.load_from_db 不会读到任何维度冲突的脏数据
        db_manager.clear_all_vectors()

        # 3. 初始化进度条弹窗
        total = len(images)
        model_display_name = target_model_name or config.MODEL_NAME
        progress = QProgressDialog(f"正在切换至 {model_display_name} 并重扫特征...", "取消", 0, total, self)
        progress.setWindowModality(Qt.WindowModal)  # 阻塞交互，防止重扫时乱点
        progress.setWindowTitle("模型引擎转换中")
        progress.setMinimumDuration(0)
        progress.resize(400, 100)

        # 4. 准备批量更新缓冲区
        update_buffer = []

        logger.info(f"开始重扫数据库：共 {total} 张图片，目标维度: {index_manager.dimension}")

        for i, (img_id, img_path, description, created_at) in enumerate(images):
            # 检查用户是否点击了“取消”
            if progress.wasCanceled():
                QMessageBox.warning(self, "操作中止", "模型转换未完成，部分向量可能缺失。")
                break

            try:
                # A. 提取新特征 (当前模型已在 load_model 阶段切换完成)
                raw_feat = model_image.extract_feature(img_path)

                # B. 后期处理 (归一化、转float32等)
                processed_feat = process_feature_vector(raw_feat)

                # C. 存入缓冲区 (存二进制 blob 和对应的 ID)
                update_buffer.append((processed_feat.tobytes(), img_id))

            except Exception as e:
                logger.error(f"处理图片失败 [ID:{img_id}]: {img_path}, 错误: {e}")

            # 更新进度条文字和数值
            progress.setLabelText(f"处理中 ({i + 1}/{total})\n当前文件: {os.path.basename(img_path)}")
            progress.setValue(i + 1)

        # 5. 【关键步】等待循环彻底结束，一次性 Commit 到数据库
        if update_buffer:
            try:
                # 批量更新：这是为了确保 load_from_db 时，所有数据都已落盘
                db_manager.update_vectors_batch(update_buffer)
                logger.info(f"💾 数据库落盘成功，共更新 {len(update_buffer)} 条记录。")
            except Exception as e:
                QMessageBox.critical(self, "数据库同步失败", f"无法写入新向量数据：{str(e)}")
                return

        # 6. 【最后一步】重载 FAISS 内存索引
        # 此时数据库中只有新维度的向量（或 NULL），load_from_db 会非常顺畅
        index_manager.load_from_db(db_manager)

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
        logger.info(f"配置已更新: {key} -> {value}")

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