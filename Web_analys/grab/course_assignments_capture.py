"""
课程 Assignments 捕获服务
从 dashboard HTML 中提取课程 URL，生成 assignments URL，并批量捕获
"""
import sys
import re
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse

# 添加 Web_analys 目录到路径
web_analys_dir = Path(__file__).parent.parent
if str(web_analys_dir) not in sys.path:
    sys.path.insert(0, str(web_analys_dir))

from BrowserManager.base_manager import BaseBrowserManager
from core.url_capture_service import URLCaptureService
from core.capture_result import CaptureResult
from grab.course_url_extractor import CourseURLExtractor


class CourseAssignmentsCapture:
    """课程 Assignments 捕获服务"""
    
    def __init__(
        self,
        browser_manager: BaseBrowserManager,
        output_dir: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化捕获服务
        
        Args:
            browser_manager: 浏览器管理器
            output_dir: 输出目录
            logger: 日志记录器
        """
        self.browser_manager = browser_manager
        self.output_dir = output_dir
        self.logger = logger or logging.getLogger("course_assignments_capture")
        
        # 创建 URL 捕获服务
        self.url_capture_service = URLCaptureService(
            browser_manager=browser_manager,
            output_dir=output_dir,
            logger=self.logger
        )
        
        # 创建课程 URL 提取器
        self.url_extractor = CourseURLExtractor(logger=self.logger)
    
    async def capture_from_dashboard_html(
        self,
        dashboard_html_file: str,
        base_url: Optional[str] = None
    ) -> List[CaptureResult]:
        """
        从 dashboard HTML 文件中提取课程 URL，生成 assignments URL，并批量捕获
        
        Args:
            dashboard_html_file: dashboard HTML 文件路径
            base_url: 基础 URL（如果不提供，会从 HTML 中提取）
            
        Returns:
            List[CaptureResult]: 捕获结果列表
        """
        try:
            # 步骤 1: 提取课程 URL
            self.logger.info("\n" + "=" * 60)
            self.logger.info("步骤 1: 从 dashboard HTML 中提取课程 URL")
            self.logger.info("=" * 60)
            
            # 提取课程 URL
            course_urls = self.url_extractor.extract_course_urls(dashboard_html_file)
            
            if not course_urls:
                self.logger.warning("⚠️  未提取到课程 URL")
                return []
            
            self.logger.info(f"✅ 提取到 {len(course_urls)} 个课程 URL:")
            for course_url in course_urls:
                self.logger.info(f"   - {course_url}")
            
            # 步骤 2: 生成 assignments URL
            self.logger.info("\n" + "=" * 60)
            self.logger.info("步骤 2: 生成 assignments URL")
            self.logger.info("=" * 60)
            
            # 提取基础 URL
            if not base_url:
                from bs4 import BeautifulSoup
                html_content = Path(dashboard_html_file).read_text(encoding='utf-8')
                soup = BeautifulSoup(html_content, 'html.parser')
                base_url = self.url_extractor._extract_base_url(
                    html_content,
                    soup
                )
            
            assignments_urls = self.url_extractor.generate_assignments_urls(
                course_urls,
                base_url
            )
            
            self.logger.info(f"✅ 生成了 {len(assignments_urls)} 个 assignments URL:")
            for url in assignments_urls:
                self.logger.info(f"   - {url}")
            
            # 步骤 3: 批量捕获 assignments 页面
            self.logger.info("\n" + "=" * 60)
            self.logger.info("步骤 3: 批量捕获 assignments 页面")
            self.logger.info("=" * 60)
            
            # 获取 dashboard HTML 文件的目录（作为父级目录）
            dashboard_path = Path(dashboard_html_file)
            dashboard_dir = dashboard_path.parent
            
            # 设置父级 HTML 文件路径（用于创建层级结构）
            parent_html_file = str(dashboard_path)
            
            results = []
            total = len(assignments_urls)
            
            for i, assignments_url in enumerate(assignments_urls, 1):
                try:
                    self.logger.info(f"\n[{i}/{total}] 捕获 assignments 页面: {assignments_url}")
                    
                    # 设置父级 HTML 文件路径（用于生成层级结构）
                    # 不使用课程名称，直接使用 URL 生成文件夹名
                    self.url_capture_service._parent_html_file = parent_html_file
                    self.url_capture_service._course_name = None
                    
                    # 捕获 URL
                    result = await self.url_capture_service.capture_url(assignments_url)
                    
                    # 清除父级 HTML 文件路径和课程名称
                    if hasattr(self.url_capture_service, '_parent_html_file'):
                        delattr(self.url_capture_service, '_parent_html_file')
                    if hasattr(self.url_capture_service, '_course_name'):
                        delattr(self.url_capture_service, '_course_name')
                    
                    if result:
                        results.append(result)
                        self.logger.info(f"✅ [{i}/{total}] 捕获成功: {result.html_file}")
                    else:
                        self.logger.error(f"❌ [{i}/{total}] 捕获失败")
                        
                except Exception as e:
                    self.logger.error(f"❌ [{i}/{total}] 捕获 assignments 页面时出错: {str(e)}", exc_info=True)
                    continue
            
            self.logger.info("\n" + "=" * 60)
            self.logger.info(f"✅ 批量捕获完成: 成功 {len(results)}/{total}")
            self.logger.info("=" * 60)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 从 dashboard HTML 捕获 assignments 页面时出错: {str(e)}", exc_info=True)
            return []

