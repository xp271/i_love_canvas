"""
Chrome 浏览器管理模块
负责启动和管理带远程调试的 Chrome 浏览器
"""
import subprocess
import time
from pathlib import Path
import requests


class ChromeManager:
    """Chrome 浏览器管理器"""
    
    def __init__(self, config: dict):
        """
        初始化 Chrome 管理器
        
        Args:
            config: 配置字典，包含 chrome_debug_port 和 chrome_user_data_dir
        """
        self.config = config
        self.chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    def is_chrome_running_with_debug(self, port: int = None):
        """检查 Chrome 是否在运行并启用了远程调试"""
        if port is None:
            port = self.config.get('chrome_debug_port', 9222)
        
        try:
            response = requests.get(f"http://localhost:{port}/json", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start_chrome_with_debug(self):
        """启动 Chrome 并启用远程调试"""
        if not Path(self.chrome_path).exists():
            raise Exception(f"未找到 Chrome 浏览器: {self.chrome_path}")
        
        port = self.config.get('chrome_debug_port', 9222)
        user_data_dir = self.config.get('chrome_user_data_dir', '/tmp/chrome-debug-profile')
        
        # 检查是否已经在运行并启用了远程调试
        if self.is_chrome_running_with_debug(port):
            print(f"✅ Chrome 已运行，远程调试端口 {port} 已启用")
            return
        
        # 检查 Chrome 进程是否在运行（不管是否启用远程调试）
        try:
            result = subprocess.run(['pgrep', '-f', 'Google Chrome'], 
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
        subprocess.Popen(
            [self.chrome_path, f'--remote-debugging-port={port}', 
             f'--user-data-dir={user_data_dir}'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # 等待 Chrome 启动
        for i in range(10):
            time.sleep(1)
            if self.is_chrome_running_with_debug(port):
                print(f"✅ Chrome 已成功启动，远程调试已启用（端口: {port}）")
                return
        
        raise Exception("Chrome 启动失败或远程调试未启用")
    
    def get_cdp_url(self):
        """获取 Chrome DevTools Protocol URL"""
        port = self.config.get('chrome_debug_port', 9222)
        return f"http://localhost:{port}"

