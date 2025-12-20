"""
元素循环点击器
功能：遍历所有元素，依次点击，每次点击后等待并返回上一个界面
"""
import asyncio
import json
import logging
from pathlib import Path
import sys

# 添加 Clicker 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "Clicker"))
from element_clicker import ElementClicker


class ElementClickerLoop:
    """元素循环点击器 - 负责点击后的等待和返回逻辑"""
    
    def __init__(self, config: dict):
        """
        初始化点击器
        
        Args:
            config: 配置字典
        """
        self.config = config
        cdp_url = f"http://localhost:{config.get('chrome_debug_port', 9222)}"
        self.clicker = ElementClicker(cdp_url)
        self.logger = logging.getLogger("web_monitor")  # 默认使用根 logger，可以在外部替换
        # 将 logger 传递给 clicker
        if hasattr(self.clicker, 'logger'):
            self.clicker.logger = self.logger
    
    def load_elements(self, elements_file: str = None):
        """
        从 JSON 文件加载元素
        
        Args:
            elements_file: JSON 文件路径，如果为 None 则使用默认路径
        
        Returns:
            list: 元素列表
        """
        if elements_file is None:
            output_dir = Path(self.config.get('output_dir', 'web_analys/output'))
            elements_file = output_dir / "hero_elements.json"
        
        elements_path = Path(elements_file)
        if not elements_path.exists():
            self.logger.error(f"❌ 元素文件不存在: {elements_file}")
            return []
        
        with open(elements_path, 'r', encoding='utf-8') as f:
            elements = json.load(f)
        
        self.logger.info(f"✅ 加载了 {len(elements)} 个元素")
        return elements
    
    async def go_back(self):
        """返回上一个界面（浏览器后退）"""
        try:
            from playwright.async_api import async_playwright
            
            cdp_url = f"http://localhost:{self.config.get('chrome_debug_port', 9222)}"
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(cdp_url)
                
                # 获取所有页面
                all_pages = []
                for context in browser.contexts:
                    all_pages.extend(context.pages)
                
                if all_pages:
                    target_page = all_pages[0]
                    await target_page.go_back()
                    self.logger.info("✅ 已返回上一个界面")
                    await browser.close()
                    return True
                else:
                    self.logger.warning("⚠️  未找到活动的浏览器页面")
                    await browser.close()
                    return False
        except Exception as e:
            self.logger.warning(f"⚠️  返回上一个界面时出错: {str(e)}")
            return False
    
    async def click_all_elements(self, elements: list, wait_seconds: int = 10):
        """
        遍历点击所有元素，每次点击后等待并返回上一个界面
        
        Args:
            elements: 元素列表
            wait_seconds: 每次点击后等待的秒数
        """
        if not elements:
            self.logger.warning("⚠️  没有可点击的元素")
            return
        
        target_urls = self.config.get('target_urls', [])
        page_url = target_urls[0] if target_urls else None
        
        self.logger.info(f"\n开始遍历点击 {len(elements)} 个元素...")
        self.logger.info("=" * 60)
        
        for i, element in enumerate(elements, 1):
            self.logger.info(f"\n[{i}/{len(elements)}] 正在点击第 {i} 个元素...")
            
            # 调用通用点击器点击元素（传入索引，从 0 开始）
            success = await self.clicker.click_element_by_info(element, page_url, element_index=i-1)
            
            if success:
                self.logger.info(f"✅ 第 {i} 个元素点击成功")
            else:
                self.logger.warning(f"⚠️  第 {i} 个元素点击失败")
            
            # 所有元素点击后都要等待并返回（包括最后一个）
            self.logger.info(f"等待 {wait_seconds} 秒后返回上一个界面...")
            await asyncio.sleep(wait_seconds)
            
            # 返回上一个界面
            await self.go_back()
            
            # 等待页面加载
            await asyncio.sleep(2)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"✅ 已完成所有 {len(elements)} 个元素的点击")
    
    async def run(self, elements_file: str = None):
        """
        运行循环点击流程
        
        Args:
            elements_file: JSON 文件路径
        """
        # 加载元素
        elements = self.load_elements(elements_file)
        
        if not elements:
            return
        
        # 遍历点击所有元素
        await self.click_all_elements(elements)

