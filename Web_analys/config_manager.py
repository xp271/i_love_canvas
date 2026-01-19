"""
配置管理器
负责配置文件的加载、验证和路径规范化
"""
import json
from pathlib import Path
from typing import Dict


class ConfigManager:
    """配置管理器 - 专门处理配置的加载和验证"""
    
    @staticmethod
    def get_default_config() -> Dict:
        """
        返回默认配置
        
        Returns:
            Dict: 默认配置字典
        """
        return {
            "target_urls": [
                ""
            ],
            "check_interval": 5,
            "output_dir": "web_analys/output",
            "chrome_path": None,
            "chrome_debug_port": 9222,
            "chrome_user_data_dir": "/tmp/chrome-debug-profile",
            "browser_startup_wait": 3,
            "page_load_wait": 2,
            "clean_output_on_start": True  # 启动时是否清理输出目录
        }
    
    @staticmethod
    def load_config(config_path: Path) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Dict: 加载后的配置字典
        """
        # 如果配置文件不存在，创建默认配置
        if not config_path.exists():
            default_config = ConfigManager.get_default_config()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"已创建默认配置文件: {config_path}")
            return default_config
        
        # 加载现有配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 规范化路径
        config = ConfigManager.normalize_paths(config)
        
        return config
    
    @staticmethod
    def normalize_paths(config: Dict) -> Dict:
        """
        规范化配置中的路径
        
        Args:
            config: 配置字典
            
        Returns:
            Dict: 规范化后的配置字典
        """
        # 规范化输出目录路径
        output_dir = config.get('output_dir', 'output')
        if not Path(output_dir).is_absolute():
            # 基于项目根目录计算绝对路径
            # 假设 Web_analys 在项目根目录下
            web_analys_dir = Path(__file__).parent
            project_root = web_analys_dir.parent
            
            # 如果输出目录以 web_analys/ 开头，基于项目根目录
            if output_dir.startswith('web_analys/'):
                config['output_dir'] = str(project_root / output_dir)
            else:
                # 否则基于 web_analys 目录
                config['output_dir'] = str(web_analys_dir / output_dir)
        
        # 规范化浏览器路径（如果配置了）
        chrome_path = config.get('chrome_path')
        if chrome_path:
            expanded_path = str(Path(chrome_path).expanduser())
            config['chrome_path'] = expanded_path
        
        # 规范化用户数据目录路径
        user_data_dir = config.get('chrome_user_data_dir')
        if user_data_dir and not Path(user_data_dir).is_absolute():
            # 如果是相对路径，基于系统临时目录
            import tempfile
            temp_dir = Path(tempfile.gettempdir())
            config['chrome_user_data_dir'] = str(temp_dir / user_data_dir)
        
        return config
    
    @staticmethod
    def get_default_config_path() -> Path:
        """
        获取默认配置文件路径
        
        Returns:
            Path: 默认配置文件路径
        """
        web_analys_dir = Path(__file__).parent
        project_root = web_analys_dir.parent
        return project_root / "config.json"

