# -*- coding: utf-8 -*-
"""
Browser Core Module - Quản lý browser với undetected-chromedriver
"""

import os
import time
import logging
from typing import Optional

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import winreg

from config.settings import (
    PROFILES_DIR, USER_AGENT, PAGE_LOAD_TIMEOUT, 
    ELEMENT_TIMEOUT, HEADLESS_MODE
)

logger = logging.getLogger(__name__)


def get_chrome_main_version() -> Optional[int]:
    """Lấy phiên bản chính (main version) của Chrome đang cài đặt trên Windows"""
    paths = [
        r"SOFTWARE\Google\Chrome\BLBeacon",
        r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon",
    ]
    for path in paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                version, _ = winreg.QueryValueEx(key, "version")
                main_version = int(version.split(".")[0])
                logger.info(f"Đã phát hiện Chrome phiên bản: {main_version}")
                return main_version
        except (FileNotFoundError, OSError, ValueError):
            continue
            
    try:
        # Fallback: Kiểm tra User-specific install
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon") as key:
            version, _ = winreg.QueryValueEx(key, "version")
            main_version = int(version.split(".")[0])
            logger.info(f"Đã phát hiện Chrome phiên bản (User): {main_version}")
            return main_version
    except (FileNotFoundError, OSError, ValueError):
        pass
        
    logger.warning("Không thể tự động phát hiện phiên bản Chrome")
    return None


class BrowserCore:
    """Lớp quản lý browser instance"""
    
    def __init__(self, profile_name: str = "default", headless: bool = None):
        """
        Khởi tạo browser
        
        Args:
            profile_name: Tên profile để lưu session
            headless: Chạy ở chế độ headless hay không
        """
        self.profile_name = profile_name
        self.headless = headless if headless is not None else HEADLESS_MODE
        self.driver: Optional[uc.Chrome] = None
        self.profile_dir = os.path.join(PROFILES_DIR, profile_name)
        
        # Tạo thư mục profile nếu chưa có
        os.makedirs(self.profile_dir, exist_ok=True)
    
    def init_browser(self, retries: int = 3) -> uc.Chrome:
        """Khởi tạo và trả về browser instance với cơ chế retry"""
        for attempt in range(retries):
            try:
                logger.info(f"Đang khởi tạo browser với profile: {self.profile_name} (Lần {attempt + 1})")
                
                options = uc.ChromeOptions()
                options.add_argument(f"--user-data-dir={self.profile_dir}")
                options.add_argument(f"--user-agent={USER_AGENT}")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-infobars")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                
                prefs = {
                    "download.default_directory": os.path.join(os.getcwd(), "data", "output"),
                    "download.prompt_for_download": False,
                    "download.directory_upgrade": True,
                    "safebrowsing.enabled": True
                }
                options.add_experimental_option("prefs", prefs)
                
                if self.headless:
                    options.add_argument("--headless=new")
                    logger.info("Chạy ở chế độ headless")
                
                # Tự động phát hiện version
                chrome_version = get_chrome_main_version()
                if chrome_version:
                    self.driver = uc.Chrome(options=options, version_main=chrome_version)
                else:
                    # Nếu không tìm thấy, để undetected_chromedriver tự quyết định (fallback)
                    self.driver = uc.Chrome(options=options)
                    
                self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
                
                # Chờ một chút để driver sẵn sàng hoàn toàn
                time.sleep(1)
                
                logger.info(f"Khởi tạo browser thành công với profile: {self.profile_name}")
                return self.driver
                
            except Exception as e:
                logger.error(f"Lỗi khởi tạo browser (Lần {attempt + 1}): {e}")
                if self.driver:
                    try: self.driver.quit()
                    except: pass
                
                if attempt < retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.info(f"Thử lại sau {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def navigate(self, url: str) -> bool:
        """
        Điều hướng đến URL
        
        Args:
            url: URL cần điều hướng
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        if not self.driver:
            logger.error("Browser chưa được khởi tạo")
            return False
        
        try:
            logger.info(f"Đang điều hướng đến: {url}")
            self.driver.get(url)
            # Log verify xem đã thực sự ở page đó chưa
            time.sleep(2)
            actual_url = self.driver.current_url
            logger.info(f"URL hiện tại sau điều hướng: {actual_url}")
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "connection refused" in err_str or "10061" in err_str:
                logger.error(f"❌ Mất kết nối trình duyệt (WinError 10061): {url}")
            else:
                logger.error(f"Lỗi điều hướng: {e}")
            return False
    
    def wait_for_element(self, selector: str, timeout: int = None, by: By = By.CSS_SELECTOR) -> Optional[object]:
        """
        Chờ element xuất hiện
        
        Args:
            selector: CSS selector hoặc XPath
            timeout: Thời gian chờ (giây)
            by: Loại selector (CSS_SELECTOR hoặc XPATH)
            
        Returns:
            Element nếu tìm thấy, None nếu không
        """
        if not self.driver:
            return None
        
        timeout = timeout or ELEMENT_TIMEOUT
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Không tìm thấy element: {selector}")
            return None
    
    def wait_for_clickable(self, selector: str, timeout: int = None, by: By = By.CSS_SELECTOR) -> Optional[object]:
        """Chờ element có thể click"""
        if not self.driver:
            return None
        
        timeout = timeout or ELEMENT_TIMEOUT
        
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            return element
        except TimeoutException:
            logger.warning(f"Element không thể click: {selector}")
            return None
    
    def click_element(self, selector: str, by: By = By.CSS_SELECTOR, timeout: int = None) -> bool:
        """
        Click vào element với nhiều fallback
        """
        # 1. Thử chờ clickable
        element = self.wait_for_clickable(selector, by=by, timeout=timeout)
        
        # 2. Nếu không clickable, thử tìm sự hiện diện (có thể bị che nhưng vẫn JS click được)
        if not element:
            element = self.wait_for_element(selector, by=by, timeout=timeout)
            
        if element:
            try:
                # Thử click bình thường
                element.click()
                time.sleep(0.5)
                return True
            except Exception:
                # Thử click bằng JavaScript
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(0.5)
                    return True
                except Exception as e:
                    logger.error(f"Lỗi click element hoàn toàn: {e}")
        return False
    
    def type_text(self, selector: str, text: str, clear_first: bool = True, by: By = By.CSS_SELECTOR) -> bool:
        """
        Nhập text vào element
        
        Args:
            selector: CSS selector hoặc XPath
            text: Text cần nhập
            clear_first: Xóa text hiện tại trước khi nhập
            by: Loại selector
            
        Returns:
            True nếu nhập thành công
        """
        element = self.wait_for_element(selector, by=by)
        if element:
            try:
                if clear_first:
                    element.clear()
                element.send_keys(text)
                return True
            except Exception as e:
                logger.error(f"Lỗi nhập text: {e}")
        return False
    
    def find_elements(self, selector: str, by: By = By.CSS_SELECTOR) -> list:
        """Tìm tất cả elements theo selector"""
        if not self.driver:
            return []
        
        try:
            return self.driver.find_elements(by, selector)
        except:
            return []
    
    def execute_script(self, script: str, *args):
        """Thực thi JavaScript"""
        if self.driver:
            return self.driver.execute_script(script, *args)
        return None
    
    def get_current_url(self) -> str:
        """Lấy URL hiện tại"""
        if self.driver:
            return self.driver.current_url
        return ""
    
    def take_screenshot(self, filepath: str) -> bool:
        """Chụp screenshot"""
        if self.driver:
            try:
                self.driver.save_screenshot(filepath)
                return True
            except:
                pass
        return False
    
    def close(self):
        """Đóng browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Đã đóng browser")
            except:
                pass
            self.driver = None
    
    def __enter__(self):
        self.init_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
