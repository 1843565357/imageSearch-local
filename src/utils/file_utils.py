import os
import shutil
import logging
import traceback

logger = logging.getLogger(__name__)


def copy_directory_contents(src_dir, dst_dir):
    """
    将源目录下的所有内容（文件和子目录）复制到目标目录。
    :param src_dir: 旧目录路径
    :param dst_dir: 新目录路径
    :return: (bool, str) 成功标志和信息描述
    """
    # 1. 基础检查
    if not os.path.exists(src_dir):
        return False, f"源目录不存在: {src_dir}"

    if os.path.normpath(src_dir) == os.path.normpath(dst_dir):
        return True, "源目录与目标目录相同，无需复制。"

    try:
        # 2. 确保目标目录存在
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
            logger.info(f"创建新目录: {dst_dir}")

        # 3. 获取源目录下所有项目
        items = os.listdir(src_dir)
        if not items:
            return True, "源目录为空，无需迁移。"

        logger.info(f"开始复制数据: 从 {src_dir} 到 {dst_dir}")

        for item in items:
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(dst_dir, item)

            # 如果目标已存在同名项目，先清理以确保复制成功
            if os.path.exists(dst_path):
                if os.path.isdir(dst_path):
                    shutil.rmtree(dst_path)
                else:
                    os.remove(dst_path)

            # 4. 执行复制操作
            if os.path.isdir(src_path):
                # 递归复制文件夹
                shutil.copytree(src_path, dst_path)
            else:
                # 复制文件并保留元数据 (时间戳、权限等)
                shutil.copy2(src_path, dst_path)

            logger.debug(f"已复制: {item}")

        logger.info(f"数据复制成功！共复制 {len(items)} 个项目。")
        return True, f"成功复制 {len(items)} 个项目。"

    except Exception as e:
        error_msg = f"复制过程中出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return False, error_msg