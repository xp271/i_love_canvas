"""
课程入口点击器实现
继承 BaseElementLoop，实现具体的"等待 -> 返回"逻辑
点击后导航到 /assignments 页面并保存
"""
import asyncio
import sys
from pathlib import Path

# 添加 Classes 目录到路径（用于相对导入）
sys.path.insert(0, str(Path(__file__).parent))
from base_element_loop import BaseElementLoop

# 添加 Web_analys 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "Web_analys" / "grab"))
from assignment_extractor import AssignmentExtractor

# 导入 Assignment 类
from assignment import Assignment


class CoursesEntrance(BaseElementLoop):
    """课程入口点击器 - 实现具体的等待和返回逻辑"""
    
    def __init__(self, config: dict, wait_seconds: int = 10):
        """
        初始化点击器
        
        Args:
            config: 配置字典
            wait_seconds: 每次点击后等待的秒数
        """
        super().__init__(config)
        self.wait_seconds = wait_seconds
    
    async def _get_target_page_after_click(self, browser, original_url=None):
        """
        获取点击后的目标页面（课程页面，排除 dashboard）
        重写基类方法以自定义页面查找逻辑
        
        Args:
            browser: Playwright 浏览器对象
            original_url: 原始页面 URL（dashboard 页面，需要排除）
        
        Returns:
            Page 对象或 None
        """
        all_pages = self._get_all_pages(browser)
        
        if not all_pages:
            return None
        
        # 找到点击后导航到的页面（不是原始 dashboard 页面的那个）
        # 优先查找包含 /courses/ 的页面（课程页面），但排除 /assignments 和 /quizzes
        for pg in all_pages:
            # 跳过特殊页面（包括 chrome://, about:, devtools://）
            if pg.url.startswith('chrome://') or pg.url.startswith('about:') or pg.url.startswith('devtools://'):
                continue
            # 跳过原始 dashboard 页面
            if original_url and original_url in pg.url:
                continue
            # 跳过包含 /assignments 或 /quizzes 的页面（这些是子页面，不是课程主页）
            if '/assignments' in pg.url or '/quizzes' in pg.url:
                continue
            # 优先返回包含 /courses/ 的页面（课程页面）
            if '/courses/' in pg.url:
                self.logger.info(f"✅ 找到课程页面: {pg.url}")
                return pg
        
        # 如果没找到课程页面，返回第一个非 dashboard 且非特殊页面（排除 /assignments 和 /quizzes）
        for pg in all_pages:
            if pg.url.startswith('chrome://') or pg.url.startswith('about:') or pg.url.startswith('devtools://'):
                continue
            if original_url and original_url in pg.url:
                continue
            # 跳过包含 /assignments 或 /quizzes 的页面
            if '/assignments' in pg.url or '/quizzes' in pg.url:
                continue
            self.logger.info(f"✅ 找到非 dashboard 页面: {pg.url}")
            return pg
        
        # 最后，返回最后一个非特殊页面（排除 /assignments 和 /quizzes）
        for pg in reversed(all_pages):
            if not pg.url.startswith('chrome://') and not pg.url.startswith('about:') and not pg.url.startswith('devtools://'):
                # 跳过包含 /assignments 或 /quizzes 的页面
                if '/assignments' in pg.url or '/quizzes' in pg.url:
                    continue
                self.logger.info(f"✅ 使用最后一个非特殊页面: {pg.url}")
                return pg
        
        return None
    
    async def _navigate_to_assignments(self, page, parent_html_file: str = None):
        """
        导航到 assignments 页面并保存
        
        Args:
            page: 当前课程页面对象
            parent_html_file: 父级 HTML 文件路径（课程页面），用于创建层级结构
        
        Returns:
            tuple: (html_file, screenshot_file) 或 (None, None)
        """
        try:
            # 等待页面加载完成
            self.logger.info(f"等待点击后的页面加载...")
            await self._wait_for_page_load(page, timeout=10000, fallback_sleep=3)
            
            # 获取当前页面 URL，然后导航到 /assignments
            current_url = page.url
            assignments_url = current_url.rstrip('/') + '/assignments'
            
            self.logger.info(f"当前课程页面: {current_url}")
            self.logger.info(f"导航到作业页面: {assignments_url}")
            
            # 导航到 assignments 页面
            await page.goto(assignments_url, wait_until='networkidle', timeout=30000)
            
            # 等待页面加载
            await asyncio.sleep(2)
            
            # 保存 assignments 页面的 HTML 和截图（在父级目录下创建子文件夹）
            return await self.save_page_content(page, assignments_url, parent_html_file)
        except Exception as e:
            self.logger.warning(f"⚠️  导航到作业页面时出错: {str(e)}")
            return None, None
    
    async def click_all_elements(self, elements: list):
        """
        遍历点击所有元素的核心逻辑
        重写基类方法，实现点击后导航到 /assignments 页面
        
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
        
        # 记录原始页面 URL（dashboard 页面）
        original_url = page_url
        
        for i, element in enumerate(elements, 1):
            self.logger.info(f"\n[{i}/{len(elements)}] 正在点击第 {i} 个元素...")
            
            # 调用通用点击器点击元素（传入索引，从 0 开始）
            success = await self.clicker.click_element_by_info(element, page_url, element_index=i-1)
            
            if success:
                self.logger.info(f"✅ 第 {i} 个元素点击成功")
            else:
                self.logger.warning(f"⚠️  第 {i} 个元素点击失败")
            
            # 如果点击成功，导航到 /assignments 页面并保存 HTML 和截图
            html_file = None
            screenshot_file = None
            if success:
                try:
                    from playwright.async_api import async_playwright
                    
                    # 等待一下，确保点击后的页面已经打开
                    await asyncio.sleep(1)
                    
                    async with async_playwright() as p:
                        cdp_url = self._get_cdp_url()
                        browser = await p.chromium.connect_over_cdp(cdp_url)
                        
                        try:
                            # 使用自定义的页面查找逻辑（排除 dashboard）
                            target_page = await self._get_target_page_after_click(browser, original_url)
                            
                            if target_page:
                                self.logger.info(f"找到目标页面: {target_page.url}")
                                
                                # 先保存课程页面（作为父级）
                                course_html_file, course_screenshot_file = await self.save_page_content(target_page)
                                
                                # 导航到 assignments 并保存（在课程页面目录下）
                                html_file, screenshot_file = await self._navigate_to_assignments(target_page, course_html_file)
                            else:
                                self.logger.warning("⚠️  未找到点击后的新页面")
                                # 尝试获取所有页面用于调试
                                all_pages = self._get_all_pages(browser)
                                self.logger.info(f"当前所有页面数量: {len(all_pages)}")
                                for i, pg in enumerate(all_pages):
                                    self.logger.info(f"  页面 {i}: {pg.url}")
                        finally:
                            await browser.close()
                except Exception as e:
                    self.logger.warning(f"⚠️  导航到作业页面或保存内容时出错: {str(e)}")
            
            # 执行点击后的操作（由子类实现，传入保存的 HTML 和截图路径）
            await self.after_click_action(i-1, element, success, html_file, screenshot_file)
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info(f"✅ 已完成所有 {len(elements)} 个元素的点击")
    
    async def _process_assignments(self, html_file: str):
        """
        处理 assignments 页面的作业提取和点击
        
        Args:
            html_file: assignments 页面的 HTML 文件路径
        """
        try:
            self.logger.info("\n开始提取 'Past Assignments' 下的作业...")
            extractor = AssignmentExtractor(self.logger)
            assignments = extractor.extract_assignments_by_title(html_file, "Past Assignments")
            
            if assignments:
                self.logger.info(f"✅ 提取到 {len(assignments)} 个作业，开始点击...")
                
                # 创建 Assignment 点击器并执行点击（传递 assignments 页面路径作为父级）
                assignment_clicker = Assignment(self.config, wait_seconds=5, parent_html_file=html_file)
                assignment_clicker.logger = self.logger  # 传递 logger
                await assignment_clicker.click_all_elements(assignments)
                
                self.logger.info("✅ 已完成所有 'Past Assignments' 作业的点击")
            else:
                self.logger.info("⚠️  未找到 'Past Assignments' 下的作业")
        except Exception as e:
            self.logger.warning(f"⚠️  提取或点击作业时出错: {str(e)}")
    
    async def after_click_action(self, element_index: int, element: dict, click_success: bool, html_file: str = None, screenshot_file: str = None):
        """
        点击元素后执行的操作：根据新页面的 HTML 和截图执行操作，然后等待并返回
        
        Args:
            element_index: 元素索引（从 0 开始）
            element: 元素信息字典
            click_success: 点击是否成功
            html_file: 点击后新页面的 HTML 文件路径
            screenshot_file: 点击后新页面的截图文件路径
        """
        if html_file and screenshot_file:
            self.logger.info(f"   新页面 HTML: {html_file}")
            self.logger.info(f"   新页面截图: {screenshot_file}")
            
            # 从 assignments 页面提取并点击作业
            await self._process_assignments(html_file)
        
        # 所有元素点击后直接返回（包括最后一个）
        # 返回两次：从 assignments 回到课程页面，再从课程页面回到 dashboard
        self.logger.info("返回课程页面...")
        await self.go_back()
        await asyncio.sleep(1)
        
        self.logger.info("返回原始 dashboard 页面...")
        await self.go_back()
        
        # 等待页面加载
        await asyncio.sleep(2)

