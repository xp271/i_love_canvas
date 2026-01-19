"""
URL 捕获服务
高级接口，整合浏览器会话和页面保存功能
"""
import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse

# 添加 Web_analys 目录到路径
web_analys_dir = Path(__file__).parent.parent
if str(web_analys_dir) not in sys.path:
    sys.path.insert(0, str(web_analys_dir))

from BrowserManager.base_manager import BaseBrowserManager
from core.browser_session import BrowserSession
from core.page_saver import PageSaver
from core.capture_result import CaptureResult
from core.exceptions import WebAnalysError, BrowserNotRunningError, PageLoadError, SaveError


class URLCaptureService:
    """URL 捕获服务 - 高级接口"""
    
    def __init__(
        self,
        browser_manager: BaseBrowserManager,
        output_dir: str,
        logger: Optional[logging.Logger] = None,
        page_saver: Optional[PageSaver] = None
    ):
        """
        初始化 URL 捕获服务
        
        Args:
            browser_manager: 浏览器管理器
            output_dir: 输出目录
            logger: 日志记录器
            page_saver: 页面保存器（可选，会自动创建）
        """
        self.browser_manager = browser_manager
        self.output_dir = output_dir
        self.logger = logger or logging.getLogger("url_capture_service")
        self.page_saver = page_saver or PageSaver(output_dir, self.logger)
    
    async def capture_url(
        self,
        url: str,
        wait_for_load: bool = True,
        wait_timeout: int = 10000
    ) -> Optional[CaptureResult]:
        """
        捕获指定 URL 的 HTML 和截图
        
        Args:
            url: 要捕获的 URL
            wait_for_load: 是否等待页面加载完成
            wait_timeout: 等待超时时间（毫秒）
            
        Returns:
            Optional[CaptureResult]: 捕获结果，如果页面被重定向到其他页面则返回 None
            
        Raises:
            BrowserNotRunningError: 浏览器未运行
            PageLoadError: 页面加载失败
            SaveError: 保存失败
        """
        timestamp = datetime.now()
        session = None
        page = None
        
        try:
            # 创建浏览器会话
            session = BrowserSession(self.browser_manager, self.logger)
            
            # 打开 URL（启用跳转监控）
            self.logger.info(f"开始捕获 URL: {url}")
            redirect_timeout = self.browser_manager.config.get('redirect_timeout', 30000)
            page = await session.open_url(
                url, 
                wait_for_load, 
                wait_timeout,
                wait_for_redirect=True,
                redirect_timeout=redirect_timeout
            )
            
            # 检查页面是否被重定向到其他页面
            current_url = page.url
            parsed_original = urlparse(url)
            parsed_current = urlparse(current_url)
            
            # 如果域名发生变化，说明被重定向了
            if parsed_current.netloc != parsed_original.netloc:
                self.logger.warning(f"⚠️  页面被重定向到不同域名: {url} -> {current_url}，放弃保存")
                await page.close()
                await session.close()
                return None
            
            # 检查路径是否发生变化（去掉尾部的斜杠进行比较）
            original_path = parsed_original.path.rstrip('/')
            current_path = parsed_current.path.rstrip('/')
            
            # 如果路径完全不同，说明被重定向了
            # 但允许路径包含原始路径（如 /courses/123/assignments 可能跳转到 /courses/123/assignments/456）
            if original_path and current_path and not current_path.startswith(original_path):
                self.logger.warning(f"⚠️  页面被重定向到不同路径: {url} -> {current_url}，放弃保存")
                await page.close()
                await session.close()
                return None
            
            # 如果原始路径是 /assignments 但当前路径不包含 /assignments，说明被重定向了
            if '/assignments' in original_path and '/assignments' not in current_path:
                self.logger.warning(f"⚠️  页面被重定向离开 assignments: {url} -> {current_url}，放弃保存")
                await page.close()
                await session.close()
                return None
            
            # 生成文件路径（支持层级结构和课程名称）
            parent_html_file = getattr(self, '_parent_html_file', None)
            course_name = getattr(self, '_course_name', None)
            
            # 调试日志
            if parent_html_file:
                self.logger.debug(f"父级 HTML 文件: {parent_html_file}")
            if course_name:
                self.logger.debug(f"课程名称: {course_name}")
            else:
                self.logger.debug("未设置课程名称")
            
            html_path, screenshot_path = self.page_saver.generate_file_paths(
                url, 
                timestamp,
                parent_html_file=parent_html_file,
                course_name=course_name
            )
            
            self.logger.debug(f"生成的文件路径 - HTML: {html_path}, 截图: {screenshot_path}")
            
            # 保存 HTML
            try:
                html_file = await self.page_saver.save_html(page, html_path)
            except SaveError as e:
                self.logger.error(f"❌ 保存 HTML 失败: {e}")
                raise
            
            # 保存截图
            try:
                screenshot_file = await self.page_saver.save_screenshot(page, screenshot_path)
            except SaveError as e:
                self.logger.error(f"❌ 保存截图失败: {e}")
                # HTML 已保存，但截图失败，仍然返回结果（但截图路径可能无效）
                screenshot_file = screenshot_path
                raise
            
            # 创建结果对象（使用实际打开的 URL）
            result = CaptureResult(
                url=current_url,
                html_file=html_file,
                screenshot_file=screenshot_file,
                timestamp=timestamp
            )
            
            self.logger.info(f"✅ 捕获完成: {url}")
            self.logger.info(f"   HTML: {html_file}")
            self.logger.info(f"   截图: {screenshot_file}")
            
            # 关闭页面和会话
            if page:
                try:
                    await page.close()
                    self.logger.debug("页面已关闭")
                except Exception as e:
                    self.logger.warning(f"关闭页面时出错: {e}")
            
            if session:
                try:
                    await session.close()
                    self.logger.debug("浏览器会话已关闭")
                except Exception as e:
                    self.logger.warning(f"关闭会话时出错: {e}")
            
            return result
            
        except (BrowserNotRunningError, PageLoadError, SaveError):
            # 发生异常时，始终清理资源
            if page:
                try:
                    await page.close()
                except Exception as e:
                    self.logger.warning(f"关闭页面时出错: {e}")
            
            if session:
                try:
                    await session.close()
                except Exception as e:
                    self.logger.warning(f"关闭会话时出错: {e}")
            
            # 重新抛出已知异常
            raise
        except Exception as e:
            # 发生未知异常时，清理资源
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            
            if session:
                try:
                    await session.close()
                except Exception:
                    pass
            
            # 包装其他异常
            self.logger.error(f"❌ 捕获 URL 时发生未知错误: {str(e)}")
            raise WebAnalysError(f"捕获 URL 失败: {str(e)}") from e

