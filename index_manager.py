import faiss
import numpy as np

class FaissIndexManager:
    def __init__(self, dimension=768):
        # 内部初始化逻辑
        self.raw_index = faiss.IndexFlatL2(dimension)
        self.index = faiss.IndexIDMap(self.raw_index)
        self.dimension = dimension

    def load_from_db(self, db_manager):
        """启动时从数据库全量加载"""
        ids, vectors = db_manager.load_all_vectors()
        if ids is not None and len(vectors) > 0:
            # 清空当前索引重新加载（防止重复）
            self.index.reset()
            self.index.add_with_ids(vectors.astype('float32'), ids.astype('int64'))
            print(f"✅ FAISS 索引重建完成，共加载 {len(ids)} 条数据")

    def add_single(self, db_id, vector):
        """单张入库时实时添加"""
        vec = np.array([vector]).astype('float32').reshape(1,        -1)
        ids = np.array([db_id]).astype('int64')
        self.index.add_with_ids(vec, ids)
        print(f"✨ FAISS 实时新增 ID: {db_id}")

    def search(self, query_vector, k=10):
        """搜索逻辑"""
        vec = np.array([query_vector]).astype('float32').reshape(1, -1)
        distances, indices = self.index.search(vec, k)
        # --- 添加这一行调试 ---
        print(f"DEBUG: FAISS 搜到的原始 ID 列表: {indices[0]}")
        print(f"DEBUG: FAISS 搜到的原始距离列表: {distances[0]}")

        return distances[0], indices[0]

    def remove_single(self, db_id):
        """从 FAISS 内存索引中移除指定 ID"""
        # FAISS 的 remove_ids 接收的是一个 numpy 数组
        ids_to_remove = np.array([db_id]).astype('int64')
        self.index.remove_ids(ids_to_remove)

# --- 关键：导出单例对象 ---
index_manager = FaissIndexManager(dimension=768)