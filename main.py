#!/usr/bin/env python3
"""
Image-App 入口脚本
重构后的项目结构需要这个包装器来保持原有的执行方式
"""
import sys
import os

# 添加当前目录到Python路径，确保能找到src模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app.main import main

if __name__ == "__main__":
    main()