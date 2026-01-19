"""
浏览器会话管理
负责管理浏览器会话的生命周期
"""
import sys
import logging
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page

# 添加 Web_analys 目录到路径
web_analys_dir = Path(__file__).parent.parent
if str(web_analys_dir) not in sys.path:
    sys.path.insert(0, str(web_analys_dir))

from BrowserManager.base_manager import BaseBrowserManager
from core.exceptions import BrowserNotRunningError, PageLoadError


class BrowserSession:
    """浏览器会话管理器"""
    
    def __init__(
        self,
        browser_manager: BaseBrowserManager,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化浏览器会话
        
        Args:
            browser_manager: 浏览器管理器实例
            logger: 日志记录器
        """
        self.browser_manager = browser_manager
        self.logger = logger or logging.getLogger("browser_session")
        self.playwright = None
        self.browser: Optional[Browser] = None
    
    async def ensure_browser_running(self) -> None:
        """
        确保浏览器正在运行（如果未运行则启动）
        
        Raises:
            BrowserNotRunningError: 浏览器启动失败
        """
        # 检查浏览器是否在运行
        if not self.browser_manager.is_running():
            self.logger.info("浏览器未运行，正在启动...")
            try:
                self.browser_manager.start()
                self.logger.info("✅ 浏览器启动成功")
            except Exception as e:
                raise BrowserNotRunningError(
                    f"无法启动浏览器: {str(e)}"
                ) from e
        else:
            self.logger.debug("浏览器已在运行")
    
    async def open_url(
        self, 
        url: str,
        wait_for_load: bool = True,
        wait_timeout: int = 10000,
        wait_for_redirect: bool = True,
        redirect_timeout: int = 300000
    ) -> Page:
        """
        打开指定的 URL，并监控页面跳转
        
        Args:
            url: 要打开的 URL
            wait_for_load: 是否等待页面加载完成
            wait_timeout: 等待超时时间（毫秒）
            wait_for_redirect: 是否等待页面跳转到目标 URL
            redirect_timeout: 等待跳转的超时时间（毫秒）
            
        Returns:
            Playwright Page 对象
            
        Raises:
            BrowserNotRunningError: 浏览器未运行
            PageLoadError: 页面加载失败
        """
        # 确保浏览器运行
        await self.ensure_browser_running()
        
        # 获取浏览器远程调试 URL
        browser_url = self.browser_manager.get_url()
        
        # 创建 Playwright 实例（如果还没有）
        if self.playwright is None:
            playwright_instance = await async_playwright().start()
            self.playwright = playwright_instance
        
        try:
            # 连接浏览器（每次打开 URL 都重新连接，确保使用最新的浏览器实例）
            browser = await self.browser_manager._connect_browser(
                self.playwright,
                browser_url
            )
            
            # 如果之前有浏览器实例且不同，关闭旧的
            if self.browser and self.browser != browser:
                try:
                    await self.browser.close()
                except Exception:
                    pass
            
            self.browser = browser
            
            if self.browser is None:
                raise BrowserNotRunningError(
                    f"无法连接到浏览器: {browser_url}"
                )
            
            # 创建或获取页面上下文
            contexts = self.browser.contexts
            if not contexts:
                context = await self.browser.new_context()
            else:
                context = contexts[0]
            
            # 创建新页面
            page = await context.new_page()
            
            # 导航到 URL
            self.logger.info(f"正在打开 URL: {url}")
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=wait_timeout)
                
                # 如果需要等待加载完成
                if wait_for_load:
                    try:
                        await page.wait_for_load_state('networkidle', timeout=wait_timeout)
                    except Exception:
                        # 如果 networkidle 超时，至少等待一下
                        import asyncio
                        await asyncio.sleep(1)
                
                current_url = page.url
                self.logger.info(f"初始页面 URL: {current_url}")
                
                # 如果需要等待页面跳转到目标 URL
                if wait_for_redirect:
                    page = await self._wait_for_target_page(
                        page, 
                        url, 
                        redirect_timeout
                    )
                
                self.logger.info(f"✅ 最终页面 URL: {page.url}")
                return page
                
            except Exception as e:
                await page.close()
                raise PageLoadError(url, f"页面加载失败: {str(e)}") from e
                
        except BrowserNotRunningError:
            raise
        except Exception as e:
            if isinstance(e, PageLoadError):
                raise
            raise PageLoadError(url, f"打开 URL 时出错: {str(e)}") from e
    
    async def _wait_for_target_page(
        self, 
        page: Page, 
        original_url: str,
        timeout: int = 30000
    ) -> Page:
        """
        等待页面跳转到目标 URL
        
        Args:
            page: 当前页面对象
            original_url: 原始打开的 URL
            timeout: 超时时间（毫秒）
            
        Returns:
            Page: 跳转后的页面对象（可能是同一个或新的页面）
        """
        import asyncio
        import sys
        from pathlib import Path
        
        # 获取目标 URL 配置
        target_urls = self.browser_manager.config.get('target_urls', [])
        if not target_urls:
            # 如果没有配置目标 URL，直接返回当前页面
            self.logger.debug("未配置 target_urls，跳过跳转监控")
            return page
        
        # 导入 URL 匹配工具
        utils_path = Path(__file__).parent.parent.parent / "utils"
        if str(utils_path) not in sys.path:
            sys.path.insert(0, str(utils_path))
        from url_utils import is_target_url
        
        start_time = asyncio.get_event_loop().time()
        check_interval = 5  # 每 5 秒检查一次
        last_url = page.url
        
        self.logger.info(f"监控页面跳转，目标 URL: {target_urls}")
        
        while True:
            # 检查当前页面 URL
            current_url = page.url
            
            # 检查是否匹配目标 URL
            if is_target_url(current_url, target_urls):
                self.logger.info(f"✅ 页面已跳转到目标 URL: {current_url}")
                return page
            
            # 检查是否超时
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            if elapsed >= timeout:
                self.logger.warning(
                    f"⏰ 等待页面跳转超时 ({timeout}ms)，当前 URL: {current_url}"
                )
                # 超时后返回当前页面
                return page
            
            # 如果 URL 发生变化，记录日志
            if current_url != last_url:
                self.logger.info(f"页面 URL 变化: {last_url} -> {current_url}")
                last_url = current_url
            
            # 等待一段时间后再次检查
            await asyncio.sleep(check_interval)
    
    async def close(self) -> None:
        """关闭浏览器会话"""
        if self.browser:
            try:
                await self.browser.close()
                self.logger.debug("浏览器会话已关闭")
            except Exception as e:
                self.logger.warning(f"关闭浏览器会话时出错: {e}")
            finally:
                self.browser = None
        
        if self.playwright:
            try:
                await self.playwright.stop()
                self.logger.debug("Playwright 已停止")
            except Exception as e:
                self.logger.warning(f"停止 Playwright 时出错: {e}")
            finally:
                self.playwright = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.ensure_browser_running()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()

