"""
Assignment 详情捕获服务
从 assignments 页面的 HTML 中提取 assignment 详情链接，并批量捕获
"""
import sys
import re
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, urljoin

# 添加 Web_analys 目录到路径
web_analys_dir = Path(__file__).parent.parent
if str(web_analys_dir) not in sys.path:
    sys.path.insert(0, str(web_analys_dir))

from BrowserManager.base_manager import BaseBrowserManager
from core.url_capture_service import URLCaptureService
from core.capture_result import CaptureResult
from bs4 import BeautifulSoup


class AssignmentDetailCapture:
    """Assignment 详情捕获服务"""
    
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
        self.output_dir = Path(output_dir)
        self.logger = logger or logging.getLogger(__name__)
        
        # 创建 URL 捕获服务
        self.url_capture_service = URLCaptureService(
            browser_manager=browser_manager,
            output_dir=str(output_dir),
            logger=self.logger
        )
    
    def extract_assignment_urls(self, assignments_html_file: str) -> List[str]:
        """
        从 assignments HTML 文件中提取所有 assignment 详情 URL
        
        Args:
            assignments_html_file: assignments HTML 文件路径
            
        Returns:
            List[str]: assignment URL 列表（如 /courses/83845/assignments/649005）
        """
        if not Path(assignments_html_file).exists():
            self.logger.error(f"❌ HTML 文件不存在: {assignments_html_file}")
            return []
        
        try:
            # 读取 HTML 文件
            with open(assignments_html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 使用 BeautifulSoup 解析
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 只查找 assignment_group_upcoming_assignments 分组
            assignment_group = soup.find('div', id='assignment_group_upcoming_assignments')
            if not assignment_group:
                self.logger.warning("⚠️  未找到 assignment_group_upcoming_assignments 分组")
                return []
            
            self.logger.debug("✅ 找到 assignment_group_upcoming_assignments 分组")
            
            # 提取基础 URL
            base_url = None
            # 从第一个链接中提取基础 URL
            first_link = assignment_group.find('a', href=True)
            if first_link:
                href = first_link.get('href', '')
                if href.startswith('http'):
                    parsed = urlparse(href)
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # 如果没有找到，尝试从 HTML 中提取
            if not base_url:
                # 尝试从 <base> 标签或第一个链接中提取
                base_tag = soup.find('base', href=True)
                if base_tag:
                    base_url = base_tag.get('href')
                else:
                    # 从整个 HTML 的链接中提取基础 URL（作为备用）
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link.get('href', '')
                        if href.startswith('http'):
                            parsed = urlparse(href)
                            base_url = f"{parsed.scheme}://{parsed.netloc}"
                            break
            
            # 只在 assignment_group_upcoming_assignments 分组下查找所有链接
            assignment_urls = set()
            assignment_pattern = r'/courses/(\d+)/assignments/(\d+)'
            
            # 只在这个分组内查找链接
            for link in assignment_group.find_all('a', href=True):
                href = link.get('href', '')
                
                # 匹配 /courses/数字/assignments/数字 格式
                match = re.search(assignment_pattern, href)
                if match:
                    course_id = match.group(1)
                    assignment_id = match.group(2)
                    
                    # 如果是相对路径，构建完整 URL
                    if href.startswith('/'):
                        if base_url:
                            full_url = urljoin(base_url, href)
                        else:
                            full_url = href
                    elif not href.startswith('http'):
                        if base_url:
                            full_url = urljoin(base_url, href)
                        else:
                            continue
                    else:
                        full_url = href
                    
                    assignment_urls.add(full_url)
                    self.logger.debug(f"从 assignment_group_upcoming_assignments 提取到 URL: {full_url}")
            
            # 也使用正则表达式在整个分组内容中搜索（确保不遗漏）
            assignment_group_content = str(assignment_group)
            matches = re.findall(assignment_pattern, assignment_group_content)
            for match in matches:
                course_id = match[0]
                assignment_id = match[1]
                if base_url:
                    assignment_url = f"{base_url}/courses/{course_id}/assignments/{assignment_id}"
                else:
                    assignment_url = f"/courses/{course_id}/assignments/{assignment_id}"
                assignment_urls.add(assignment_url)
                self.logger.debug(f"从分组内容中提取到 URL: {assignment_url}")
            
            assignment_urls_list = sorted(list(assignment_urls))
            self.logger.info(f"✅ 从 HTML 中提取到 {len(assignment_urls_list)} 个 assignment URL")
            
            return assignment_urls_list
            
        except Exception as e:
            self.logger.error(f"❌ 提取 assignment URL 时出错: {str(e)}", exc_info=True)
            return []
    
    async def capture_from_assignments_html(
        self,
        assignments_html_file: str
    ) -> List[CaptureResult]:
        """
        从 assignments HTML 文件中提取 assignment 详情 URL，并批量捕获
        
        Args:
            assignments_html_file: assignments HTML 文件路径
            
        Returns:
            List[CaptureResult]: 捕获结果列表
        """
        try:
            # 步骤 1: 提取 assignment 详情 URL
            self.logger.info("\n" + "=" * 60)
            self.logger.info("步骤 1: 从 assignments HTML 中提取 assignment 详情 URL")
            self.logger.info("=" * 60)
            
            assignment_urls = self.extract_assignment_urls(assignments_html_file)
            
            if not assignment_urls:
                self.logger.warning("⚠️  未提取到 assignment URL")
                return []
            
            self.logger.info(f"✅ 提取到 {len(assignment_urls)} 个 assignment URL:")
            for url in assignment_urls:
                self.logger.info(f"   - {url}")
            
            # 步骤 2: 批量捕获 assignment 详情页面
            self.logger.info("\n" + "=" * 60)
            self.logger.info("步骤 2: 批量捕获 assignment 详情页面")
            self.logger.info("=" * 60)
            
            # 获取 assignments HTML 文件的目录（作为父级目录）
            assignments_path = Path(assignments_html_file)
            assignments_dir = assignments_path.parent
            
            # 设置父级 HTML 文件路径（用于创建层级结构）
            parent_html_file = str(assignments_path)
            
            results = []
            total = len(assignment_urls)
            
            for i, assignment_url in enumerate(assignment_urls, 1):
                try:
                    # 从 URL 中提取 assignment ID，用作文件夹名
                    match = re.search(r'/assignments/(\d+)$', assignment_url)
                    if match:
                        assignment_id = match.group(1)
                        self.logger.info(f"\n[{i}/{total}] 捕获 assignment 详情: {assignment_url}")
                        self.logger.debug(f"    Assignment ID: {assignment_id}")
                    else:
                        self.logger.warning(f"\n[{i}/{total}] 无法从 URL 提取 assignment ID: {assignment_url}")
                    
                    # 设置父级 HTML 文件路径（用于生成层级结构）
                    # 使用 assignment ID 作为子文件夹名
                    self.url_capture_service._parent_html_file = parent_html_file
                    # 使用 assignment ID 作为文件夹名
                    self.url_capture_service._course_name = assignment_id if match else None
                    
                    # 捕获 URL
                    result = await self.url_capture_service.capture_url(assignment_url)
                    
                    # 清除父级 HTML 文件路径和文件夹名
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
                    self.logger.error(f"❌ [{i}/{total}] 捕获 assignment 详情时出错: {str(e)}", exc_info=True)
            
            self.logger.info(f"\n✅ 完成！共捕获 {len(results)}/{total} 个 assignment 详情页面")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 捕获过程中出错: {str(e)}", exc_info=True)
            return []
    
    async def capture_all_from_output_dir(
        self,
        output_dir: str,
        pattern: str = "**/course_*/**/*.html"
    ) -> List[CaptureResult]:
        """
        从输出目录中查找所有 assignments HTML 文件，并批量捕获 assignment 详情
        
        Args:
            output_dir: 输出目录路径
            pattern: 文件匹配模式，默认查找所有 course_* 文件夹下的 HTML 文件
            
        Returns:
            List[CaptureResult]: 所有捕获结果列表
        """
        output_path = Path(output_dir)
        if not output_path.exists():
            self.logger.error(f"❌ 输出目录不存在: {output_dir}")
            return []
        
        # 查找所有可能的 assignments HTML 文件
        # 查找 course_* 文件夹下的所有 HTML 文件
        html_files = list(output_path.glob(pattern))
        
        # 过滤出 assignments 页面（包含 assignment_group_upcoming_assignments）
        assignments_files = []
        for html_file in html_files:
            try:
                content = html_file.read_text(encoding='utf-8')
                if 'assignment_group_upcoming_assignments' in content:
                    assignments_files.append(html_file)
                    self.logger.debug(f"找到 assignments 文件: {html_file}")
            except Exception as e:
                self.logger.warning(f"⚠️  读取文件失败: {html_file}, {str(e)}")
        
        if not assignments_files:
            self.logger.warning("⚠️  未找到任何 assignments HTML 文件")
            return []
        
        self.logger.info(f"✅ 找到 {len(assignments_files)} 个 assignments HTML 文件")
        
        # 批量处理每个 assignments 文件
        all_results = []
        for assignments_file in assignments_files:
            self.logger.info(f"\n处理文件: {assignments_file}")
            results = await self.capture_from_assignments_html(str(assignments_file))
            all_results.extend(results)
        
        return all_results

