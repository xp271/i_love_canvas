"""
网页抓取模块
"""
from .monitor import WebMonitor
from .chrome_manager import ChromeManager
from .page_capture import PageCapture

__all__ = ['WebMonitor', 'ChromeManager', 'PageCapture']

