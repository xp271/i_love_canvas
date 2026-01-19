"""
主程序入口
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 添加 Web_analys 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "Web_analys"))
# 添加 Classes 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "Classes"))
# 添加 utils 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "utils"))
from grab import WebMonitor
from grab.page_capture import PageCapture
from courses_entrance import CoursesEntrance
from utils import setup_logger, cleanup_output_dir


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='网页监控工具 - 自动监听浏览器标签页并捕获目标网页',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-c', '--config', type=str, default=None,
                       help='配置文件路径（默认: 上级目录的 config.json）')
    
    args = parser.parse_args()
    
    # 初始化日志（在创建 monitor 之前，因为 monitor 需要日志）
    log_dir = Path(__file__).parent / "logs"
    logger = setup_logger("web_monitor", str(log_dir))
    
    monitor = WebMonitor(args.config)
    monitor.logger = logger  # 将 logger 传递给 monitor
    
    # 执行监控，等待保存 HTML
    asyncio.run(monitor.run())
    
    # 等待一下确保文件已保存
    import time
    time.sleep(1)
    
    # 从保存的 HTML 文件中提取元素并保存
    if monitor.last_html_file:
        page_capture = PageCapture(monitor.config)
        page_capture.logger = logger  # 将 logger 传递给 page_capture
        elements_file = page_capture.extract_and_save_hero_elements(monitor.last_html_file)
        
        if elements_file:
            # 创建点击器并循环点击所有元素
            clicker = CoursesEntrance(monitor.config)
            clicker.logger = logger  # 将 logger 传递给 clicker
            asyncio.run(clicker.run(elements_file))
    else:
        logger.warning("未找到保存的 HTML 文件")
    
    # 程序结束前清理输出目录（根据配置决定是否清理）
    output_dir = monitor.config.get('output_dir', 'web_analys/output')
    cleanup_on_exit = monitor.config.get('cleanup_on_exit', True)
    logger.info("\n正在清理输出目录...")
    cleanup_output_dir(output_dir, logger, cleanup_on_exit)


if __name__ == "__main__":
    main()
