"""
捕获结果数据类
封装页面捕获的结果信息
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CaptureResult:
    """捕获结果数据类"""
    url: str
    html_file: str
    screenshot_file: str
    timestamp: datetime
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保 timestamp 是 datetime 类型
        if isinstance(self.timestamp, str):
            # 如果是字符串，尝试解析
            try:
                self.timestamp = datetime.fromisoformat(self.timestamp)
            except (ValueError, AttributeError):
                self.timestamp = datetime.now()
        elif not isinstance(self.timestamp, datetime):
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        """
        转换为字典
        
        Returns:
            dict: 结果字典
        """
        return {
            'url': self.url,
            'html_file': self.html_file,
            'screenshot_file': self.screenshot_file,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"CaptureResult(\n"
            f"  url: {self.url}\n"
            f"  html_file: {self.html_file}\n"
            f"  screenshot_file: {self.screenshot_file}\n"
            f"  timestamp: {self.timestamp}\n"
            f")"
        )

