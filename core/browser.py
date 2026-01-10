"""
Browser automation core - Selenium wrapper with human-like behavior
"""
import os
import sys
import time
import random
from pathlib import Path
from typing import Optional, Callable

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager


class BrowserCore:
    """Core browser automation with human-like behavior"""
    
    def __init__(
        self,
        cache_dir: str = None,
        headless: bool = False,
        log_callback: Callable[[str], None] = None
    ):
        self.driver: Optional[webdriver.Chrome] = None
        self.cache_dir = cache_dir
        self.headless = headless
        self._log = log_callback or print
        
    def log(self, message: str):
        """Log a message"""
        self._log(message)
        
    def build_driver(self) -> webdriver.Chrome:
        """Build and return a Chrome WebDriver instance"""
        options = Options()
        
        # User data directory for persistent sessions
        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            options.add_argument(f"--user-data-dir={self.cache_dir}")
            
        # Common options
        if not self.headless:
            options.add_argument("--start-maximized")
        else:
            # Headless mode cần window size cụ thể
            options.add_argument("--window-size=1920,1080")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        if self.headless:
            options.add_argument("--headless=new")
            # Thêm user agent cho headless mode
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
        # Language
        options.add_argument("--lang=vi")
        prefs = {
            "intl.accept_languages": "vi,en",
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Set window size nếu headless (đảm bảo window size được set)
            if self.headless:
                driver.set_window_size(1920, 1080)
            
            # Remove webdriver flag
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            })
            
            self.driver = driver
            self.log("✅ Browser initialized successfully")
            return driver
            
        except Exception as e:
            self.log(f"❌ Failed to initialize browser: {e}")
            raise
            
    def close(self):
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
                self.log("🔒 Browser closed")
            except Exception:
                pass
            self.driver = None
            
    # ==================== Human-like behaviors ====================
    
    def human_delay(self, min_sec: float = 0.5, max_sec: float = 1.5):
        """Random delay to simulate human behavior"""
        time.sleep(random.uniform(min_sec, max_sec))
        
    def human_type(self, element, text: str, delay_range: tuple = (0.05, 0.15)):
        """Type text with human-like delays between keystrokes"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(*delay_range))
            
    def human_click(self, element):
        """Click with slight random offset to simulate human behavior"""
        try:
            actions = ActionChains(self.driver)
            # Move to element with slight offset
            offset_x = random.randint(-3, 3)
            offset_y = random.randint(-3, 3)
            actions.move_to_element_with_offset(element, offset_x, offset_y)
            actions.click()
            actions.perform()
        except Exception:
            # Fallback to regular click
            element.click()
            
    def scroll_page(self, direction: str = "down", amount: int = 300):
        """Scroll the page"""
        if direction == "down":
            self.driver.execute_script(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            self.driver.execute_script(f"window.scrollBy(0, -{amount})")
        self.human_delay(0.3, 0.5)
        
    # ==================== Element finding ====================
    
    def wait_for_element(
        self, 
        by: By, 
        value: str, 
        timeout: int = 10,
        clickable: bool = False
    ):
        """Wait for an element to be present/clickable"""
        wait = WebDriverWait(self.driver, timeout)
        condition = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
        return wait.until(condition((by, value)))
    
    def wait_for_elements(self, by: By, value: str, timeout: int = 10) -> list:
        """Wait for multiple elements"""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_all_elements_located((by, value)))
    
    def find_element_safe(self, by: By, value: str):
        """Find element without throwing exception"""
        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            return None
            
    def find_button_by_text(self, text: str, timeout: int = 5):
        """Find a button by its visible text"""
        try:
            xpath = f"//button[contains(., '{text}')] | //a[contains(., '{text}')] | //*[@role='button'][contains(., '{text}')]"
            return self.wait_for_element(By.XPATH, xpath, timeout, clickable=True)
        except TimeoutException:
            return None
            
    def find_input_by_placeholder(self, placeholder: str, timeout: int = 5):
        """Find input by placeholder text"""
        try:
            xpath = f"//input[@placeholder='{placeholder}'] | //textarea[@placeholder='{placeholder}']"
            return self.wait_for_element(By.XPATH, xpath, timeout)
        except TimeoutException:
            return None
            
    # ==================== Navigation ====================
    
    def navigate(self, url: str, wait_for: str = None, wait_timeout: int = 10):
        """Navigate to URL and optionally wait for an element"""
        self.log(f"🌐 Navigating to: {url}")
        self.driver.get(url)
        self.human_delay(1, 2)
        
        if wait_for:
            try:
                self.wait_for_element(By.CSS_SELECTOR, wait_for, wait_timeout)
                self.log(f"✅ Page loaded, found: {wait_for}")
            except TimeoutException:
                self.log(f"⚠️ Timeout waiting for: {wait_for}")
                
    def current_url(self) -> str:
        """Get current URL"""
        return self.driver.current_url if self.driver else ""
    
    def get_page_source(self) -> str:
        """Get page HTML source"""
        return self.driver.page_source if self.driver else ""
    
    # ==================== Screenshots ====================
    
    def take_screenshot(self, filepath: str):
        """Take a screenshot and save to file"""
        try:
            self.driver.save_screenshot(filepath)
            self.log(f"📸 Screenshot saved: {filepath}")
            return True
        except Exception as e:
            self.log(f"❌ Screenshot failed: {e}")
            return False
