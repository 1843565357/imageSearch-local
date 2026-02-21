import sys

import torch
from torch.hub import download_url_to_file
from torchvision import transforms
from PIL import Image
import numpy as np
import os


class DINOv2Manager:
    # 官方模型权重下载链接映射
    MODEL_URLS = {
        "dinov2_vits14": "https://dl.fbaipublicfiles.com/dinov2/dinov2_vits14/dinov2_vits14_pretrain.pth",
        "dinov2_vitb14": "https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14/dinov2_vitb14_pretrain.pth",
    }

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
        model_root_dir: 模型的根存放目录（如 F:/code/models）
        model_name: 模型的架构名（如 dinov2_vitb14）
        """
        if self.model is not None:
            return

        # 1. 自动拼接出该模型对应的完整文件路径
        # 结果：F:/code/models/dinov2_vitb14.pth
        target_path = os.path.join(model_root_dir, f"{model_name}.pth")

        # 2. 自动检测并下载
        if not os.path.exists(target_path):
            os.makedirs(model_root_dir, exist_ok=True)
            url = self.MODEL_URLS.get(model_name)
            # 打包后关闭进度条，防止 NoneType 报错
            is_frozen = getattr(sys, 'frozen', False)
            download_url_to_file(url, target_path, progress=not is_frozen)

        # 3. 加载
        self.model = torch.hub.load('facebookresearch/dinov2', model_name)
        self.model.load_state_dict(torch.load(target_path, map_location='cpu'))
        self.model.eval()
        print("模型加载完成！")

    @torch.no_grad()
    def extract_feature(self, image_path):
        if self.model is None:
            raise RuntimeError("模型尚未初始化，请先调用 load_model")

        img = Image.open(image_path).convert('RGB')
        tensor = self.transform(img).unsqueeze(0).to(self.device)
        features = self.model(tensor)
        feat_np = features.cpu().numpy().flatten().astype('float32')
        return feat_np / np.linalg.norm(feat_np)


# --- 关键：在这里实例化，其他文件 import 这个变量 ---
model_image = DINOv2Manager()