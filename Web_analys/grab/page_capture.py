"""
页面捕获模块
负责捕获网页的 HTML 内容和截图
"""
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import requests


class PageCapture:
    """页面捕获器"""
    
    def __init__(self, config: dict):
        """
        初始化页面捕获器
        
        Args:
            config: 配置字典，包含 output_dir
        """
        self.config = config
        self.captured_urls = set()  # 记录已捕获的 URL，避免重复
        self.logger = logging.getLogger("web_monitor")  # 默认使用根 logger，可以在外部替换
    
    def is_target_url(self, url: str, target_urls: list):
        """检查 URL 是否为目标 URL"""
        if not target_urls:
            return False
        
        for target in target_urls:
            if target in url or url in target:
                return True
        return False
    
    def extract_hero_elements(self, html_content: str):
        """
        从 HTML 内容中提取类别为 DashboardCard__header_hero 的元素
        
        Args:
            html_content: HTML 内容字符串
        
        Returns:
            list: 包含元素信息的列表，每个元素是一个字典
        """
        hero_elements = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # 查找所有包含 DashboardCard__header_hero 类的元素（不区分大小写）
            elements = soup.find_all(class_=lambda x: x and 'DashboardCard__header_hero' in ' '.join(x) if isinstance(x, list) else 'DashboardCard__header_hero' in str(x))
            
            for element in elements:
                element_info = {
                    'tag': element.name,
                    'class': element.get('class', []),
                    'style': element.get('style', ''),
                    'html': str(element),
                    'text': element.get_text(strip=True)
                }
                # 提取背景颜色（如果有）
                style = element.get('style', '')
                if 'background-color' in style:
                    # 尝试提取 rgb 值
                    import re
                    bg_match = re.search(r'background-color:\s*([^;]+)', style)
                    if bg_match:
                        element_info['background_color'] = bg_match.group(1).strip()
                
                hero_elements.append(element_info)
        except Exception as e:
            self.logger.error(f"⚠️  提取 hero 元素时出错: {str(e)}")
        
        return hero_elements
    
    def extract_and_save_hero_elements(self, html_file: str):
        """
        从保存的 HTML 文件中提取 hero 元素并保存到 JSON 文件
        
        Args:
            html_file: HTML 文件路径
        
        Returns:
            str: 保存的元素文件路径，如果失败返回 None
        """
        if not Path(html_file).exists():
            self.logger.error(f"❌ HTML 文件不存在: {html_file}")
            return None
        
        self.logger.info(f"\n从 HTML 文件中提取 DashboardCard__header_hero 元素...")
        self.logger.info(f"   HTML 文件: {html_file}")
        
        # 读取 HTML 文件
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 提取 hero 元素
        hero_elements = self.extract_hero_elements(html_content)
        
        if not hero_elements:
            self.logger.warning("⚠️  未找到 DashboardCard__header_hero 元素")
            return None
        
        self.logger.info(f"✅ 提取到 {len(hero_elements)} 个 DashboardCard__header_hero 元素")
        
        # 保存所有元素到 JSON 文件
        output_dir = Path(self.config.get('output_dir', 'output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        elements_file = output_dir / "hero_elements.json"
        with open(elements_file, 'w', encoding='utf-8') as f:
            json.dump(hero_elements, f, indent=2, ensure_ascii=False)
        self.logger.info(f"✅ 所有元素已保存到: {elements_file}")
        
        return str(elements_file)
    
    async def capture_page(self, page, url: str, on_success_callback=None):
        """
        捕获页面内容
        
        Args:
            page: Playwright 页面对象
            url: 页面 URL
            on_success_callback: 成功回调函数，接收 (html_file, screenshot_file) 参数
        
        Returns:
            (html_file, screenshot_file) 或 (None, None)
        """
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_url = url.replace("://", "_").replace("/", "_").replace(":", "_")[:50]
        
        output_dir = Path(self.config.get('output_dir', 'output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        html_file = output_dir / f"{safe_url}_{timestamp}.html"
        screenshot_file = output_dir / f"{safe_url}_{timestamp}.png"
        
        try:
            # 等待页面加载
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass
            
            # 获取 HTML
            html_content = await page.content()
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 提取 DashboardCard__header_hero 类别的元素
            hero_elements = self.extract_hero_elements(html_content)
            
            # 获取截图
            await page.screenshot(path=str(screenshot_file), full_page=True)
            
            self.logger.info(f"✅ 已捕获: {url}")
            self.logger.info(f"   HTML: {html_file}")
            self.logger.info(f"   截图: {screenshot_file}")
            self.logger.info(f"   提取到 {len(hero_elements)} 个 DashboardCard__header_hero 元素")
            
            # 调用成功回调，传递 hero_elements（点击逻辑在回调中处理）
            if on_success_callback:
                # 检查回调是否是异步函数
                import asyncio
                import inspect
                if inspect.iscoroutinefunction(on_success_callback):
                    await on_success_callback(html_file, screenshot_file, hero_elements)
                else:
                    on_success_callback(html_file, screenshot_file, hero_elements)
            
            return str(html_file), str(screenshot_file)
        except Exception as e:
            self.logger.error(f"❌ 捕获失败 {url}: {str(e)}")
            return None, None
    
    async def open_target_urls(self, target_urls: list, cdp_url: str):
        """打开配置中的目标 URL（如果尚未打开）"""
        if not target_urls:
            return
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(cdp_url)
                
                # 获取所有已打开的页面
                all_pages = []
                for context in browser.contexts:
                    all_pages.extend(context.pages)
                
                # 检查哪些 URL 已经打开
                existing_urls = set()
                for page in all_pages:
                    url = page.url
                    # 跳过特殊页面
                    if url.startswith('chrome://') or url.startswith('about:'):
                        continue
                    # 检查是否匹配目标 URL
                    for target_url in target_urls:
                        if self.is_target_url(url, [target_url]):
                            existing_urls.add(target_url)
                
                # 只打开尚未打开的 URL
                urls_to_open = [url for url in target_urls if url not in existing_urls]
                
                if existing_urls:
                    self.logger.info(f"\n✅ 检测到已打开的标签页: {len(existing_urls)} 个")
                    for url in existing_urls:
                        self.logger.info(f"  已存在: {url}")
                
                if urls_to_open:
                    # 获取或创建上下文
                    contexts = browser.contexts
                    if not contexts:
                        context = await browser.new_context()
                    else:
                        context = contexts[0]
                    
                    # 打开每个目标 URL
                    self.logger.info(f"\n正在打开 {len(urls_to_open)} 个新网页...")
                    for url in urls_to_open:
                        try:
                            page = await context.new_page()
                            self.logger.info(f"  打开: {url}")
                            await page.goto(url, wait_until='networkidle', timeout=30000)
                            await asyncio.sleep(1)  # 等待页面加载
                        except Exception as e:
                            self.logger.warning(f"  ⚠️  打开失败 {url}: {str(e)}")
                    self.logger.info("✅ 所有目标网页已打开\n")
                else:
                    self.logger.info("✅ 所有目标网页已在浏览器中打开\n")
                
                await browser.close()
        except Exception as e:
            self.logger.error(f"⚠️  打开网页时出错: {str(e)}")
    
    async def check_and_capture(self, cdp_url: str, target_urls: list, on_success_callback=None):
        """
        检查浏览器标签页并捕获目标网页
        
        Args:
            cdp_url: Chrome DevTools Protocol URL
            target_urls: 目标 URL 列表
            on_success_callback: 成功回调函数
        
        Returns:
            bool: 是否成功捕获
        """
        try:
            # 获取所有标签页
            response = requests.get(f"{cdp_url}/json", timeout=2)
            if response.status_code != 200:
                return False
            
            tabs = response.json()
            if not tabs:
                return False
            
            # 连接到浏览器
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(cdp_url)
                
                # 获取所有页面
                all_pages = []
                for context in browser.contexts:
                    all_pages.extend(context.pages)
                
                # 检查每个页面
                captured = False
                for page in all_pages:
                    url = page.url
                    
                    # 跳过特殊页面
                    if url.startswith('chrome://') or url.startswith('about:'):
                        continue
                    
                    # 检查是否为目标 URL
                    if self.is_target_url(url, target_urls):
                        # 检查是否已捕获过（避免重复）
                        url_key = f"{url}_{datetime.now().strftime('%Y%m%d')}"
                        if url_key not in self.captured_urls:
                            await self.capture_page(page, url, on_success_callback)
                            self.captured_urls.add(url_key)
                            captured = True
                
                await browser.close()
                return captured
        except Exception as e:
            # 静默处理错误，避免中断监控
            return False

