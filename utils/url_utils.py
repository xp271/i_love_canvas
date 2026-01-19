"""
URL 工具函数
"""
from urllib.parse import urlparse
import re


def is_target_url(url: str, target_urls: list):
    """
    检查 URL 是否为目标 URL
    
    Args:
        url: 要检查的 URL
        target_urls: 目标 URL 列表
    
    Returns:
        bool: 如果 URL 匹配目标 URL 列表中的任何一个，返回 True
    """
    if not target_urls:
        return False
    
    for target in target_urls:
        if target in url or url in target:
            return True
    return False


def url_to_folder_name(url: str, max_length: int = 100):
    """
    将 URL 转换为安全的文件夹名称
    
    Args:
        url: 要转换的 URL
        max_length: 最大长度限制
    
    Returns:
        str: 安全的文件夹名称
    """
    try:
        parsed = urlparse(url)
        # 组合域名和路径
        if parsed.netloc:
            folder_name = parsed.netloc
            if parsed.path and parsed.path != '/':
                # 添加路径部分，但限制长度
                path_part = parsed.path.strip('/').replace('/', '_')
                folder_name = f"{folder_name}_{path_part}"
        else:
            # 如果没有域名，使用整个 URL
            folder_name = url
        
        # 移除协议前缀（如果存在）
        folder_name = folder_name.replace('https://', '').replace('http://', '')
        
        # 替换不安全的字符
        folder_name = re.sub(r'[<>:"|?*\x00-\x1f]', '_', folder_name)
        
        # 限制长度
        if len(folder_name) > max_length:
            folder_name = folder_name[:max_length]
        
        # 移除末尾的点或空格
        folder_name = folder_name.rstrip('. ')
        
        return folder_name if folder_name else 'unknown'
    except Exception:
        # 如果解析失败，使用简单的替换方法
        safe_name = url.replace("://", "_").replace("/", "_").replace(":", "_")
        safe_name = re.sub(r'[<>:"|?*\x00-\x1f]', '_', safe_name)
        if len(safe_name) > max_length:
            safe_name = safe_name[:max_length]
        return safe_name if safe_name else 'unknown'


def url_to_subfolder_name(url: str, max_length: int = 50):
    """
    从 URL 中提取路径的最后一部分作为子文件夹名称
    
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
                subfolder = re.sub(r'[<>:"|?*\x00-\x1f]', '_', subfolder)
                if len(subfolder) > max_length:
                    subfolder = subfolder[:max_length]
                return subfolder.rstrip('. ')
        
        # 如果没有路径，返回默认名称
        return 'page'
    except Exception:
        return 'page'

