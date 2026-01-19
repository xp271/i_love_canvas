"""
元素循环点击基类
抽象出"点击元素 -> 保存新页面 -> 执行操作 -> 返回"的逻辑
"""
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
import sys

# 添加 Clicker 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "Clicker"))
from element_clicker import ElementClicker


class BaseElementLoop:
    """元素循环点击基类 - 抽象出通用的点击循环逻辑"""
    
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
    
    def _get_cdp_url(self):
        """
        获取 CDP URL（公共方法）
        
        Returns:
            str: CDP URL
        """
        return f"http://localhost:{self.config.get('chrome_debug_port', 9222)}"
    
    def _get_all_pages(self, browser):
        """
        获取所有页面（公共方法）
        
        Args:
            browser: Playwright 浏览器对象
        
        Returns:
            list: 页面列表
        """
        all_pages = []
        if browser:
            for context in browser.contexts:
                all_pages.extend(context.pages)
        return all_pages
    
    async def _get_target_page_after_click(self, browser, original_url=None):
        """
        获取点击后的目标页面（可被子类重写）
        
        Args:
            browser: Playwright 浏览器对象
            original_url: 原始页面 URL（用于排除）
        
        Returns:
            Page 对象或 None
        """
        all_pages = self._get_all_pages(browser)
        
        if not all_pages:
            return None
        
        # 默认实现：返回最后一个非特殊页面
        for pg in reversed(all_pages):
            if not pg.url.startswith('chrome://') and not pg.url.startswith('about:') and not pg.url.startswith('devtools://'):
                return pg
        
        return None
    
    async def _wait_for_page_load(self, page, timeout=10000, fallback_sleep=2):
        """
        统一的页面加载等待逻辑
        
        Args:
            page: Playwright 页面对象
            timeout: 等待超时时间（毫秒）
            fallback_sleep: 超时后的备用等待时间（秒）
        """
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
        except:
            await asyncio.sleep(fallback_sleep)
    
    async def _save_page_after_click(self, browser, original_url=None):
        """
        点击后保存页面的通用逻辑
        
        Args:
            browser: Playwright 浏览器对象
            original_url: 原始页面 URL（用于排除）
        
        Returns:
            tuple: (html_file, screenshot_file) 或 (None, None)
        """
        try:
            target_page = await self._get_target_page_after_click(browser, original_url)
            
            if target_page:
                # 等待页面加载
                await self._wait_for_page_load(target_page)
                
                # 保存页面内容
                return await self.save_page_content(target_page)
            else:
                self.logger.warning("⚠️  未找到目标页面")
                return None, None
        except Exception as e:
            self.logger.warning(f"⚠️  保存页面时出错: {str(e)}")
            return None, None
    
    
    async def go_back(self):
        """
        返回上一个界面（浏览器后退）
        
        子类可以重写此方法以实现自定义的返回逻辑
        """
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                cdp_url = self._get_cdp_url()
                browser = await p.chromium.connect_over_cdp(cdp_url)
                
                try:
                    all_pages = self._get_all_pages(browser)
                    
                    if all_pages:
                        target_page = all_pages[0]
                        await target_page.go_back()
                        self.logger.info("✅ 已返回上一个界面")
                        return True
                    else:
                        self.logger.warning("⚠️  未找到活动的浏览器页面")
                        return False
                finally:
                    await browser.close()
        except Exception as e:
            self.logger.warning(f"⚠️  返回上一个界面时出错: {str(e)}")
            return False
    
    async def save_page_content(self, page, url: str = None, parent_html_file: str = None):
        """
        保存页面的 HTML 和截图
        
        Args:
            page: Playwright 页面对象
            url: 页面 URL（用于生成文件名）
            parent_html_file: 父级 HTML 文件路径（如果提供，则在父级目录下创建子文件夹）
        
        Returns:
            tuple: (html_file, screenshot_file) 文件路径，如果失败返回 (None, None)
        """
        try:
            # 等待页面加载
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass
            
            # 获取当前页面 URL（如果没有提供）
            if url is None:
                url = page.url
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 根据是否有父级文件决定保存路径
            utils_path = Path(__file__).parent.parent.parent / "utils"
            if str(utils_path) not in sys.path:
                sys.path.insert(0, str(utils_path))
            from url_utils import url_to_folder_name, url_to_subfolder_name
            
            if parent_html_file:
                # 层级结构：在父级文件的目录下创建子文件夹
                parent_path = Path(parent_html_file)
                parent_dir = parent_path.parent
                
                # 从 URL 提取子文件夹名称
                subfolder_name = url_to_subfolder_name(url)
                url_dir = parent_dir / subfolder_name
            else:
                # 扁平结构：根据 URL 创建文件夹（保持向后兼容）
                folder_name = url_to_folder_name(url)
                output_dir = Path(self.config.get('output_dir', 'Web_analys/output'))
                url_dir = output_dir / folder_name
            
            url_dir.mkdir(parents=True, exist_ok=True)
            
            html_file = url_dir / f"{timestamp}.html"
            screenshot_file = url_dir / f"{timestamp}.png"
            
            # 获取 HTML
            html_content = await page.content()
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 获取截图
            await page.screenshot(path=str(screenshot_file), full_page=True)
            
            self.logger.info(f"✅ 已保存新页面内容")
            self.logger.info(f"   HTML: {html_file}")
            self.logger.info(f"   截图: {screenshot_file}")
            
            return str(html_file), str(screenshot_file)
        except Exception as e:
            self.logger.error(f"❌ 保存页面内容失败: {str(e)}")
            return None, None
    
    async def after_click_action(self, element_index: int, element: dict, click_success: bool, html_file: str = None, screenshot_file: str = None):
        """
        点击元素后执行的操作（抽象方法）
        
        Args:
            element_index: 元素索引（从 0 开始）
            element: 元素信息字典
            click_success: 点击是否成功
            html_file: 点击后新页面的 HTML 文件路径
            screenshot_file: 点击后新页面的截图文件路径
        
        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 after_click_action 方法")
    
    async def click_all_elements(self, elements: list):
        """
        遍历点击所有元素的核心逻辑
        
        Args:
            elements: 元素列表
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
            
            # 如果点击成功，等待页面加载并保存 HTML 和截图
            html_file = None
            screenshot_file = None
            if success:
                try:
                    from playwright.async_api import async_playwright
                    
                    async with async_playwright() as p:
                        cdp_url = self._get_cdp_url()
                        browser = await p.chromium.connect_over_cdp(cdp_url)
                        
                        html_file, screenshot_file = await self._save_page_after_click(browser, page_url)
                        
                        await browser.close()
                except Exception as e:
                    self.logger.warning(f"⚠️  保存新页面内容时出错: {str(e)}")
            
            # 执行点击后的操作（由子类实现，传入保存的 HTML 和截图路径）
            await self.after_click_action(i-1, element, success, html_file, screenshot_file)
        
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

