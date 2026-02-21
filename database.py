import sqlite3
import numpy as np
import os


class DatabaseManager:
    # 接收外部传入的文件夹和文件名
    def __init__(self, db_folder="database", db_name="image.db"):
        self.db_path = os.path.join(db_folder, db_name)

        # 自动创建数据库文件夹（如果不存在）
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)

        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            conn.execute('''
                    CREATE TABLE IF NOT EXISTS images (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        image_path TEXT NOT NULL,
                        vector_data BLOB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            conn.commit()

    def add_image(self, image_path, vector=None):
        """
        新增记录
        :param vector: numpy array 形式的特征向量
        """
        vector_blob = vector.tobytes() if vector is not None else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO images (image_path, vector_data) VALUES (?, ?)",
                (image_path, vector_blob)
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

    def update_vector(self, image_id, vector):
        """更新已有记录的特征向量 (留给 DINOv2 重新扫描时使用)"""
        vector_blob = vector.tobytes()
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE images SET vector_data = ? WHERE id = ?",
                (vector_blob, image_id)
            )
            conn.commit()

    def get_all_images(self):
        """获取所有记录用于数据库管理页面显示"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, image_path, created_at FROM images ORDER BY created_at DESC")
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
db_manager = DatabaseManager()