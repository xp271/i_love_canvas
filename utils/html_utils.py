"""
HTML 处理工具函数
"""
import re
from bs4 import BeautifulSoup


def extract_hero_elements(html_content: str, logger=None):
    """
    从 HTML 内容中提取类别为 DashboardCard__header_hero 的元素
    
    Args:
        html_content: HTML 内容字符串
        logger: 可选的日志记录器
    
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
                bg_match = re.search(r'background-color:\s*([^;]+)', style)
                if bg_match:
                    element_info['background_color'] = bg_match.group(1).strip()
            
            hero_elements.append(element_info)
    except Exception as e:
        if logger:
            logger.error(f"⚠️  提取 hero 元素时出错: {str(e)}")
    
    return hero_elements

