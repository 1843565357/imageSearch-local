import logging

import faiss
import numpy as np

import config
from config import MODEL_DIMENSIONS, MODEL_NAME

logger = logging.getLogger(__name__)


class FaissIndexManager:
    def __init__(self, model_name=None):
        # 核心修改：使用 config 模块名访问，保证获取到的是 load_config() 后的最新值
        target_model = model_name or config.MODEL_NAME

        # 容错：如果 config.MODEL_NAME 还没加载出来，先给个默认值
        if not target_model:
            target_model = "dinov2_vitb14"

        self.dimension = MODEL_DIMENSIONS.get(target_model, 768)
        self.reinit_index(self.dimension)
        logger.info(f"FAISS 初始化完成 - 模型: {target_model}, 维度: {self.dimension}")

    def reinit_index(self, new_dimension):
        """完全重置索引结构 (线程安全地重建)"""
        self.dimension = new_dimension
        self.raw_index = faiss.IndexFlatL2(self.dimension)
        self.index = faiss.IndexIDMap(self.raw_index)
        logger.info(f"🚀 FAISS 索引已重置，当前维度: {self.dimension}")

    def load_from_db(self, db_manager):
        """全量加载逻辑"""
        ids, vectors = db_manager.load_all_vectors()

        if ids is None or len(vectors) == 0:
            self.index.reset()
            logger.info("数据库无向量数据，FAISS 已清空。")
            return

        # 校验维度一致性
        incoming_dim = vectors.shape[1]
        if incoming_dim != self.dimension:
            # 只有在确实需要兼容旧数据时才自动适配
            logger.warning(f"⚠️ 维度不匹配！DB({incoming_dim}) != 索引({self.dimension})，强制同步...")
            self.reinit_index(incoming_dim)

        self.index.reset()
        self.index.add_with_ids(vectors.astype('float32'), ids.astype('int64'))
        logger.info(f"✅ FAISS 加载成功，维度: {self.dimension}, 数量: {len(ids)}")

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
        logger.debug(f"FAISS 搜到的原始 ID 列表: {indices[0]}")
        logger.debug(f"FAISS 搜到的原始距离列表: {distances[0]}")

        return distances[0], indices[0]

    def remove_single(self, db_id):
        """从 FAISS 内存索引中移除指定 ID"""
        # FAISS 的 remove_ids 接收的是一个 numpy 数组
        ids_to_remove = np.array([db_id]).astype('int64')
        self.index.remove_ids(ids_to_remove)

# --- 关键：导出单例对象 ---
index_manager = FaissIndexManager()