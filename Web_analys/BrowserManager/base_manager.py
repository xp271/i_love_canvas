"""
浏览器管理器基类
提供通用的浏览器管理接口，支持多种浏览器实现
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
import sys
import json
from pathlib import Path

# 添加 utils 目录到路径
utils_path = Path(__file__).parent.parent.parent / "utils"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))
from url_utils import is_target_url


class BaseBrowserManager(ABC):
    """浏览器管理器基类"""
    
    def __init__(self, config: Dict):
        """
        初始化浏览器管理器
        
        Args:
            config: 配置字典
        """
        self.config = config
        # 自动检测当前运行的浏览器进程
        self._detected_browser = self._auto_detect_running_browser()
    
    def _auto_detect_running_browser(self) -> Optional[Dict]:
        """
        自动检测当前运行的浏览器
        通过检查进程来找出哪个浏览器正在运行
        
        Returns:
            Optional[Dict]: 检测到的浏览器信息，包含 type、url 和 port，如果未检测到返回 None
        """
        import platform
        
        system = platform.system()
        detected_browsers = []
        
        # 加载浏览器配置
        browsers_config = self._load_browsers_config()
        
        # 检测每个浏览器（使用配置文件中的配置）
        for browser_config in browsers_config:
            browser_type = browser_config['type']
            process_name = browser_config['process_names'].get(system)
            
            if not process_name:
                continue
            
            # 检查进程是否运行
            if self._check_browser_process(process_name, system):
                # 获取端口配置
                port = (
                    self.config.get(browser_config['port_key']) or
                    self.config.get(browser_config.get('fallback_port_key')) or
                    browser_config['default_port']
                )
                
                detected_browsers.append({
                    'type': browser_type,
                    'url': f"http://localhost:{port}",
                    'port': port
                })
        
        # 返回第一个检测到的浏览器（如果有多个，优先返回第一个）
        return detected_browsers[0] if detected_browsers else None
    
    def _check_browser_process(self, process_name: str, system: str) -> bool:
        """
        检查指定浏览器进程是否在运行
        
        Args:
            process_name: 进程名称
            system: 操作系统类型（"Windows", "Darwin", "Linux"）
            
        Returns:
            bool: 如果进程正在运行返回 True
        """
        import subprocess
        
        try:
            if system == "Windows":
                result = subprocess.run(
                    ['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                    capture_output=True,
                    text=True
                )
                return process_name in result.stdout
            else:  # macOS 或 Linux
                result = subprocess.run(
                    ['pgrep', '-f', process_name],
                    capture_output=True
                )
                return result.returncode == 0
        except:
            return False
    
    def _load_browsers_config(self) -> List[Dict]:
        """
        从 JSON 文件加载浏览器配置
        
        Returns:
            List[Dict]: 浏览器配置列表
        """
        config_file = Path(__file__).parent / "browsers.json"
        
        if not config_file.exists():
            raise FileNotFoundError(f"浏览器配置文件不存在: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @abstractmethod
    def start(self) -> None:
        """
        启动浏览器并启用远程调试
        
        Raises:
            Exception: 启动失败时抛出异常
        """
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """
        检查浏览器是否在运行并启用了远程调试
        
        Returns:
            bool: 浏览器是否运行中
        """
        pass
    
    @abstractmethod
    def get_url(self) -> str:
        """
        获取浏览器远程调试 URL（CDP/Marionette 等）
        
        Returns:
            str: 远程调试 URL，格式如 "http://localhost:9222"
        """
        pass
    
    async def get_browser(self) -> Optional[Dict]:
        """
        检测哪个浏览器正在运行 config 里面的网页
        如果有多个就取第一个匹配的
        如果初始化时已检测到运行的浏览器，优先使用该浏览器
        
        Returns:
            Optional[Dict]: 浏览器信息字典，包含以下键：
                - type: 浏览器类型（如 "chrome", "firefox"）
                - url: 浏览器远程调试 URL
                - matched_pages: 匹配的页面 URL 列表
            如果没有找到匹配的浏览器，返回 None
        """
        # 如果初始化时已检测到浏览器，使用检测到的浏览器
        if self._detected_browser:
            browser_url = self._detected_browser['url']
            
            # 获取配置中的目标 URL
            target_urls = self.config.get('target_urls', [])
            if not target_urls:
                # 如果没有配置目标 URL，直接返回检测到的浏览器信息
                return {
                    'type': self._detected_browser['type'],
                    'url': browser_url,
                    'matched_pages': []
                }
            
            # 尝试连接浏览器并检查页面
            try:
                from playwright.async_api import async_playwright
                
                async with async_playwright() as p:
                    # 使用子类指定的连接方法连接浏览器
                    browser = await self._connect_browser(p, browser_url)
                    
                    if browser is None:
                        return None
                    
                    try:
                        # 获取所有页面
                        all_pages = []
                        for context in browser.contexts:
                            all_pages.extend(context.pages)
                        
                        # 检查哪些页面匹配目标 URL
                        matched_pages = []
                        for page in all_pages:
                            page_url = page.url
                            
                            # 跳过特殊页面
                            if page_url.startswith('chrome://') or \
                               page_url.startswith('about:') or \
                               page_url.startswith('devtools://'):
                                continue
                            
                            # 检查是否匹配目标 URL
                            if is_target_url(page_url, target_urls):
                                matched_pages.append(page_url)
                        
                        # 如果找到匹配的页面，返回浏览器信息
                        if matched_pages:
                            return {
                                'type': self._detected_browser['type'],
                                'url': browser_url,
                                'matched_pages': matched_pages
                            }
                        
                    finally:
                        await browser.close()
            
            except Exception:
                # 连接失败或检查出错，返回 None
                return None
        
        # 如果没有检测到浏览器，检查当前浏览器管理器管理的浏览器
        if not self.is_running():
            return None
        
        # 获取浏览器远程调试 URL
        browser_url = self.get_url()
        
        # 获取配置中的目标 URL
        target_urls = self.config.get('target_urls', [])
        if not target_urls:
            # 如果没有配置目标 URL，只要浏览器运行就返回
            return {
                'type': self._get_browser_type(),
                'url': browser_url,
                'matched_pages': []
            }
        
        # 尝试连接浏览器并检查页面
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                # 使用子类指定的连接方法连接浏览器
                browser = await self._connect_browser(p, browser_url)
                
                if browser is None:
                    return None
                
                try:
                    # 获取所有页面
                    all_pages = []
                    for context in browser.contexts:
                        all_pages.extend(context.pages)
                    
                    # 检查哪些页面匹配目标 URL
                    matched_pages = []
                    for page in all_pages:
                        page_url = page.url
                        
                        # 跳过特殊页面
                        if page_url.startswith('chrome://') or \
                           page_url.startswith('about:') or \
                           page_url.startswith('devtools://'):
                            continue
                        
                        # 检查是否匹配目标 URL
                        if is_target_url(page_url, target_urls):
                            matched_pages.append(page_url)
                    
                    # 如果找到匹配的页面，返回浏览器信息
                    if matched_pages:
                        return {
                            'type': self._get_browser_type(),
                            'url': browser_url,
                            'matched_pages': matched_pages
                        }
                    
                finally:
                    await browser.close()
        
        except Exception:
            # 连接失败或检查出错，返回 None
            return None
        
        # 没有找到匹配的页面
        return None
    
    @abstractmethod
    def _get_browser_type(self) -> str:
        """
        获取浏览器类型标识
        
        Returns:
            str: 浏览器类型，如 "chrome", "firefox", "edge"
        """
        pass
    
    @abstractmethod
    async def _connect_browser(self, playwright, browser_url: str):
        """
        连接到浏览器
        
        Args:
            playwright: Playwright 实例
            browser_url: 浏览器远程调试 URL
        
        Returns:
            浏览器对象，如果连接失败返回 None
        """
        pass

