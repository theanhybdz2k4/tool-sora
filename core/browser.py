# -*- coding: utf-8 -*-
"""
Browser Core Module - Quản lý browser với Playwright
Đã tối ưu hóa cực nhẹ và ổn định
"""

import os
import time
import logging
import json
import shutil
from typing import Optional, List, Any

from config.settings import (
    PROFILES_DIR, USER_AGENT, PAGE_LOAD_TIMEOUT, 
    ELEMENT_TIMEOUT, HEADLESS_MODE
)

logger = logging.getLogger(__name__)

class BrowserCore:
    """Lớp quản lý browser instance sử dụng Playwright"""
    
    def __init__(self, profile_name: str = "default", headless: bool = None):
        """
        Khởi tạo browser
        
        Args:
            profile_name: Tên profile để lưu session
            headless: Chạy ở chế độ headless hay không
        """
        self.profile_name = profile_name
        self.headless = headless if headless is not None else HEADLESS_MODE
        self._playwright = None
        self.context = None
        self.page = None
        self.base_profile_dir = os.path.join(PROFILES_DIR, profile_name)
        
        # Tạo thư mục profile nếu chưa có
        os.makedirs(self.base_profile_dir, exist_ok=True)
    
    def _cleanup_profile(self):
        """Dọn dẹp các tệp tin khóa hoặc rác của profile cũ để đảm bảo khởi động nhẹ nhất"""
        try:
            lock_files = ["SingletonLock", "SingletonSocket", "SingletonCookie", "lock"]
            for root, dirs, files in os.walk(self.base_profile_dir):
                for file in files:
                    if file in lock_files:
                        try:
                            os.remove(os.path.join(root, file))
                            logger.info(f"🔓 Đã xóa file lock: {file}")
                        except: pass
                break
        except Exception as e:
            logger.warning(f"Lỗi khi dọn dẹp profile: {e}")

    def init_browser(self, initial_url: str = None, retries: int = 3, port: int = None, **kwargs):
        """Khởi tạo và trả về page instance với Playwright"""
        self._cleanup_profile()
        
        for attempt in range(retries):
            try:
                logger.info(f"🚀 [Playwright] Đang khởi tạo browser: {self.profile_name} (Lần {attempt + 1})")
                
                if not self._playwright:
                    from playwright.sync_api import sync_playwright
                    self._playwright = sync_playwright().start()
                
                # Cấu hình browser tối ưu cực nhẹ
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-service-autorun",
                    "--password-store=basic"
                ]
                
                # Khởi tạo Persistent Context (giống profile của Chrome)
                self.context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self.base_profile_dir,
                    headless=self.headless,
                    user_agent=USER_AGENT,
                    no_viewport=True,
                    args=launch_args,
                    accept_downloads=True,
                    ignore_https_errors=True,
                    bypass_csp=True,
                    slow_mo=50
                )
                
                self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
                
                # Thiết lập timeout
                self.page.set_default_timeout(ELEMENT_TIMEOUT * 1000)
                self.page.set_default_navigation_timeout(PAGE_LOAD_TIMEOUT * 1000)
                
                if initial_url:
                    logger.info(f"Điều hướng đến: {initial_url}")
                    self.page.goto(initial_url, wait_until="domcontentloaded")
                
                logger.info(f"✅ Khởi tạo Playwright thành công!")
                return self.page
                
            except Exception as e:
                logger.error(f"❌ Lỗi khởi tạo Playwright (Lần {attempt + 1}): {e}")
                self.close()
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    raise

    def navigate(self, url: str) -> bool:
        """Điều hướng đến URL"""
        if not self.page:
            logger.error("Page chưa được khởi tạo")
            return False
            
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT * 1000)
            return True
        except Exception as e:
            logger.error(f"Lỗi điều hướng: {e}")
            return False

    def wait_for_element(self, selector: str, timeout: int = None, state: str = "attached") -> Any:
        """
        Chờ element xuất hiện
        state: "attached", "visible", "hidden", "detached"
        """
        if not self.page: return None
        timeout = (timeout or ELEMENT_TIMEOUT) * 1000
        
        try:
            return self.page.wait_for_selector(selector, state=state, timeout=timeout)
        except Exception:
            return None

    def click_element(self, selector: str, timeout: int = None, force: bool = False) -> bool:
        """Click vào element"""
        if not self.page: return False
        timeout = (timeout or ELEMENT_TIMEOUT) * 1000
        
        try:
            self.page.click(selector, timeout=timeout, force=force)
            return True
        except Exception as e:
            try:
                self.page.evaluate(f"document.querySelector('{selector}').click()")
                return True
            except:
                logger.error(f"Lỗi click: {e}")
                return False

    def type_text(self, selector: str, text: str, delay: int = 50) -> bool:
        """Nhập văn bản"""
        if not self.page: return False
        
        try:
            self.page.fill(selector, "")
            self.page.type(selector, text, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Lỗi nhập text: {e}")
            return False

    def find_elements(self, selector: str) -> List[Any]:
        """Tìm danh sách elements"""
        if not self.page: return []
        return self.page.query_selector_all(selector)

    def execute_script(self, script: str, *args):
        """Thực thi JavaScript"""
        if self.page:
            return self.page.evaluate(script, *args)
        return None

    def get_current_url(self) -> str:
        """Lấy URL hiện tại"""
        return self.page.url if self.page else ""

    def take_screenshot(self, name: str = "screenshot") -> Optional[str]:
        """Chụp màn hình"""
        if self.page:
            try:
                filepath = os.path.join(self.base_profile_dir, f"{name}_{int(time.time())}.png")
                self.page.screenshot(path=filepath)
                return filepath
            except Exception as e:
                logger.error(f"Lỗi chụp màn hình: {e}")
        return None

    def close(self):
        """Đóng hoàn toàn browser và Playwright"""
        try:
            if self.context:
                self.context.close()
                self.context = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            logger.info("🔒 Đã đóng Playwright Browser")
        except: pass

    def __enter__(self):
        self.init_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
