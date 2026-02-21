import numpy as np


def process_feature_vector(features):
    # 1. 转换为 numpy (如果是 torch.Tensor)
    if hasattr(features, "cpu"):
        features_np = features.cpu().numpy()
    else:
        features_np = np.array(features)

    # 2. 展平并确保是 float32
    features_flat = features_np.flatten().astype(np.float32)

    # 3. L2 归一化
    # 归一化后，余弦相似度 = 欧氏距离的线性映射，检索更准确
    l2_norm = np.linalg.norm(features_flat)
    if l2_norm > 0:
        features_flat = features_flat / l2_norm

    # 4. 返回符合 FAISS 要求的形状 (1, dimension)
    # 注意：这里不转 tolist()，保留 numpy 数组
    return features_flat