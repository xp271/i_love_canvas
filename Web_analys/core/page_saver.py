"""
页面内容保存器
负责保存页面的 HTML 内容和截图
"""
import sys
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from playwright.async_api import Page
from urllib.parse import urlparse

# 添加 utils 目录到路径
utils_path = Path(__file__).parent.parent.parent / "utils"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

# 添加 Web_analys 目录到路径
web_analys_dir = Path(__file__).parent.parent
if str(web_analys_dir) not in sys.path:
    sys.path.insert(0, str(web_analys_dir))

from url_utils import url_to_folder_name, url_to_subfolder_name
from core.exceptions import SaveError


class PageSaver:
    """页面内容保存器"""
    
    def __init__(
        self,
        output_dir: str,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化页面保存器
        
        Args:
            output_dir: 输出目录
            logger: 日志记录器
        """
        self.output_dir = Path(output_dir)
        self.logger = logger or logging.getLogger("page_saver")
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_file_paths(
        self, 
        url: str, 
        timestamp: Optional[datetime] = None,
        parent_html_file: Optional[str] = None,
        course_name: Optional[str] = None
    ) -> tuple[str, str]:
        """
        生成 HTML 和截图文件路径
        
        Args:
            url: 页面 URL
            timestamp: 时间戳，如果为 None 则使用当前时间
            parent_html_file: 父级 HTML 文件路径（如果提供，则在父级目录下创建子文件夹，实现层级结构）
            course_name: 课程名称（如果提供，使用课程名称作为文件夹名，而不是 URL）
            
        Returns:
            (html_path, screenshot_path): HTML 和截图文件路径元组
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 生成文件名（基于时间戳）
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # 根据是否有父级文件决定保存路径
        if parent_html_file:
            # 层级结构：在父级文件的目录下创建子文件夹
            parent_path = Path(parent_html_file)
            parent_dir = parent_path.parent
            
            # 如果提供了课程名称，使用课程名称作为文件夹名
            if course_name:
                # 清理课程名称，移除非法字符
                safe_course_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', course_name)
                # 限制长度
                if len(safe_course_name) > 100:
                    safe_course_name = safe_course_name[:100]
                subfolder_name = safe_course_name
                self.logger.debug(f"使用课程名称作为文件夹名: {subfolder_name}")
            else:
                # 从 URL 提取子文件夹名称
                subfolder_name = url_to_subfolder_name(url)
                self.logger.debug(f"未提供课程名称，从 URL 提取文件夹名: {subfolder_name}")
                # 如果 URL 包含 /assignments，尝试从课程 URL 中提取课程 ID
                if '/assignments' in url:
                    parsed = urlparse(url)
                    # 尝试提取课程 ID（/courses/123/assignments -> course_123）
                    match = re.search(r'/courses/(\d+)/assignments', parsed.path)
                    if match:
                        course_id = match.group(1)
                        subfolder_name = f"course_{course_id}"
                        self.logger.debug(f"从 URL 提取课程 ID，使用文件夹名: {subfolder_name}")
            url_dir = parent_dir / subfolder_name
        else:
            # 扁平结构：根据 URL 或课程名称创建文件夹
            if course_name:
                safe_course_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', course_name)
                if len(safe_course_name) > 100:
                    safe_course_name = safe_course_name[:100]
                folder_name = safe_course_name
            else:
                folder_name = url_to_folder_name(url)
            url_dir = self.output_dir / folder_name
        
        url_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件路径
        html_path = url_dir / f"{timestamp_str}.html"
        screenshot_path = url_dir / f"{timestamp_str}.png"
        
        return str(html_path), str(screenshot_path)
    
    async def save_html(self, page: Page, html_path: str) -> str:
        """
        保存页面 HTML
        
        Args:
            page: Playwright Page 对象
            html_path: HTML 文件保存路径
            
        Returns:
            保存的 HTML 文件路径
            
        Raises:
            SaveError: 保存失败
        """
        try:
            # 获取 HTML 内容
            html_content = await page.content()
            
            # 保存到文件
            html_file = Path(html_path)
            html_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"✅ HTML 已保存: {html_path}")
            return str(html_path)
            
        except Exception as e:
            raise SaveError(html_path, f"保存 HTML 失败: {str(e)}") from e
    
    async def save_screenshot(
        self,
        page: Page,
        screenshot_path: str,
        full_page: bool = True
    ) -> str:
        """
        保存页面截图
        
        Args:
            page: Playwright Page 对象
            screenshot_path: 截图文件保存路径
            full_page: 是否截取整个页面
            
        Returns:
            保存的截图文件路径
            
        Raises:
            SaveError: 保存失败
        """
        try:
            # 确保目录存在
            screenshot_file = Path(screenshot_path)
            screenshot_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存截图
            await page.screenshot(path=str(screenshot_path), full_page=full_page)
            
            self.logger.info(f"✅ 截图已保存: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            raise SaveError(screenshot_path, f"保存截图失败: {str(e)}") from e

