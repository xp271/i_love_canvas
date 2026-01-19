"""
Chrome 浏览器管理器
继承自 BaseBrowserManager，实现 Chrome 特定的启动和管理逻辑
"""
import subprocess
import time
import os
import platform
from pathlib import Path
import requests
from typing import Dict, Optional
from .base_manager import BaseBrowserManager


class ChromeManager(BaseBrowserManager):
    """Chrome 浏览器管理器"""
    
    def __init__(self, config: Dict):
        """
        初始化 Chrome 管理器
        
        Args:
            config: 配置字典，包含 chrome_debug_port 和 chrome_user_data_dir
        """
        super().__init__(config)
        self.chrome_path = self._get_chrome_path()
    
    def _get_chrome_path(self) -> str:
        """
        获取 Chrome 浏览器路径（跨平台）
        优先使用配置文件中的路径，如果未配置则自动检测
        
        Returns:
            str: Chrome 可执行文件路径
        """
        # 优先使用配置文件中的路径
        configured_path = self.config.get('chrome_path')
        if configured_path:
            # 展开用户目录路径（如 ~）
            expanded_path = os.path.expanduser(configured_path)
            if Path(expanded_path).exists():
                return expanded_path
            else:
                # 如果配置的路径不存在，抛出警告但继续自动检测
                print(f"⚠️  配置的 Chrome 路径不存在: {configured_path}，将尝试自动检测")
        
        # 自动检测 Chrome 路径
        system = platform.system()
        
        if system == "Windows":
            # Windows 常见路径
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
            ]
            for path in possible_paths:
                if Path(path).exists():
                    return path
        elif system == "Darwin":  # macOS
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            if Path(chrome_path).exists():
                return chrome_path
        else:  # Linux
            possible_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser"
            ]
            for path in possible_paths:
                if Path(path).exists():
                    return path
        
        # 如果所有路径都找不到，抛出异常
        raise Exception(f"未找到 Chrome 浏览器。请确保已安装 Chrome 或在配置文件中指定 chrome_path。")
    
    def is_running(self, port: Optional[int] = None) -> bool:
        """
        检查 Chrome 是否在运行并启用了远程调试
        
        Args:
            port: 调试端口，如果为 None 则从配置读取
        
        Returns:
            bool: Chrome 是否运行中
        """
        if port is None:
            port = self.config.get('chrome_debug_port', 9222)
        
        try:
            response = requests.get(f"http://localhost:{port}/json", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start(self) -> None:
        """
        启动 Chrome 并启用远程调试
        
        Raises:
            Exception: 启动失败时抛出异常
        """
        if not Path(self.chrome_path).exists():
            raise Exception(f"未找到 Chrome 浏览器: {self.chrome_path}")
        
        port = self.config.get('chrome_debug_port', 9222)
        # 根据操作系统设置默认的用户数据目录
        system = platform.system()
        if system == "Windows":
            default_user_data_dir = os.path.expanduser(r"~\AppData\Local\Temp\chrome-debug-profile")
        elif system == "Darwin":  # macOS
            default_user_data_dir = "/tmp/chrome-debug-profile"
        else:  # Linux
            default_user_data_dir = "/tmp/chrome-debug-profile"
        user_data_dir = self.config.get('chrome_user_data_dir', default_user_data_dir)
        
        # 检查是否已经在运行并启用了远程调试
        if self.is_running(port):
            print(f"✅ Chrome 已运行，远程调试端口 {port} 已启用")
            return
        
        # 检查 Chrome 进程是否在运行（不管是否启用远程调试）
        system = platform.system()
        
        if system == "Windows":
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq chrome.exe'],
                    capture_output=True,
                    text=True
                )
                chrome_process_running = 'chrome.exe' in result.stdout
            except:
                chrome_process_running = False
        elif system == "Darwin":  # macOS
            try:
                result = subprocess.run(['pgrep', '-f', 'Google Chrome'], 
                                      capture_output=True)
                chrome_process_running = result.returncode == 0
            except:
                chrome_process_running = False
        else:  # Linux
            try:
                result = subprocess.run(['pgrep', '-f', 'google-chrome'], 
                                      capture_output=True)
                chrome_process_running = result.returncode == 0
            except:
                chrome_process_running = False
        
        # 如果 Chrome 正在运行但没有启用远程调试，不关闭它，直接启动新的带远程调试的实例
        if chrome_process_running:
            print(f"⚠️  检测到 Chrome 正在运行，但未启用远程调试")
            print(f"   将启动一个新的带远程调试的 Chrome 实例（不关闭现有窗口）")
        
        # 启动新的 Chrome 实例（带远程调试）
        print(f"正在启动 Chrome（远程调试端口: {port}）...")
        
        # 构建启动命令
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(
                [self.chrome_path, 
                 f'--remote-debugging-port={port}', 
                 f'--user-data-dir={user_data_dir}'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
        else:
            subprocess.Popen(
                [self.chrome_path, f'--remote-debugging-port={port}', 
                 f'--user-data-dir={user_data_dir}'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        # 等待 Chrome 启动
        for i in range(10):
            time.sleep(1)
            if self.is_running(port):
                print(f"✅ Chrome 已成功启动，远程调试已启用（端口: {port}）")
                return
        
        raise Exception("Chrome 启动失败或远程调试未启用")
    
    def get_url(self) -> str:
        """
        获取 Chrome DevTools Protocol URL
        
        Returns:
            str: CDP URL，格式如 "http://localhost:9222"
        """
        port = self.config.get('chrome_debug_port', 9222)
        return f"http://localhost:{port}"
    
    def _get_browser_type(self) -> str:
        """获取浏览器类型标识"""
        return "chrome"
    
    async def _connect_browser(self, playwright, browser_url: str):
        """
        连接到 Chrome 浏览器
        
        Args:
            playwright: Playwright 实例
            browser_url: Chrome DevTools Protocol URL
        
        Returns:
            浏览器对象，如果连接失败返回 None
        """
        try:
            browser = await playwright.chromium.connect_over_cdp(browser_url)
            return browser
        except Exception:
            return None
    
    # 保持向后兼容的别名方法
    def start_chrome_with_debug(self) -> None:
        """启动 Chrome 并启用远程调试（向后兼容方法）"""
        return self.start()
    
    def is_chrome_running_with_debug(self, port: Optional[int] = None) -> bool:
        """检查 Chrome 是否在运行并启用了远程调试（向后兼容方法）"""
        return self.is_running(port)
    
    def get_cdp_url(self) -> str:
        """获取 Chrome DevTools Protocol URL（向后兼容方法）"""
        return self.get_url()

