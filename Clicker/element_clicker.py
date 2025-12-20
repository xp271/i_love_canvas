"""
网页元素点击器
功能：根据 HTML 文件中的元素定位并点击浏览器中的对应元素
"""
import asyncio
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import requests


class ElementClicker:
    """元素点击器"""
    
    def __init__(self, cdp_url: str = "http://localhost:9222"):
        """
        初始化点击器
        
        Args:
            cdp_url: Chrome DevTools Protocol URL
        """
        self.cdp_url = cdp_url
        self.logger = logging.getLogger("web_monitor")  # 默认使用根 logger，可以在外部替换
    
    def parse_html_line(self, html_file: str, line_number: int):
        """
        解析 HTML 文件，获取指定行号的元素信息
        
        Args:
            html_file: HTML 文件路径
            line_number: 行号（从 1 开始）
        
        Returns:
            dict: 包含元素信息的字典，包括 tag, attributes, text 等
        """
        html_path = Path(html_file)
        if not html_path.exists():
            raise FileNotFoundError(f"HTML 文件不存在: {html_file}")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_number < 1 or line_number > len(lines):
            raise ValueError(f"行号超出范围: {line_number} (文件共 {len(lines)} 行)")
        
        # 获取指定行的内容
        target_line = lines[line_number - 1].strip()
        
        # 如果该行是 HTML 标签的一部分，尝试解析
        if target_line and not target_line.startswith('//'):
            # 使用 BeautifulSoup 解析这一行附近的 HTML
            # 获取前后几行来构建完整的 HTML 片段
            start = max(0, line_number - 5)
            end = min(len(lines), line_number + 5)
            html_snippet = ''.join(lines[start:end])
            
            soup = BeautifulSoup(html_snippet, 'html.parser')
            
            # 尝试找到包含目标行的元素
            # 方法1: 通过行号计算在片段中的位置
            line_in_snippet = line_number - start
            
            # 方法2: 直接解析目标行，找到其中的标签
            soup_line = BeautifulSoup(target_line, 'html.parser')
            elements = soup_line.find_all()
            
            if elements:
                # 返回第一个找到的元素
                element = elements[0]
                return {
                    'tag': element.name,
                    'attributes': dict(element.attrs),
                    'text': element.get_text(strip=True),
                    'html': str(element),
                    'line_content': target_line
                }
            else:
                # 如果没有找到标签，返回原始行内容
                return {
                    'tag': None,
                    'attributes': {},
                    'text': target_line,
                    'html': target_line,
                    'line_content': target_line
                }
        
        return {
            'tag': None,
            'attributes': {},
            'text': target_line,
            'html': target_line,
            'line_content': target_line
        }
    
    def build_selector(self, element_info: dict):
        """
        根据元素信息构建 CSS 选择器或 XPath
        
        Args:
            element_info: 元素信息字典
        
        Returns:
            str: 选择器字符串
        """
        tag = element_info.get('tag')
        attrs = element_info.get('attributes', {})
        
        if not tag:
            return None
        
        # 优先使用 id
        if 'id' in attrs:
            return f"#{attrs['id']}"
        
        # 使用 class
        if 'class' in attrs:
            classes = attrs['class']
            if isinstance(classes, list):
                class_str = '.'.join(classes)
            else:
                class_str = classes
            return f"{tag}.{class_str.replace(' ', '.')}"
        
        # 使用 data-testid
        if 'data-testid' in attrs:
            return f"{tag}[data-testid='{attrs['data-testid']}']"
        
        # 使用 aria-label
        if 'aria-label' in attrs:
            return f"{tag}[aria-label='{attrs['aria-label']}']"
        
        # 使用 href（对于链接）
        if tag == 'a' and 'href' in attrs:
            return f"a[href='{attrs['href']}']"
        
        # 使用 title
        if 'title' in attrs:
            return f"{tag}[title='{attrs['title']}']"
        
        # 默认返回标签名
        return tag
    
    async def click_element(self, selector: str, page_url: str = None, wait_timeout: int = 10000):
        """
        在浏览器中点击指定元素
        
        Args:
            selector: CSS 选择器或 XPath
            page_url: 目标页面 URL，如果为 None 则使用当前页面
            wait_timeout: 等待超时时间（毫秒）
        
        Returns:
            bool: 是否成功点击
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(self.cdp_url)
                
                # 获取所有页面
                all_pages = []
                for context in browser.contexts:
                    all_pages.extend(context.pages)
                
                if not all_pages:
                    self.logger.error("❌ 未找到活动的浏览器页面")
                    return False
                
                # 选择目标页面
                target_page = None
                if page_url:
                    for pg in all_pages:
                        if page_url in pg.url:
                            target_page = pg
                            break
                
                if target_page is None:
                    target_page = all_pages[0]
                
                self.logger.info(f"当前页面: {target_page.url}")
                
                # 等待元素出现并点击
                try:
                    # 尝试使用 CSS 选择器
                    element = await target_page.wait_for_selector(selector, timeout=wait_timeout)
                    if element:
                        await element.click()
                        self.logger.info(f"✅ 成功点击元素: {selector}")
                        await browser.close()
                        return True
                except Exception as e1:
                    # 如果 CSS 选择器失败，尝试 XPath
                    try:
                        element = await target_page.wait_for_selector(f"xpath={selector}", timeout=wait_timeout)
                        if element:
                            await element.click()
                            self.logger.info(f"✅ 成功点击元素 (XPath): {selector}")
                            await browser.close()
                            return True
                    except Exception as e2:
                        self.logger.error(f"❌ 无法找到元素: {selector}")
                        self.logger.error(f"   CSS 选择器错误: {str(e1)}")
                        self.logger.error(f"   XPath 错误: {str(e2)}")
                        await browser.close()
                        return False
                
                await browser.close()
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 点击元素时出错: {str(e)}")
            return False
    
    def build_selector_from_element(self, element: dict):
        """
        根据元素信息构建 CSS 选择器（通用方法）
        
        Args:
            element: 元素信息字典，包含 tag, class 等
        
        Returns:
            str: CSS 选择器字符串，如果无法构建则返回 None
        """
        tag = element.get('tag', 'div')
        attrs = element.get('attributes', {})
        classes = element.get('class', [])
        
        # 如果直接提供了 class 列表
        if classes and isinstance(classes, list):
            class_str = '.'.join(classes).replace(' ', '.')
            return f"{tag}.{class_str}"
        
        # 从 attributes 中获取 class
        if 'class' in attrs:
            classes = attrs['class']
            if isinstance(classes, list):
                class_str = '.'.join(classes).replace(' ', '.')
            else:
                class_str = str(classes).replace(' ', '.')
            return f"{tag}.{class_str}"
        
        # 优先使用 id
        if 'id' in attrs:
            return f"#{attrs['id']}"
        
        # 使用 data-testid
        if 'data-testid' in attrs:
            return f"{tag}[data-testid='{attrs['data-testid']}']"
        
        # 使用 aria-label
        if 'aria-label' in attrs:
            return f"{tag}[aria-label='{attrs['aria-label']}']"
        
        # 使用 href（对于链接）
        if tag == 'a' and 'href' in attrs:
            return f"a[href='{attrs['href']}']"
        
        # 使用 title
        if 'title' in attrs:
            return f"{tag}[title='{attrs['title']}']"
        
        # 如果只有 tag，返回 tag
        if tag:
            return tag
        
        return None
    
    async def click_element_by_info(self, element: dict, page_url: str = None, wait_timeout: int = 10000, element_index: int = 0):
        """
        根据元素信息点击元素（通用方法）
        
        Args:
            element: 元素信息字典，包含 tag, class, attributes 等
            page_url: 目标页面 URL，如果为 None 则使用当前页面
            wait_timeout: 等待超时时间（毫秒）
            element_index: 元素索引（从 0 开始），用于选择第几个匹配的元素
        
        Returns:
            bool: 是否成功点击
        """
        try:
            selector = self.build_selector_from_element(element)
            if not selector:
                self.logger.warning("⚠️  无法构建选择器，跳过点击")
                return False
            
            self.logger.info(f"正在点击第 {element_index + 1} 个元素...")
            self.logger.info(f"   选择器: {selector}")
            self.logger.info(f"   索引: {element_index}")
            
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(self.cdp_url)
                
                # 获取所有页面
                all_pages = []
                for context in browser.contexts:
                    all_pages.extend(context.pages)
                
                if not all_pages:
                    self.logger.error("❌ 未找到活动的浏览器页面")
                    await browser.close()
                    return False
                
                # 选择目标页面
                target_page = None
                if page_url:
                    for pg in all_pages:
                        if page_url in pg.url:
                            target_page = pg
                            break
                
                if target_page is None:
                    target_page = all_pages[0]
                
                self.logger.info(f"当前页面: {target_page.url}")
                
                # 等待至少一个元素出现
                try:
                    await target_page.wait_for_selector(selector, timeout=wait_timeout, state='visible')
                except Exception as e:
                    self.logger.error(f"❌ 等待元素超时: {selector}")
                    self.logger.error(f"   错误: {str(e)}")
                    await browser.close()
                    return False
                
                # 使用 JavaScript 获取所有匹配的元素，然后选择指定索引的元素
                try:
                    element_handle = await target_page.evaluate_handle(f'''
                        () => {{
                            const elements = document.querySelectorAll('{selector}');
                            if (elements.length === 0) {{
                                return null;
                            }}
                            if ({element_index} >= elements.length) {{
                                return null;
                            }}
                            return elements[{element_index}];
                        }}
                    ''')
                    
                    if not element_handle or await element_handle.evaluate('el => el === null'):
                        self.logger.error(f"❌ 未找到索引为 {element_index} 的元素（可能元素数量不足）")
                        await browser.close()
                        return False
                    
                    # 尝试点击该元素的父元素（通常是可点击的链接或卡片）
                    try:
                        # 查找最近的包含链接的父元素
                        parent_link = await element_handle.evaluate_handle('''
                            el => {
                                let current = el.parentElement;
                                while (current) {
                                    if (current.tagName === 'A' || current.closest('a')) {
                                        return current.closest('a') || current;
                                    }
                                    current = current.parentElement;
                                }
                                return el.parentElement;
                            }
                        ''')
                        if parent_link:
                            await parent_link.click()
                            self.logger.info(f"✅ 成功点击第 {element_index + 1} 个元素的父链接")
                            await browser.close()
                            return True
                    except Exception as e1:
                        # 如果父元素点击失败，尝试点击元素本身
                        try:
                            await element_handle.click()
                            self.logger.info(f"✅ 成功点击第 {element_index + 1} 个元素")
                            await browser.close()
                            return True
                        except Exception as e2:
                            self.logger.warning(f"⚠️  点击失败: {str(e1)}, {str(e2)}")
                            await browser.close()
                            return False
                except Exception as e:
                    self.logger.error(f"❌ 无法找到或点击元素: {selector}")
                    self.logger.error(f"   错误: {str(e)}")
                    await browser.close()
                    return False
                
        except Exception as e:
            self.logger.error(f"❌ 点击元素时出错: {str(e)}")
            return False
    
    async def click_by_html_line(self, html_file: str, line_number: int, page_url: str = None):
        """
        根据 HTML 文件的行号点击对应元素
        
        Args:
            html_file: HTML 文件路径
            line_number: 行号
            page_url: 目标页面 URL
        
        Returns:
            bool: 是否成功点击
        """
        # 解析 HTML 文件
        element_info = self.parse_html_line(html_file, line_number)
        
        self.logger.info(f"解析 HTML 文件: {html_file}")
        self.logger.info(f"行号: {line_number}")
        self.logger.info(f"元素信息:")
        self.logger.info(f"  标签: {element_info.get('tag')}")
        self.logger.info(f"  属性: {element_info.get('attributes')}")
        self.logger.info(f"  文本: {element_info.get('text', '')[:50]}...")
        
        # 构建选择器
        selector = self.build_selector(element_info)
        
        if not selector:
            self.logger.error("❌ 无法构建选择器")
            return False
        
        self.logger.info(f"构建的选择器: {selector}")
        
        # 点击元素
        return await self.click_element(selector, page_url)

