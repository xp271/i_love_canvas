"""
网页监控模块
负责监控浏览器标签页并协调抓取流程
"""
import asyncio
import json
import signal
import logging
from pathlib import Path
from .chrome_manager import ChromeManager
from .page_capture import PageCapture


class WebMonitor:
    """网页监控器"""
    
    def __init__(self, config_path: str = None):
        """
        初始化监控器
        
        Args:
            config_path: 配置文件路径，如果为 None 则使用默认路径
        """
        # 默认配置文件路径（上级目录）
        if config_path is None:
            script_dir = Path(__file__).parent.parent
            config_path = script_dir.parent / "config.json"
        
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.running = True
        self.hero_elements = []  # 存储提取的 hero 元素
        self.last_html_file = None  # 存储最后保存的 HTML 文件路径
        self.logger = logging.getLogger("web_monitor")  # 默认使用根 logger，可以在 main 中替换
        
        # 初始化组件
        self.chrome_manager = ChromeManager(self.config)
        self.page_capture = PageCapture(self.config)
        self.page_capture.logger = self.logger  # 共享 logger
        
        # 设置信号处理，优雅退出
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """处理退出信号"""
        self.logger.info("\n正在退出...")
        self.running = False
    
    def load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            # 创建默认配置
            default_config = {
                "target_urls": [
                    "https://sit.instructure.com/"
                ],
                "check_interval": 5,
                "output_dir": "web_analys/output",
                "chrome_debug_port": 9222,
                "chrome_user_data_dir": "/tmp/chrome-debug-profile"
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"已创建默认配置文件: {self.config_path}")
            return default_config
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 确保输出目录是相对路径时，基于脚本目录
        output_dir = config.get('output_dir', 'output')
        if not Path(output_dir).is_absolute():
            script_dir = Path(__file__).parent.parent
            # 如果已经是相对路径，直接使用；否则拼接
            if output_dir.startswith('web_analys/'):
                config['output_dir'] = str(script_dir.parent / output_dir)
            else:
                config['output_dir'] = str(script_dir / output_dir)
        
        return config
    
    async def on_capture_success(self, html_file, screenshot_file, hero_elements=None):
        """捕获成功回调"""
        self.logger.info("\n✅ 捕获完成")
        if hero_elements:
            self.logger.info(f"   提取到的 DashboardCard__header_hero 元素数量: {len(hero_elements)}")
            # 存储到实例变量中（用于后续处理）
            self.hero_elements = hero_elements
            self.last_html_file = html_file
        
        self.logger.info("正在退出...")
        self.running = False
    
    async def monitor_loop(self):
        """监控循环"""
        self.logger.info("=" * 60)
        self.logger.info("网页监控已启动")
        self.logger.info(f"目标 URL: {self.config.get('target_urls', [])}")
        self.logger.info(f"检查间隔: {self.config.get('check_interval', 5)} 秒")
        self.logger.info(f"输出目录: {self.config.get('output_dir', 'output')}")
        self.logger.info("=" * 60)
        self.logger.info("按 Ctrl+C 停止监控\n")
        
        check_interval = self.config.get('check_interval', 5)
        target_urls = self.config.get('target_urls', [])
        cdp_url = self.chrome_manager.get_cdp_url()
        
        while self.running:
            try:
                captured = await self.page_capture.check_and_capture(
                    cdp_url, 
                    target_urls,
                    self.on_capture_success
                )
                # 如果捕获成功，on_capture_success 会设置 self.running = False
                # 立即检查并退出
                if not self.running:
                    break
            except Exception as e:
                self.logger.error(f"检查时出错: {str(e)}")
            
            # 等待指定间隔
            await asyncio.sleep(check_interval)
    
    async def run(self):
        """运行监控器"""
        # 启动 Chrome
        try:
            self.chrome_manager.start_chrome_with_debug()
        except Exception as e:
            self.logger.error(f"❌ 启动 Chrome 失败: {str(e)}")
            return
        
        # 等待一下让 Chrome 完全启动
        await asyncio.sleep(3)
        
        # 自动打开配置中的目标 URL
        target_urls = self.config.get('target_urls', [])
        cdp_url = self.chrome_manager.get_cdp_url()
        await self.page_capture.open_target_urls(target_urls, cdp_url)
        
        # 等待一下让页面完全加载
        await asyncio.sleep(2)
        
        # 开始监控循环
        await self.monitor_loop()
    
    async def check_once(self):
        """单次检查模式"""
        target_urls = self.config.get('target_urls', [])
        cdp_url = self.chrome_manager.get_cdp_url()
        await self.page_capture.check_and_capture(
            cdp_url,
            target_urls,
            self.on_capture_success
        )

