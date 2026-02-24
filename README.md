## imageSearch-local
**imageSearch-local** 是一个基于深度学习的本地图像检索客户端。它利用 Meta 的 **DINOv2** 视觉大模型提取图像特征，并结合 **FAISS** 向量搜索引擎实现亚秒级的视觉相似度检索。项目专注于隐私安全，所有处理流程均在本地执行，无需上传数据至云端。

## 技术栈

**视觉特征提取**：DINOv2。

**向量搜索**：FAISS。

**前端交互框架**：PyQt5。

**数据管理系统**：SQLite3。



## 页面

![image-20260225004719031](https://github.com/1843565357/imageSearch-local/blob/main/readme_image/image-20260225004719031.png)

![image-20260225004745974](https://github.com/1843565357/imageSearch-local/blob/main/readme_image/image-20260225004745974.png)

![image-20260225004754461](https://github.com/1843565357/imageSearch-local/blob/main/readme_image/image-20260225004754461.png)

![image-20260225004802167](https://github.com/1843565357/imageSearch-local/blob/main/readme_image/image-20260225004802167.png)

## 快速开始

### 1. 环境准备

推荐使用 Python 3.10 环境：

```bash
conda create -n Image-App python=3.10
conda activate Image-App
pip install -r requirements.txt
```

### 2.运行程序

```bash
python main.py
```



### 3. 模型配置

首次启动时，程序会根据 `config.py` 中的链接自动下载权重文件至 `models` 文件夹。您也可以在“系统设置”页面手动指定模型存放目录。



## 项目结构

- `main.py`：程序入口，负责输出重定向、闪屏显示及全局单例初始化。
- `model_manager.py`：处理 DINOv2 模型加载与 `extract_feature` 核心逻辑。
- `index_manager.py`：管理 FAISS 内存索引，执行向量搜索与维度适配。
- `database.py`：封装 SQLite 操作，包括批量更新特征向量和路径同步。
- `config.py`：管理 JSON 配置文件的读写及全局变量更新。
- `util/`：包含特征归一化 (`feature_utils.py`) 与文件系统迁移工具。

## 部署打包

本项目提供了预置的 `.spec` 文件，针对深度学习环境进行了深度优化：

Bash

```
pyinstaller ImageSearch.spec
```
