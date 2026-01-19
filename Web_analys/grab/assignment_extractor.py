"""
作业提取器
从 assignments 页面中提取指定标题下的所有作业详情页链接
"""
import logging
from pathlib import Path
from bs4 import BeautifulSoup


class AssignmentExtractor:
    """作业提取器"""
    
    def __init__(self, logger=None):
        """
        初始化作业提取器
        
        Args:
            logger: 日志记录器，如果为 None 则创建默认 logger
        """
        self.logger = logger or logging.getLogger("web_monitor")
    
    def extract_assignments_by_title(self, html_file: str, section_title: str):
        """
        从 HTML 文件中提取指定标题下的所有作业详情页链接
        通过查找包含指定标题的 button（如 "Past Assignments"），然后在该 button 控制的 section 下查找所有 ig-title 链接
        
        Args:
            html_file: HTML 文件路径
            section_title: 要提取的作业组标题（如 "Past Assignments", "Undated Assignments"）
        
        Returns:
            list: 包含作业链接信息的列表，每个元素是一个字典，包含：
                - url: 作业详情页 URL
                - assignment_name: 作业名称
                - section_aria_controls: section 的 aria-controls 属性值（用于在浏览器中定位）
                - text: 链接文本
        """
        if not Path(html_file).exists():
            self.logger.error(f"❌ HTML 文件不存在: {html_file}")
            return []
        
        try:
            # 读取 HTML 文件
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找包含指定标题的 button（element_toggler）
            # 例如：<button class="element_toggler accessible-toggler" aria-controls="assignment_group_past_assignments"...>Past Assignments</button>
            section_button = None
            for button in soup.find_all('button', class_='element_toggler'):
                text = button.get_text(strip=True)
                if section_title.lower() in text.lower():
                    section_button = button
                    break
            
            if not section_button:
                self.logger.warning(f"⚠️  未找到标题为 '{section_title}' 的按钮")
                return []
            
            # 获取 button 的 aria-controls 属性（用于在浏览器中定位对应的 section）
            aria_controls = section_button.get('aria-controls', '')
            if not aria_controls:
                self.logger.warning(f"⚠️  按钮没有 aria-controls 属性")
                return []
            
            self.logger.info(f"找到 '{section_title}' 按钮，aria-controls: {aria_controls}")
            
            # 通过 aria-controls 找到对应的容器（通过 ID）
            section_container = soup.find('div', id=aria_controls)
            if not section_container:
                # 如果没找到，尝试查找 assignment-list
                section_container = soup.find('div', class_='assignment-list', id=lambda x: x and aria_controls in str(x))
            
            if not section_container:
                # 如果还是没找到，尝试向上查找 assignment_group
                current = section_button.parent
                while current:
                    if current.name == 'div' and 'assignment_group' in current.get('class', []):
                        # 在 assignment_group 中查找 assignment-list
                        section_container = current.find('div', class_='assignment-list')
                        if section_container:
                            break
                    current = current.parent
            
            if not section_container:
                self.logger.warning(f"⚠️  未找到 '{section_title}' 对应的作业列表容器")
                return []
            
            # 在该容器中查找所有 .ig-title 链接
            links = section_container.find_all('a', class_='ig-title')
            
            assignment_links = []
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href:
                    # 构建完整 URL（如果是相对路径）
                    if href.startswith('http://') or href.startswith('https://'):
                        full_url = href
                    elif href.startswith('/'):
                        # 从 HTML 中提取基础 URL
                        base_url = 'https://sit.instructure.com'
                        base_tag = soup.find('base', href=True)
                        if base_tag:
                            base_url = base_tag['href'].rstrip('/')
                        full_url = base_url + href
                    else:
                        # 相对路径
                        base_url = 'https://sit.instructure.com'
                        full_url = base_url + '/' + href.lstrip('/')
                    
                    assignment_info = {
                        'url': full_url,
                        'assignment_name': text,
                        'section_aria_controls': aria_controls,  # 用于在浏览器中定位 section
                        'text': text,
                        'tag': 'a',
                        'class': ['ig-title'],
                        'attributes': {
                            'href': full_url,
                            'class': 'ig-title',
                        },
                        'html': str(link)
                    }
                    assignment_links.append(assignment_info)
            
            self.logger.info(f"✅ 从 '{section_title}' 中提取到 {len(assignment_links)} 个作业链接")
            
            return assignment_links
            
        except Exception as e:
            self.logger.error(f"❌ 提取作业链接时出错: {str(e)}")
            return []

