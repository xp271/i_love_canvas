"""
URL 工具函数
提供 URL 处理、匹配和转换的工具函数
"""
import re
from urllib.parse import urlparse, urlunparse
from typing import List, Union


def is_target_url(url: str, target_urls: Union[str, List[str]]) -> bool:
    """
    检查 URL 是否匹配目标 URL 列表
    
    Args:
        url: 要检查的 URL
        target_urls: 目标 URL 或目标 URL 列表
        
    Returns:
        bool: 如果 URL 匹配目标 URL，返回 True，否则返回 False
    """
    if not url or not target_urls:
        return False
    
    # 将单个字符串转换为列表
    if isinstance(target_urls, str):
        target_urls = [target_urls]
    
    # 解析目标 URL
    parsed_url = urlparse(url)
    
    for target_url in target_urls:
        if not target_url:
            continue
        
        parsed_target = urlparse(target_url)
        
        # 比较域名和路径
        # 如果目标 URL 是根路径，匹配所有该域名的页面
        if parsed_target.path == '/' or parsed_target.path == '':
            if parsed_url.netloc == parsed_target.netloc:
                return True
        # 否则检查 URL 是否以目标 URL 开头
        else:
            # 检查域名是否相同
            if parsed_url.netloc != parsed_target.netloc:
                continue
            
            # 检查路径是否以目标路径开头
            target_path = parsed_target.path.rstrip('/')
            url_path = parsed_url.path.rstrip('/')
            
            if url_path.startswith(target_path):
                return True
    
    return False


def url_to_folder_name(url: str, max_length: int = 100) -> str:
    """
    从 URL 中提取文件夹名称
    
    Args:
        url: 要转换的 URL
        max_length: 最大长度限制
        
    Returns:
        str: 文件夹名称
    """
    try:
        parsed = urlparse(url)
        
        # 使用域名和路径作为文件夹名
        folder_parts = []
        
        # 添加域名
        if parsed.netloc:
            # 移除 www. 前缀
            netloc = parsed.netloc.replace('www.', '')
            folder_parts.append(netloc)
        
        # 添加路径的主要部分（如果有）
        if parsed.path and parsed.path != '/':
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            if path_parts:
                # 只使用路径的前几个部分，避免太长
                folder_parts.extend(path_parts[:2])
        
        if folder_parts:
            folder_name = '_'.join(folder_parts)
        else:
            folder_name = 'page'
        
        # 清理非法字符
        folder_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', folder_name)
        
        # 限制长度
        if len(folder_name) > max_length:
            folder_name = folder_name[:max_length]
        
        return folder_name.rstrip('_')
        
    except Exception:
        return 'page'


def url_to_subfolder_name(url: str, max_length: int = 50) -> str:
    """
    从 URL 中提取子文件夹名称
    
    Args:
        url: 要转换的 URL
        max_length: 最大长度限制
        
    Returns:
        str: 子文件夹名称
    """
    try:
        parsed = urlparse(url)
        if parsed.path and parsed.path != '/':
            # 获取路径的所有部分
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            if path_parts:
                # 根据路径结构决定子文件夹名
                if len(path_parts) == 1:
                    # 单一部分，直接使用
                    subfolder = path_parts[0]
                elif len(path_parts) == 2:
                    # 两部分，如 courses/123，使用第二部分
                    subfolder = path_parts[1]
                elif len(path_parts) >= 3:
                    # 三部分或更多，如 courses/123/assignments 或 courses/123/assignments/456
                    # 使用最后一部分，如果是数字则加上前缀
                    last_part = path_parts[-1]
                    second_last = path_parts[-2] if len(path_parts) >= 2 else None
                    
                    # 如果最后一部分是数字，且前一部分是 assignments，使用 assignment_数字
                    if last_part.isdigit() and second_last == 'assignments':
                        subfolder = f"assignment_{last_part}"
                    # 如果最后一部分是 assignments，使用 assignments
                    elif last_part == 'assignments':
                        subfolder = 'assignments'
                    # 否则使用最后一部分
                    else:
                        subfolder = last_part
                else:
                    subfolder = path_parts[-1]
                
                # 清理和限制长度
                subfolder = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', subfolder)
                if len(subfolder) > max_length:
                    subfolder = subfolder[:max_length]
                return subfolder.rstrip('_ ')
        
        # 如果没有路径，返回默认名称
        return 'page'
    except Exception:
        return 'page'

