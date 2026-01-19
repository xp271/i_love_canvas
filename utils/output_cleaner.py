"""
输出清理工具
清理输出目录中的文件
"""
import logging
import shutil
from pathlib import Path
from typing import Optional


def clean_output_dir(output_dir: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    清理输出目录中的所有文件
    
    Args:
        output_dir: 输出目录路径
        logger: 日志记录器
        
    Returns:
        bool: 是否成功清理
    """
    logger = logger or logging.getLogger(__name__)
    
    output_path = Path(output_dir)
    
    if not output_path.exists():
        logger.info(f"输出目录不存在，无需清理: {output_dir}")
        return True
    
    try:
        # 删除目录中的所有内容
        for item in output_path.iterdir():
            if item.is_file():
                item.unlink()
                logger.debug(f"删除文件: {item}")
            elif item.is_dir():
                shutil.rmtree(item)
                logger.debug(f"删除目录: {item}")
        
        logger.info(f"✅ 已清理输出目录: {output_dir}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 清理输出目录失败: {output_dir}, 错误: {str(e)}", exc_info=True)
        return False

