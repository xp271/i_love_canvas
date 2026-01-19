"""
Edge 浏览器管理器
继承自 BaseBrowserManager，实现 Edge 特定的启动和管理逻辑
"""
import subprocess
import time
import os
import platform
from pathlib import Path
import requests
from typing import Dict, Optional
from .base_manager import BaseBrowserManager


class EdgeManager(BaseBrowserManager):
    """Edge 浏览器管理器"""
    
    def __init__(self, config: Dict):
        """
        初始化 Edge 管理器
        
        Args:
            config: 配置字典，包含 edge_debug_port 和 edge_user_data_dir
                   如果未配置，会回退到 chrome_debug_port 和 chrome_user_data_dir
        """
        super().__init__(config)
        self.edge_path = self._get_edge_path()
    
    def _get_edge_path(self) -> str:
        """
        获取 Edge 浏览器路径（跨平台）
        优先使用配置文件中的路径，如果未配置则自动检测
        
        Returns:
            str: Edge 可执行文件路径
        """
        # 优先使用配置文件中的路径
        configured_path = self.config.get('edge_path')
        if configured_path:
            # 展开用户目录路径（如 ~）
            expanded_path = os.path.expanduser(configured_path)
            if Path(expanded_path).exists():
                return expanded_path
            else:
                # 如果配置的路径不存在，抛出警告但继续自动检测
                print(f"⚠️  配置的 Edge 路径不存在: {configured_path}，将尝试自动检测")
        
        # 自动检测 Edge 路径
        system = platform.system()
        
        if system == "Windows":
            # Windows 常见路径
            possible_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
            ]
            for path in possible_paths:
                if Path(path).exists():
                    return path
        elif system == "Darwin":  # macOS
            edge_path = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
            if Path(edge_path).exists():
                return edge_path
        else:  # Linux
            possible_paths = [
                "/usr/bin/microsoft-edge",
                "/usr/bin/microsoft-edge-stable",
                "/usr/bin/msedge"
            ]
            for path in possible_paths:
                if Path(path).exists():
                    return path
        
        # 如果所有路径都找不到，抛出异常
        raise Exception(f"未找到 Edge 浏览器。请确保已安装 Edge 或在配置文件中指定 edge_path。")
    
    def is_running(self, port: Optional[int] = None) -> bool:
        """
        检查 Edge 是否在运行并启用了远程调试
        
        Args:
            port: 调试端口，如果为 None 则从配置读取
        
        Returns:
            bool: Edge 是否运行中
        """
        if port is None:
            # 优先使用 edge_debug_port，如果没有则使用 chrome_debug_port
            port = self.config.get('edge_debug_port') or self.config.get('chrome_debug_port', 9222)
        
        try:
            response = requests.get(f"http://localhost:{port}/json", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start(self) -> None:
        """
        启动 Edge 并启用远程调试
        
        Raises:
            Exception: 启动失败时抛出异常
        """
        if not Path(self.edge_path).exists():
            raise Exception(f"未找到 Edge 浏览器: {self.edge_path}")
        
        # 优先使用 edge_debug_port，如果没有则使用 chrome_debug_port
        port = self.config.get('edge_debug_port') or self.config.get('chrome_debug_port', 9222)
        
        # 根据操作系统设置默认的用户数据目录
        system = platform.system()
        if system == "Windows":
            default_user_data_dir = os.path.expanduser(r"~\AppData\Local\Temp\edge-debug-profile")
        elif system == "Darwin":  # macOS
            default_user_data_dir = "/tmp/edge-debug-profile"
        else:  # Linux
            default_user_data_dir = "/tmp/edge-debug-profile"
        
        # 优先使用 edge_user_data_dir，如果没有则使用 chrome_user_data_dir 或默认值
        user_data_dir = (
            self.config.get('edge_user_data_dir') or 
            self.config.get('chrome_user_data_dir') or 
            default_user_data_dir
        )
        
        # 检查是否已经在运行并启用了远程调试
        if self.is_running(port):
            print(f"✅ Edge 已运行，远程调试端口 {port} 已启用")
            return
        
        # 检查 Edge 进程是否在运行（不管是否启用远程调试）
        system = platform.system()
        
        if system == "Windows":
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq msedge.exe'],
                    capture_output=True,
                    text=True
                )
                edge_process_running = 'msedge.exe' in result.stdout
            except:
                edge_process_running = False
        elif system == "Darwin":  # macOS
            try:
                result = subprocess.run(['pgrep', '-f', 'Microsoft Edge'], 
                                      capture_output=True)
                edge_process_running = result.returncode == 0
            except:
                edge_process_running = False
        else:  # Linux
            try:
                result = subprocess.run(['pgrep', '-f', 'microsoft-edge'], 
                                      capture_output=True)
                edge_process_running = result.returncode == 0
            except:
                edge_process_running = False
        
        # 如果 Edge 正在运行但没有启用远程调试，不关闭它，直接启动新的带远程调试的实例
        if edge_process_running:
            print(f"⚠️  检测到 Edge 正在运行，但未启用远程调试")
            print(f"   将启动一个新的带远程调试的 Edge 实例（不关闭现有窗口）")
        
        # 启动新的 Edge 实例（带远程调试）
        print(f"正在启动 Edge（远程调试端口: {port}）...")
        
        # 构建启动命令
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(
                [self.edge_path, 
                 f'--remote-debugging-port={port}', 
                 f'--user-data-dir={user_data_dir}'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
        else:
            subprocess.Popen(
                [self.edge_path, f'--remote-debugging-port={port}', 
                 f'--user-data-dir={user_data_dir}'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        
        # 等待 Edge 启动
        for i in range(10):
            time.sleep(1)
            if self.is_running(port):
                print(f"✅ Edge 已成功启动，远程调试已启用（端口: {port}）")
                return
        
        raise Exception("Edge 启动失败或远程调试未启用")
    
    def get_url(self) -> str:
        """
        获取 Edge DevTools Protocol URL
        
        Returns:
            str: CDP URL，格式如 "http://localhost:9222"
        """
        # 优先使用 edge_debug_port，如果没有则使用 chrome_debug_port
        port = self.config.get('edge_debug_port') or self.config.get('chrome_debug_port', 9222)
        return f"http://localhost:{port}"
    
    def _get_browser_type(self) -> str:
        """获取浏览器类型标识"""
        return "edge"
    
    async def _connect_browser(self, playwright, browser_url: str):
        """
        连接到 Edge 浏览器
        
        Args:
            playwright: Playwright 实例
            browser_url: Edge DevTools Protocol URL
        
        Returns:
            浏览器对象，如果连接失败返回 None
        """
        try:
            # Edge 使用与 Chrome 相同的 CDP 协议
            browser = await playwright.chromium.connect_over_cdp(browser_url)
            return browser
        except Exception:
            return None

