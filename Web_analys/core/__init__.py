"""
Web_analys 核心模块
提供 URL 捕获和页面保存的核心功能
"""
from .url_capture_service import URLCaptureService
from .capture_result import CaptureResult
from .browser_session import BrowserSession
from .page_saver import PageSaver
from .exceptions import (
    WebAnalysError,
    BrowserNotRunningError,
    PageLoadError,
    SaveError
)

__all__ = [
    'URLCaptureService',
    'CaptureResult',
    'BrowserSession',
    'PageSaver',
    'WebAnalysError',
    'BrowserNotRunningError',
    'PageLoadError',
    'SaveError'
]

