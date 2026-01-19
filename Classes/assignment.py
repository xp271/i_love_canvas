"""
作业详情页点击器
继承 BaseElementLoop，实现点击作业详情页并保存的逻辑
"""
import asyncio
import sys
from pathlib import Path

# 添加 Classes 目录到路径（用于相对导入）
sys.path.insert(0, str(Path(__file__).parent))
from base_element_loop import BaseElementLoop


class Assignment(BaseElementLoop):
    """作业详情页点击器 - 实现点击作业并保存详情页的逻辑"""
    
    def __init__(self, config: dict, wait_seconds: int = 5, parent_html_file: str = None):
        """
        初始化点击器
        
        Args:
            config: 配置字典
            wait_seconds: 每次点击后等待的秒数，默认 5 秒
            parent_html_file: 父级 HTML 文件路径（assignments 页面），用于创建层级结构
        """
        super().__init__(config)
        self.wait_seconds = wait_seconds
        self.parent_html_file = parent_html_file
    
    async def after_click_action(self, element_index: int, element: dict, click_success: bool, html_file: str = None, screenshot_file: str = None):
        """
        点击作业后执行的操作：等待并保存详情页
        
        Args:
            element_index: 元素索引（从 0 开始）
            element: 元素信息字典
            click_success: 点击是否成功
            html_file: 点击后新页面的 HTML 文件路径
            screenshot_file: 点击后新页面的截图文件路径
        """
        if html_file and screenshot_file:
            self.logger.info(f"   作业详情页 HTML: {html_file}")
            self.logger.info(f"   作业详情页截图: {screenshot_file}")
        
        # 等待指定秒数
        self.logger.info(f"等待 {self.wait_seconds} 秒...")
        await asyncio.sleep(self.wait_seconds)
        
        # 返回上一个界面（回到 assignments 页面）
        self.logger.info("返回 assignments 页面...")
        await self.go_back()
        
        # 等待页面加载
        await asyncio.sleep(1)
    
    async def _get_target_page_after_click(self, browser, original_url=None):
        """
        获取点击后的目标页面（作业详情页）
        重写基类方法以自定义页面查找逻辑
        
        Args:
            browser: Playwright 浏览器对象
            original_url: 原始页面 URL（assignments 列表页，需要排除）
        
        Returns:
            Page 对象或 None
        """
        all_pages = self._get_all_pages(browser)
        
        if not all_pages:
            return None
        
        # 优先查找作业详情页（包含 /assignments/ 或 /quizzes/ 且后面还有路径）
        # 作业详情页的 URL 格式：/courses/123/assignments/456 或 /courses/123/quizzes/456
        # 列表页的 URL 格式：/courses/123/assignments 或 /courses/123/quizzes
        for pg in reversed(all_pages):
            if not pg.url.startswith('chrome://') and not pg.url.startswith('about:') and not pg.url.startswith('devtools://'):
                url = pg.url.rstrip('/')
                # 检查是否是 assignments 详情页
                if '/assignments/' in url:
                    # 排除 assignments 列表页（以 /assignments 结尾）
                    if url.endswith('/assignments'):
                        continue
                    # 找到作业详情页（/assignments/ 后面还有内容）
                    parts = url.split('/assignments/')
                    if len(parts) > 1 and parts[1]:  # 确保 /assignments/ 后面有内容
                        self.logger.info(f"找到作业详情页: {url}")
                        return pg
                # 检查是否是 quizzes 详情页
                if '/quizzes/' in url:
                    # 排除 quizzes 列表页（以 /quizzes 结尾）
                    if url.endswith('/quizzes'):
                        continue
                    # 找到 quizzes 详情页（/quizzes/ 后面还有内容）
                    parts = url.split('/quizzes/')
                    if len(parts) > 1 and parts[1]:  # 确保 /quizzes/ 后面有内容
                        self.logger.info(f"找到 quizzes 详情页（视为作业详情页）: {url}")
                        return pg
        
        # 如果没找到，查找所有非列表页的页面
        for pg in reversed(all_pages):
            if not pg.url.startswith('chrome://') and not pg.url.startswith('about:') and not pg.url.startswith('devtools://'):
                url = pg.url.rstrip('/')
                # 排除 assignments 和 quizzes 列表页
                if url.endswith('/assignments') or url.endswith('/quizzes'):
                    continue
                # 如果包含 /assignments 或 /quizzes 但不是列表页，可能是详情页
                if '/assignments' in url or '/quizzes' in url:
                    self.logger.info(f"找到可能的作业详情页: {url}")
                    return pg
        
        # 最后，返回最后一个非特殊且非列表页的页面（可能是当前页面导航到了作业详情页）
        for pg in reversed(all_pages):
            if not pg.url.startswith('chrome://') and not pg.url.startswith('about:') and not pg.url.startswith('devtools://'):
                url = pg.url.rstrip('/')
                # 跳过 assignments 和 quizzes 列表页
                if url.endswith('/assignments') or url.endswith('/quizzes'):
                    continue
                self.logger.info(f"使用最后一个非列表页: {url}")
                return pg
        
        return None
    
    async def click_all_elements(self, elements: list):
        """
        遍历点击所有作业元素的核心逻辑
        重写基类方法，使用自定义的页面查找逻辑
        
        Args:
            elements: 作业元素列表
        """
        if not elements:
            self.logger.warning("⚠️  没有可点击的作业")
            return
        
        # 从父级 HTML 文件路径推断 assignments 页面 URL
        # 或者从元素信息中获取（元素信息包含完整的作业 URL，可以推断出 assignments 页面 URL）
        assignments_page_url = None
        if elements and len(elements) > 0:
            # 从第一个元素的 URL 推断 assignments 页面 URL
            first_element = elements[0]
            assignment_url = first_element.get('url', '')
            if assignment_url:
                # 从作业详情页 URL 推断 assignments 列表页 URL
                # 例如：/courses/123/assignments/456 -> /courses/123/assignments
                if '/assignments/' in assignment_url:
                    assignments_page_url = assignment_url.split('/assignments/')[0] + '/assignments'
                    self.logger.info(f"推断的 assignments 页面 URL: {assignments_page_url}")
        
        self.logger.info(f"\n开始遍历点击 {len(elements)} 个作业...")
        self.logger.info("=" * 60)
        
        for i, element in enumerate(elements, 1):
            assignment_name = element.get('assignment_name', element.get('text', f'作业 {i}'))
            self.logger.info(f"\n[{i}/{len(elements)}] 正在点击作业: {assignment_name}")
            
            # 如果点击成功，等待页面导航完成并保存 HTML 和截图
            html_file = None
            screenshot_file = None
            
            # 使用点击器点击元素，并在点击后等待页面导航
            try:
                from playwright.async_api import async_playwright
                
                async with async_playwright() as p:
                    cdp_url = self._get_cdp_url()
                    browser = await p.chromium.connect_over_cdp(cdp_url)
                    
                    try:
                        # 找到 assignments 页面
                        all_pages = self._get_all_pages(browser)
                        assignments_page = None
                        if assignments_page_url:
                            for pg in all_pages:
                                if assignments_page_url in pg.url:
                                    assignments_page = pg
                                    break
                        
                        if not assignments_page:
                            # 如果没找到，使用第一个非特殊页面
                            for pg in all_pages:
                                if not pg.url.startswith('chrome://') and not pg.url.startswith('about:') and not pg.url.startswith('devtools://'):
                                    assignments_page = pg
                                    break
                        
                        if not assignments_page:
                            self.logger.warning("⚠️  未找到 assignments 页面")
                            continue
                        
                        self.logger.info(f"当前 assignments 页面: {assignments_page.url}")
                        
                        # 从元素信息中获取 section_aria_controls（从 assignment_extractor 提取的信息）
                        section_aria_controls = element.get('section_aria_controls', '')
                        if not section_aria_controls:
                            # 如果没有提供，尝试从第一个元素获取（假设所有元素都在同一个 section）
                            if i == 1 and elements:
                                section_aria_controls = elements[0].get('section_aria_controls', '')
                        
                        if section_aria_controls:
                            self.logger.info(f"定位到 section: {section_aria_controls}")
                            
                            # 确保 section 是展开的
                            # 查找对应的 button（通过 aria-controls 属性）
                            button_selector = f'button.element_toggler[aria-controls="{section_aria_controls}"]'
                            try:
                                button = await assignments_page.wait_for_selector(button_selector, timeout=5000, state='visible')
                                if button:
                                    # 检查 aria-expanded 属性
                                    aria_expanded = await button.get_attribute('aria-expanded')
                                    if aria_expanded != 'true':
                                        self.logger.info(f"展开 section: {section_aria_controls}")
                                        await button.click()
                                        await asyncio.sleep(0.5)  # 等待展开动画
                                    else:
                                        self.logger.info(f"Section {section_aria_controls} 已展开")
                            except Exception as e:
                                self.logger.warning(f"⚠️  无法找到或展开 section 按钮: {str(e)}")
                        
                        # 在指定的 section 下查找 ig-title 元素
                        # 如果提供了 section_aria_controls，则在该 section 下查找；否则在整个页面查找
                        if section_aria_controls:
                            # 在指定 section 容器下查找
                            section_selector = f'#{section_aria_controls} a.ig-title'
                            self.logger.info(f"在 section {section_aria_controls} 下查找作业链接: {section_selector}")
                        else:
                            # 在整个页面查找（向后兼容）
                            section_selector = 'a.ig-title'
                            self.logger.info(f"在整个页面查找作业链接: {section_selector}")
                        
                        # 等待元素出现
                        try:
                            await assignments_page.wait_for_selector(section_selector, timeout=10000, state='visible')
                        except Exception as e:
                            self.logger.error(f"❌ 等待元素超时: {section_selector} - {str(e)}")
                            continue
                        
                        # 获取所有匹配的元素，选择指定索引的元素
                        if section_aria_controls:
                            # 在指定 section 下查找
                            element_handle = await assignments_page.evaluate_handle(f'''
                                () => {{
                                    const section = document.getElementById('{section_aria_controls}');
                                    if (!section) {{
                                        return null;
                                    }}
                                    const elements = section.querySelectorAll('a.ig-title');
                                    if (elements.length === 0) {{
                                        return null;
                                    }}
                                    if ({i-1} >= elements.length) {{
                                        return null;
                                    }}
                                    return elements[{i-1}];
                                }}
                            ''')
                        else:
                            # 在整个页面查找
                            element_handle = await assignments_page.evaluate_handle(f'''
                                () => {{
                                    const elements = document.querySelectorAll('a.ig-title');
                                    if (elements.length === 0) {{
                                        return null;
                                    }}
                                    if ({i-1} >= elements.length) {{
                                        return null;
                                    }}
                                    return elements[{i-1}];
                                }}
                            ''')
                        
                        if not element_handle or await element_handle.evaluate('el => el === null'):
                            # 获取元素总数（用于错误信息）
                            if section_aria_controls:
                                total_count = await assignments_page.evaluate(f'''
                                    () => {{
                                        const section = document.getElementById('{section_aria_controls}');
                                        return section ? section.querySelectorAll('a.ig-title').length : 0;
                                    }}
                                ''')
                            else:
                                total_count = await assignments_page.evaluate(f'document.querySelectorAll("a.ig-title").length')
                            self.logger.error(f"❌ 未找到索引为 {i-1} 的元素（共找到 {total_count} 个元素）")
                            continue
                        
                        # 获取元素的 URL 和文本信息（用于日志）
                        element_url = await element_handle.evaluate('el => el.href || ""')
                        element_text = await element_handle.evaluate('el => el.textContent || ""')
                        self.logger.info(f"找到第 {i} 个作业链接: {element_text.strip()[:50]}...")
                        self.logger.info(f"   链接 URL: {element_url}")
                        
                        # 点击元素（等待导航）
                        assignment_url = element.get('url', '')
                        expected_url = element_url if element_url else assignment_url
                        self.logger.info(f"点击作业链接，等待导航到: {expected_url}")
                        
                        # 记录点击前的 URL
                        url_before_click = assignments_page.url
                        
                        # 点击元素
                        success = False
                        
                        # 验证导航后的 URL 是否包含 /assignments/ 且不是 assignments 列表页
                        def is_assignment_detail_url(url):
                            """检查 URL 是否是作业详情页（包括 assignments 和 quizzes）"""
                            if not url:
                                return False
                            url_clean = url.rstrip('/')
                            # 检查是否是 assignments 详情页：包含 /assignments/ 且后面有内容
                            if '/assignments/' in url_clean:
                                parts = url_clean.split('/assignments/')
                                if len(parts) > 1 and parts[1]:  # /assignments/ 后面有内容
                                    return True
                            # 检查是否是 quizzes 详情页：包含 /quizzes/ 且后面有内容
                            if '/quizzes/' in url_clean:
                                parts = url_clean.split('/quizzes/')
                                if len(parts) > 1 and parts[1]:  # /quizzes/ 后面有内容
                                    return True
                            return False
                        
                        try:
                            # 直接点击 ig-title 链接（它本身就是 <a> 标签）
                            async with assignments_page.expect_navigation(
                                url=lambda url: is_assignment_detail_url(url),
                                timeout=15000
                            ):
                                await element_handle.click()
                            
                            # 验证导航后的 URL
                            current_url = assignments_page.url
                            if is_assignment_detail_url(current_url):
                                self.logger.info(f"✅ 点击成功，已导航到作业详情页: {current_url}")
                                success = True
                            else:
                                self.logger.warning(f"⚠️  导航到了错误的页面: {current_url}")
                                success = False
                        except Exception as nav_error:
                            # 检查当前 URL 是否已经是作业详情页
                            current_url = assignments_page.url
                            if is_assignment_detail_url(current_url):
                                self.logger.info(f"✅ 页面已导航到作业详情页（超时但已到达）: {current_url}")
                                success = True
                            else:
                                self.logger.warning(f"⚠️  导航超时或失败: {str(nav_error)}")
                                self.logger.warning(f"   当前 URL: {current_url}")
                                self.logger.warning(f"   期望 URL: {expected_url}")
                                success = False
                        
                        if success:
                            # 等待页面加载完成
                            self.logger.info(f"等待作业详情页加载...")
                            await self._wait_for_page_load(assignments_page, timeout=10000, fallback_sleep=2)
                            
                            # 保存作业详情页
                            html_file, screenshot_file = await self.save_page_content(assignments_page, parent_html_file=self.parent_html_file)
                            
                            self.logger.info(f"✅ 作业 '{assignment_name}' 点击成功")
                        else:
                            self.logger.error(f"❌ 作业 '{assignment_name}' 点击失败，跳过保存")
                            html_file, screenshot_file = None, None
                        
                    finally:
                        await browser.close()
            except Exception as e:
                self.logger.warning(f"⚠️  点击或保存作业详情页时出错: {str(e)}")
                success = False
            
            # 执行点击后的操作（等待并返回）
            await self.after_click_action(i-1, element, success, html_file, screenshot_file)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"✅ 已完成所有 {len(elements)} 个作业的点击")

