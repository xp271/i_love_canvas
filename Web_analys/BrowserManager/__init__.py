"""
浏览器管理器模块
提供浏览器管理器的基类和具体实现
"""
from .base_manager import BaseBrowserManager
from .chrome_manager import ChromeManager
from .edge_manager import EdgeManager

__all__ = ['BaseBrowserManager', 'ChromeManager', 'EdgeManager']

