"""
自定义异常类
定义 Web_analys 模块使用的异常类型
"""


class WebAnalysError(Exception):
    """Web_analys 基础异常类"""
    pass


class BrowserNotRunningError(WebAnalysError):
    """浏览器未运行异常"""
    
    def __init__(self, message: str = "浏览器未运行"):
        super().__init__(message)
        self.message = message


class PageLoadError(WebAnalysError):
    """页面加载失败异常"""
    
    def __init__(self, url: str, message: str = None):
        if message is None:
            message = f"页面加载失败: {url}"
        super().__init__(message)
        self.url = url
        self.message = message


class SaveError(WebAnalysError):
    """保存失败异常"""
    
    def __init__(self, file_path: str, message: str = None):
        if message is None:
            message = f"保存文件失败: {file_path}"
        super().__init__(message)
        self.file_path = file_path
        self.message = message

