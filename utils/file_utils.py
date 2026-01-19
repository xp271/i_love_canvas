"""
文件操作工具函数
"""
import shutil
from pathlib import Path


def cleanup_output_dir(output_dir: str, logger, cleanup_on_exit: bool = True):
    """
    清理输出目录
    
    Args:
        output_dir: 输出目录路径
        logger: 日志记录器
        cleanup_on_exit: 是否在运行结束时清理文件，默认为 True
    """
    if not cleanup_on_exit:
        logger.info("配置为保留输出文件，跳过清理")
        return
    
    try:
        output_path = Path(output_dir)
        if output_path.exists() and output_path.is_dir():
            # 删除目录中的所有文件
            for item in output_path.iterdir():
                if item.is_file():
                    item.unlink()
                    logger.info(f"已删除文件: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    logger.info(f"已删除目录: {item.name}")
            logger.info(f"✅ 已清理输出目录: {output_dir}")
        else:
            logger.info(f"输出目录不存在，无需清理: {output_dir}")
    except Exception as e:
        logger.error(f"清理输出目录时出错: {str(e)}")

