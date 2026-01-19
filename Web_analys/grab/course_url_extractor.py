"""
课程 URL 提取器
从 dashboard HTML 中提取所有课程 URL，并生成 assignments URL
"""
import sys
import re
import logging
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


class CourseURLExtractor:
    """课程 URL 提取器"""
    
    def __init__(self, logger: logging.Logger = None):
        """
        初始化提取器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger("course_url_extractor")
    
    def extract_course_info(self, html_file: str) -> dict:
        """
        从 HTML 文件中提取课程信息（ID 到名称的映射）
        
        Args:
            html_file: HTML 文件路径
            
        Returns:
            dict: 课程信息字典，键为课程 ID（字符串），值为课程信息字典
                格式: {
                    "82537": {
                        "id": "82537",
                        "longName": "2025F CS 570-B - Introduction to Programming, Data Structures, and Algorithms",
                        "shortName": "2025F CS 570-B",
                        "href": "/courses/82537"
                    },
                    ...
                }
        """
        course_info_map = {}
        
        if not Path(html_file).exists():
            self.logger.error(f"❌ HTML 文件不存在: {html_file}")
            return course_info_map
        
        try:
            # 读取 HTML 文件
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 直接搜索 "originalName" 字段来提取课程信息
            # 匹配包含 originalName、id 和 href 的 JSON 对象
            import json
            
            # 搜索所有包含 originalName 的课程对象（字段顺序可能不同）
            # 使用更灵活的匹配，分别提取三个字段
            course_blocks = re.findall(r'\{[^{}]*(?:"originalName":"[^"]+")[^{}]*(?:"id":"\d+")[^{}]*(?:"href":"[^"]+")[^{}]*\}', html_content, re.DOTALL)
            
            for block in course_blocks:
                # 从块中分别提取 originalName、id 和 href
                original_name_match = re.search(r'"originalName":"([^"]+)"', block)
                id_match = re.search(r'"id":"(\d+)"', block)
                href_match = re.search(r'"href":"([^"]+)"', block)
                
                if original_name_match and id_match and href_match:
                    original_name = original_name_match.group(1)
                    course_id = id_match.group(1)
                    href = href_match.group(1)
                    
                    # 清理转义字符
                    try:
                        original_name = json.loads(f'"{original_name}"')
                    except:
                        original_name = original_name.replace('\\u0026', '&').replace('\\/', '/')
                    
                    # 直接存储 originalName，用作文件夹名
                    course_info_map[course_id] = original_name
                    self.logger.debug(f"提取课程: {course_id} -> {original_name} ({href})")
            
            self.logger.info(f"✅ 从 HTML 中提取到 {len(course_info_map)} 个课程信息")
            
            return course_info_map
            
        except Exception as e:
            self.logger.error(f"❌ 提取课程信息时出错: {str(e)}", exc_info=True)
            return course_info_map
    
    def extract_course_urls(self, html_file: str) -> List[str]:
        """
        从 HTML 文件中提取所有课程 URL
        
        Args:
            html_file: HTML 文件路径
            
        Returns:
            List[str]: 课程 URL 列表（如 /courses/123）
        """
        if not Path(html_file).exists():
            self.logger.error(f"❌ HTML 文件不存在: {html_file}")
            return []
        
        try:
            # 读取 HTML 文件
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 使用 BeautifulSoup 解析
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取基础 URL
            base_url = self._extract_base_url(html_content, soup)
            
            # 使用正则表达式提取所有 /courses/数字 的 URL
            course_urls: Set[str] = set()
            
            # 从 href 属性中提取
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                course_url = self._extract_course_url_from_href(href, base_url)
                if course_url:
                    course_urls.add(course_url)
            
            # 从 JavaScript 代码中提取（很多课程 URL 可能在 JS 数据中）
            js_pattern = r'/courses/(\d+)'
            matches = re.findall(js_pattern, html_content)
            for match in matches:
                course_url = f"/courses/{match}"
                course_urls.add(course_url)
            
            # 转换为列表并排序
            course_urls_list = sorted(list(course_urls))
            
            self.logger.info(f"✅ 从 HTML 中提取到 {len(course_urls_list)} 个课程 URL")
            
            return course_urls_list
            
        except Exception as e:
            self.logger.error(f"❌ 提取课程 URL 时出错: {str(e)}", exc_info=True)
            return []
    
    def _extract_base_url(self, html_content: str, soup: BeautifulSoup) -> str:
        """
        从 HTML 中提取基础 URL
        
        Args:
            html_content: HTML 内容
            soup: BeautifulSoup 对象
            
        Returns:
            str: 基础 URL（如 https://sit.instructure.com）
        """
        # 尝试从 <base> 标签获取
        base_tag = soup.find('base', href=True)
        if base_tag:
            base_href = base_tag['href']
            parsed = urlparse(base_href)
            return f"{parsed.scheme}://{parsed.netloc}"
        
        # 尝试从 ENV 变量中提取（Canvas 页面通常有）
        env_match = re.search(r'"DEEP_LINKING_POST_MESSAGE_ORIGIN":"([^"]+)"', html_content)
        if env_match:
            return env_match.group(1)
        
        # 尝试从其他链接中提取基础 URL
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.startswith('http://') or href.startswith('https://'):
                parsed = urlparse(href)
                return f"{parsed.scheme}://{parsed.netloc}"
        
        # 默认值
        return "https://sit.instructure.com"
    
    def _extract_course_url_from_href(self, href: str, base_url: str) -> str:
        """
        从 href 中提取课程 URL
        
        Args:
            href: 链接的 href 属性
            base_url: 基础 URL
            
        Returns:
            str: 课程 URL（如 /courses/123），如果没有则返回 None
        """
        if not href:
            return None
        
        # 如果是完整 URL，先解析
        if href.startswith('http://') or href.startswith('https://'):
            parsed = urlparse(href)
            path = parsed.path
        else:
            path = href
        
        # 匹配 /courses/数字 的模式
        match = re.match(r'/courses/(\d+)', path)
        if match:
            course_id = match.group(1)
            return f"/courses/{course_id}"
        
        return None
    
    def generate_assignments_urls(
        self, 
        course_urls: List[str], 
        base_url: str = "https://sit.instructure.com"
    ) -> List[str]:
        """
        生成 assignments URL 列表
        
        Args:
            course_urls: 课程 URL 列表（如 /courses/123）
            base_url: 基础 URL
            
        Returns:
            List[str]: assignments URL 列表（如 https://sit.instructure.com/courses/123/assignments）
        """
        assignments_urls = []
        
        for course_url in course_urls:
            # 清除后面的 /pages（如果有）
            clean_url = course_url.rstrip('/').rstrip('/pages')
            
            # 确保以 /courses/数字 结尾
            if not re.match(r'/courses/\d+$', clean_url):
                self.logger.warning(f"⚠️  跳过无效的课程 URL: {course_url}")
                continue
            
            # 加上 /assignments
            assignments_url = f"{clean_url}/assignments"
            
            # 构建完整 URL
            full_url = urljoin(base_url, assignments_url)
            assignments_urls.append(full_url)
        
        self.logger.info(f"✅ 生成了 {len(assignments_urls)} 个 assignments URL")
        
        return assignments_urls

