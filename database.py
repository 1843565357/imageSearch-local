import logging
import sqlite3
import numpy as np
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_folder="database", db_name="image.db"):
        self.db_path = os.path.join(db_folder, db_name)
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """初始化数据库表：直接在建表时加入 description 字段"""
        with self.get_connection() as conn:
            conn.execute('''
                    CREATE TABLE IF NOT EXISTS images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        image_path TEXT NOT NULL,
                        vector_data BLOB,
                        description TEXT,  -- 【新增】文本描述字段
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            conn.commit()

    def add_image(self, image_path, vector=None, description=None):
        """
        新增记录：支持传入描述文本
        :param description: 字符串，用于描述图片内容
        """
        vector_blob = vector.tobytes() if vector is not None else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 修改 SQL 增加字段占位符
            cursor.execute(
                "INSERT INTO images (image_path, vector_data, description) VALUES (?, ?, ?)",
                (image_path, vector_blob, description)
            )
            conn.commit()
            return cursor.lastrowid

    def delete_image(self, image_id):
        """根据 ID 删除记录并返回路径，方便后续物理清理"""
        # 强制转换 ID 类型，确保匹配
        clean_id = int(image_id)
        path_to_delete = self.get_path_by_id(clean_id)

        with self.get_connection() as conn:
            conn.execute("DELETE FROM images WHERE id = ?", (clean_id,))
            conn.commit()

        return path_to_delete  # 返回路径，UI 层级会用到

    def update_vectors_batch(self, update_list):
        """
        批量更新向量，使用单个事务确保速度和一致性
        :param update_list: [(vector_blob, img_id), ...]
        """
        with self.get_connection() as conn:
            # 使用 executemany 批量操作，比一条条 update 快几十倍
            conn.executemany(
                "UPDATE images SET vector_data = ? WHERE id = ?",
                update_list
            )
            # Context Manager (with) 会在这里自动执行 commit()
        logger.info(f"✅ 成功提交 {len(update_list)} 条向量更新到数据库")

    def get_all_images(self):
        """获取所有记录，包含描述字段"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, image_path, description, created_at FROM images ORDER BY created_at DESC")
            return cursor.fetchall()

    def get_path_by_id(self, image_id):
        """根据 FAISS 返回的 ID 查找路径"""
        # 强制转换，防止 numpy.int64 导致的查询失效
        clean_id = int(image_id)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT image_path FROM images WHERE id = ?", (clean_id,))
            row = cursor.fetchone()

            # 调试打印：确认查询是否成功
            if row:
                return row[0]
            else:
                print(f"🔎 数据库查询失败：ID {clean_id} (类型: {type(clean_id)}) 未找到结果")
                return None

    def load_all_vectors(self):
        """加载所有向量用于初始化 FAISS 索引"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, vector_data FROM images WHERE vector_data IS NOT NULL")
            rows = cursor.fetchall()

            ids = []
            vectors = []
            for row in rows:
                ids.append(row[0])
                # 将 bytes 转回 numpy 数组
                vectors.append(np.frombuffer(row[1], dtype='float32'))

            return np.array(ids), np.array(vectors)

    def refresh_storage_path(self, old_root, new_root):
        """
        当存储目录改变时，批量更新数据库中的图片绝对路径
        :param old_root: 旧的根目录路径 (来自 config.STORAGE_DIR 修改前)
        :param new_root: 新的根目录路径 (来自用户输入)
        """
        # 1. 路径标准化，确保不同系统的斜杠一致
        old_root = os.path.normpath(old_root)
        new_root = os.path.normpath(new_root)

        # 2. 只有路径真的变了才执行
        if old_root == new_root:
            return 0

        import logging
        logger = logging.getLogger(__name__)

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 使用 SQLite 的 REPLACE 函数：将路径中包含的 old_root 部分替换为 new_root
                # WHERE 子句确保我们只更新确实以旧路径开头的记录
                sql = "UPDATE images SET image_path = REPLACE(image_path, ?, ?) WHERE image_path LIKE ?"

                # LIKE 参数增加 % 通配符
                cursor.execute(sql, (old_root, new_root, f"{old_root}%"))

                count = cursor.rowcount
                conn.commit()

                logger.info(f" 数据库路径同步完成：共更新 {count} 条记录")
                return count

        except Exception as e:
            logger.error(f" 数据库路径同步失败: {str(e)}")
            raise e

    def clear_all_vectors(self):
        """【新增】彻底清空特征向量字段，为模型切换做准备"""
        with self.get_connection() as conn:
            conn.execute("UPDATE images SET vector_data = NULL")
            conn.commit()
        logger.info("🧹 数据库特征向量已清空")

    def update_description(self, db_id, new_desc):
        """更新指定 ID 的图片描述"""
        with self.get_connection() as conn:
            conn.execute("UPDATE images SET description = ? WHERE id = ?", (new_desc, db_id))
            conn.commit()

    def get_info_by_id(self, image_id):
        """根据 ID 获取图片的完整信息（路径和描述）"""
        clean_id = int(image_id)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 显式查询这两个字段
            cursor.execute("SELECT image_path, description FROM images WHERE id = ?", (clean_id,))
            return cursor.fetchone()  # 返回 (path, description)

db_manager = DatabaseManager()