import logging
import sys
import torch
from torch.hub import download_url_to_file
from torchvision import transforms
from PIL import Image
import numpy as np
import os
from config import MODEL_URLS
from util.feature_utils import process_feature_vector


class DINOv2Manager:

    def __init__(self):
        self.model = None
        self.device = torch.device("cpu")
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def load_model(self, model_root_dir, model_name):
        """
        model_root_dir: 模型的根存放目录
        model_name: 模型的架构名
        """
        # --- 1. 修改后的判断逻辑 ---
        # 如果模型已存在，且名称也没变，才跳过
        # 我们需要一个属性来记录当前加载的是哪个模型
        if self.model is not None and getattr(self, "current_model_name", "") == model_name:
            return

        logging.info(f"正在切换模型引擎至: {model_name}...")

        # 2. 清理旧模型，释放显存/内存 (如果是从 Large 换到 Small)
        if self.model is not None:
            self.model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        # 3. 自动拼接路径
        target_path = os.path.join(model_root_dir, f"{model_name}.pth")

        # 4. 自动检测并下载 (保持原有逻辑)
        if not os.path.exists(target_path):
            os.makedirs(model_root_dir, exist_ok=True)
            url = MODEL_URLS.get(model_name)
            is_frozen = getattr(sys, 'frozen', False)
            download_url_to_file(url, target_path, progress=not is_frozen)

        # 5. 加载新架构与权重
        # 注意：torch.hub.load 会根据 model_name 创建对应的网络结构 (384/768/1024)
        self.model = torch.hub.load('facebookresearch/dinov2', model_name)
        self.model.load_state_dict(torch.load(target_path, map_location='cpu'))
        self.model.eval()

        # 记录当前模型名称，方便下次对比
        self.current_model_name = model_name
        logging.info(f"✨ 模型 {model_name} 加载完成！")

    @torch.no_grad()
    def extract_feature(self, image_path):
        if self.model is None:
            raise RuntimeError("模型尚未初始化，请先调用 load_model")

        # 1. 基础图像处理
        img = Image.open(image_path).convert('RGB')
        tensor = self.transform(img).unsqueeze(0).to(self.device)

        # 2. 模型推理 (得到的是 torch.Tensor)
        features = self.model(tensor)

        # 3. 【核心应用】使用你的处理工具
        # 它会自动处理 Tensor 转 Numpy、展平、float32 和 L2 归一化
        feat_processed = process_feature_vector(features)

        return feat_processed


# --- 关键：在这里实例化，其他文件 import 这个变量 ---
model_image = DINOv2Manager()