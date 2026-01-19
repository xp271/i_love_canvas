"""
网页抓取模块
"""
from .monitor import WebMonitor
from .chrome_manager import ChromeManager
from .page_capture import PageCapture
from .assignment_extractor import AssignmentExtractor

__all__ = ['WebMonitor', 'ChromeManager', 'PageCapture', 'AssignmentExtractor']

