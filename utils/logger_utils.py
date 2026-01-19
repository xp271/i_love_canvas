"""
日志工具函数
"""
import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(name: str = "web_monitor", log_dir: str = "logs", level: int = logging.INFO):
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录
        level: 日志级别
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # 创建日志文件名（带时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_path / f"{name}_{timestamp}.log"
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 文件处理器（输出到文件）
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # 控制台处理器（输出到控制台）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info(f"日志文件: {log_file}")
    
    return logger

