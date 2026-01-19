"""
主程序入口
"""
import asyncio
import argparse
import sys
import logging
from pathlib import Path

# 添加 Web_analys 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "Web_analys"))
# 添加 utils 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from Web_analys.config_manager import ConfigManager
from Web_analys.BrowserManager import ChromeManager, EdgeManager
from Web_analys.core.url_capture_service import URLCaptureService
from Web_analys.grab import CourseAssignmentsCapture, AssignmentDetailCapture
from utils import clean_output_dir


def setup_logger(name: str, log_dir: str) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        log_dir: 日志目录路径
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 文件 handler
    log_file = log_path / f"{name}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


async def main_async():
    """异步主函数"""
    parser = argparse.ArgumentParser(
        description='Canvas 课程 Assignments 捕获工具 - 自动捕获所有课程的 assignments 页面',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-c', '--config', type=str, default=None,
                       help='配置文件路径（默认: config.json）')
    
    args = parser.parse_args()
    
    # 初始化日志
    log_dir = Path(__file__).parent / "logs"
    logger = setup_logger("canvas_capture", str(log_dir))
    
    logger.info("=" * 60)
    logger.info("Canvas 课程 Assignments 捕获工具")
    logger.info("=" * 60)
    
    # 加载配置
    logger.info("\n步骤 1: 加载配置")
    logger.info("-" * 60)
    
    config_path = Path(args.config) if args.config else Path(__file__).parent / "config.json"
    config = ConfigManager.load_config(config_path)
    
    logger.info(f"配置文件: {config_path}")
    logger.info(f"输出目录: {config.get('output_dir')}")
    logger.info(f"目标 URL: {config.get('target_urls')}")
    
    # 清理输出目录（如果配置开启）
    output_dir = config.get('output_dir', 'web_analys/output')
    clean_output_on_start = config.get('clean_output_on_start', True)
    
    if clean_output_on_start:
        logger.info("\n步骤 0: 清理输出目录")
        logger.info("-" * 60)
        clean_output_dir(output_dir, logger)
    else:
        logger.info("\n步骤 0: 跳过清理输出目录（配置已禁用）")
    
    # 获取目标 URL
    target_urls = config.get('target_urls', [])
    if not target_urls or not target_urls[0]:
        logger.error("❌ 配置中未找到 target_urls，请检查配置文件")
        return
    
    dashboard_url = target_urls[0]
    
    # 创建浏览器管理器
    logger.info("\n步骤 2: 创建浏览器管理器")
    logger.info("-" * 60)
    
    browser_manager = None
    try:
        browser_manager = ChromeManager(config)
        logger.info("✅ 使用 Chrome 浏览器管理器")
    except Exception as e:
        try:
            browser_manager = EdgeManager(config)
            logger.info("✅ 使用 Edge 浏览器管理器")
        except Exception as e2:
            logger.error(f"❌ 无法创建浏览器管理器: {e}, {e2}")
            return
    
    # 确保浏览器正在运行
    logger.info("\n步骤 3: 确保浏览器正在运行")
    logger.info("-" * 60)
    
    if not browser_manager.is_running():
        logger.warning("⚠️  浏览器未运行，尝试启动...")
        try:
            browser_manager.start()
            logger.info("✅ 浏览器已启动")
        except Exception as e:
            logger.error(f"❌ 启动浏览器失败: {e}")
            return
    else:
        logger.info("✅ 浏览器已在运行")
    
    # 捕获 dashboard 页面
    logger.info("\n步骤 4: 捕获 dashboard 页面")
    logger.info("-" * 60)
    url_capture_service = URLCaptureService(
        browser_manager=browser_manager,
        output_dir=output_dir,
        logger=logger
    )
    
    try:
        dashboard_result = await url_capture_service.capture_url(dashboard_url)
        
        if not dashboard_result:
            logger.error("❌ 捕获 dashboard 页面失败")
            return
        
        logger.info(f"✅ Dashboard 页面已保存: {dashboard_result.html_file}")
        
    except Exception as e:
        logger.error(f"❌ 捕获 dashboard 页面时出错: {e}", exc_info=True)
        return
    
    # 从 dashboard HTML 中提取课程并批量捕获 assignments 页面
    logger.info("\n步骤 5: 从 dashboard HTML 提取课程并批量捕获 assignments 页面")
    logger.info("-" * 60)
    
    course_capture_service = CourseAssignmentsCapture(
        browser_manager=browser_manager,
        output_dir=output_dir,
        logger=logger
    )
    
    try:
        assignments_results = await course_capture_service.capture_from_dashboard_html(
            dashboard_result.html_file
        )
        
        logger.info(f"✅ 成功捕获 {len(assignments_results)} 个 assignments 页面")
        
    except Exception as e:
        logger.error(f"❌ 捕获 assignments 页面时出错: {e}", exc_info=True)
        return
    
    # 从 assignments 页面中提取并批量捕获 assignment 详情页面
    logger.info("\n步骤 6: 从 assignments 页面提取并批量捕获 assignment 详情页面")
    logger.info("-" * 60)
    
    assignment_detail_capture_service = AssignmentDetailCapture(
        browser_manager=browser_manager,
        output_dir=output_dir,
        logger=logger
    )
    
    try:
        assignment_detail_results = await assignment_detail_capture_service.capture_all_from_output_dir(
            output_dir
        )
        
        logger.info(f"✅ 成功捕获 {len(assignment_detail_results)} 个 assignment 详情页面")
        
    except Exception as e:
        logger.error(f"❌ 捕获 assignment 详情页面时出错: {e}", exc_info=True)
        return
    
    # 完成
    logger.info("\n" + "=" * 60)
    logger.info("✅ 所有操作完成")
    logger.info("=" * 60)
    logger.info(f"Dashboard 页面: {dashboard_result.html_file}")
    logger.info(f"成功捕获 {len(assignments_results)} 个 assignments 页面")
    logger.info(f"成功捕获 {len(assignment_detail_results)} 个 assignment 详情页面")


def main():
    """主函数"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
