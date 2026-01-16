import os
import time
import requests
from pathlib import Path
from typing import Optional, Callable, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class SoraAutomationService:
    """Automate Sora video generation"""
    
    BASE_URL = "https://sora.chatgpt.com"
    
    def __init__(self, browser=None, driver=None, download_dir: str = None, 
                 log_callback: Optional[Callable] = None):
        if browser is not None:
            self.browser = browser
            self.driver = browser.driver
        elif driver is not None:
            self.browser = None
            self.driver = driver
        else:
            raise ValueError("Either browser or driver must be provided")
        
        self.download_dir = download_dir or str(Path.cwd() / "downloads")
        self.log = log_callback or print
        self.wait = WebDriverWait(self.driver, 30)
        
        # Cache flags to avoid redundant operations
        self._switched_to_old_sora = False  # Only switch once per session
        self._last_settings = {}  # Cache last configured settings
        
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Navigate to Sora immediately
        self.log("🌐 Đang mở sora.chatgpt.com...")
        self.driver.get(self.BASE_URL)
        time.sleep(3)
        
        # PROACTIVE: Switch to old Sora immediately after login/opening
        self.log("🔍 Đang thực hiện kiểm tra giao diện Old Sora...")
        if self.switch_to_old_sora():
            self._switched_to_old_sora = True
        else:
            self.log("⚠️ Không thể xác định hoặc chuyển đổi giao diện trong lúc khởi tạo.")
        time.sleep(1)
        
        
    # ==================== LOGIN CHECK ====================
    
    def is_logged_in(self) -> bool:
        """Check if user is logged into Sora"""
        try:
            page_source = self.driver.page_source.lower()
            # Check for signs of being logged in
            if 'describe your video' in page_source or 'storyboard' in page_source:
                return True
            return False
        except Exception:
            return False
            
    def wait_for_manual_login(self, timeout: int = 300) -> bool:
        """Wait for user to manually log in"""
        self.log("⏳ Đang chờ đăng nhập thủ công...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                page_source = self.driver.page_source.lower()
                # Check for logged-in indicators
                if 'describe your video' in page_source or 'storyboard' in page_source:
                    self.log("✅ Phát hiện đăng nhập thành công!")
                    return True
            except Exception:
                pass
            time.sleep(3)
            
        return False
        
    # ==================== NAVIGATION ====================
    
    def switch_to_old_sora(self) -> bool:
        """
        Switch from New Sora to Old Sora interface.
        
        New Sora indicators:
        - Has Settings button (3 dots icon) with aria-label="Settings"
        - Menu contains "Switch to old Sora"
        
        Old Sora indicators:
        - Has "Open New Sora" button
        - Has "Describe your image..." prompt input
        """
        self.log("🔄 Kiểm tra và chuyển sang Old Sora...")
        
        try:
            # Check if already on old Sora by looking for indicators
            page_source = self.driver.page_source.lower()
            
            # Old Sora has "Describe your image" input
            if 'describe your image' in page_source:
                self.log("✅ Đang ở Old Sora (có prompt input)")
                return True
            
            # Old Sora has "Open New Sora" button
            if 'open new sora' in page_source:
                self.log("✅ Đang ở Old Sora (có Open New Sora button)")
                return True
            
            # We are on New Sora - need to switch
            self.log("🔍 Đang ở New Sora, tìm nút Settings...")
            
            # Method 1: Find Settings button by aria-label="Settings"
            try:
                settings_btn = self.driver.find_element(By.CSS_SELECTOR, 
                    'button[aria-label="Settings"]')
                if settings_btn.is_displayed():
                    settings_btn.click()
                    self.log("✅ Đã click Settings button")
                    time.sleep(1)
                    
                    # Now find "Switch to old Sora" in menu
                    try:
                        switch_item = self.driver.find_element(By.XPATH,
                            "//*[contains(text(), 'Switch to old Sora')]")
                        if switch_item.is_displayed():
                            switch_item.click()
                            self.log("✅ Đã click 'Switch to old Sora'")
                            time.sleep(3)
                            return True
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Method 2: Find by 3 dots icon SVG (backup)
            try:
                # Look for buttons with SVG containing 3 circles (dots pattern)
                dot_buttons = self.driver.find_elements(By.XPATH,
                    "//button[.//svg and (contains(@aria-label, 'Settings') or contains(@aria-label, 'More') or contains(@aria-label, 'Menu'))]")
                
                for btn in dot_buttons:
                    try:
                        if btn.is_displayed():
                            btn.click()
                            self.log("✅ Đã click dot menu button")
                            time.sleep(1)
                            
                            # Find Switch to old Sora
                            switch_item = self.driver.find_element(By.XPATH,
                                "//*[contains(text(), 'Switch to old Sora')]")
                            if switch_item.is_displayed():
                                switch_item.click()
                                self.log("✅ Đã click 'Switch to old Sora' từ menu")
                                time.sleep(3)
                                return True
                    except Exception:
                        continue
            except Exception:
                pass
            
            # Method 3: Look for menu item with role="menuitem"  
            try:
                menu_items = self.driver.find_elements(By.CSS_SELECTOR, '[role="menuitem"]')
                for item in menu_items:
                    if 'switch to old sora' in item.text.lower():
                        item.click()
                        self.log("✅ Đã click 'Switch to old Sora' (menuitem)")
                        time.sleep(3)
                        return True
            except Exception:
                pass
            
            # Method 4: Click any visible element with "Switch to old Sora" text
            try:
                switch_elem = self.driver.find_element(By.XPATH, 
                    "//*[contains(text(), 'Switch to old Sora')]")
                if switch_elem.is_displayed():
                    switch_elem.click()
                    self.log("✅ Đã click 'Switch to old Sora'")
                    time.sleep(3)
                    return True
            except Exception:
                pass
            
            self.log("⚠️ Không tìm thấy option Switch to old Sora")
            return False
            
        except Exception as e:
            self.log(f"⚠️ Lỗi switch Sora version: {e}")
            return False
    
    def navigate_to_create(self) -> bool:
        """Navigate to video creation page - OPTIMIZED"""
        
        try:
            # PRIORITIZE: Switch to old Sora ONLY if not already switched this session
            # Must run BEFORE checking prompt input, because New Sora also has prompt input
            if not self._switched_to_old_sora:
                self.log("🔄 Kiểm tra và Chuyển sang Old Sora...")
                if self.switch_to_old_sora():
                    self._switched_to_old_sora = True
                time.sleep(2)

            # Check if already on correct page (avoid unnecessary navigation)
            try:
                current_url = self.driver.current_url
            except:
                current_url = ""
            
            # If already on create page with prompt input, no need to navigate
            if 'sora.chatgpt.com' in current_url:
                # Check if prompt input exists = already on create page
                if self._find_prompt_input():
                    self.log("✅ Đã ở trang tạo video")
                    return True
                
                # If prompt input not found, we might be on New Sora or redirect loop
                self.log("🔄 Không thấy prompt input, kiểm tra lại giao diện...")
                if self.switch_to_old_sora():
                    self._switched_to_old_sora = True
                time.sleep(2)
                
                # Re-check after switch
                if self._find_prompt_input():
                    self.log("✅ Đã ở trang tạo video")
                    return True
            
            # Only navigate if NOT already on sora domain
            if 'sora.chatgpt.com' not in current_url:
                self.log("🌐 Navigating to Sora...")
                self.driver.get(self.BASE_URL)
                time.sleep(3)
            
            # Wait for prompt input to appear (max 15 seconds)
            for i in range(15):
                if self._find_prompt_input():
                    self.log("✅ Đã vào trang tạo video")
                    return True
                time.sleep(1)
            
            # ONLY check Cloudflare when we FAILED to find prompt input
            if self._is_cloudflare_challenge():
                self.log("⚠️ Cloudflare challenge! Waiting...")
                if self._wait_for_cloudflare():
                    # Try again after Cloudflare
                    for _ in range(10):
                        if self._find_prompt_input():
                            self.log("✅ Đã vào trang tạo video")
                            return True
                        time.sleep(1)
                
            self.log("⚠️ Không tìm thấy ô nhập prompt")
            return False
            
        except Exception as e:
            self.log(f"❌ Lỗi navigation: {e}")
            return False
    
    def _is_cloudflare_challenge(self) -> bool:
        """Check if Cloudflare challenge page is displayed - STRICT detection"""
        try:
            # More strict: check page title and specific challenge elements
            title = self.driver.title.lower()
            
            # Cloudflare challenge page has specific titles
            if 'just a moment' in title or 'attention required' in title:
                return True
            
            # Check for specific challenge text (not generic "cloudflare")
            page_source = self.driver.page_source.lower()
            
            # These are SPECIFIC to challenge page, not footer/scripts
            strict_indicators = [
                'xác minh bạn là con người',  # Vietnamese
                'verify you are human',
                'checking your browser before',
                'please wait while we verify',
                'chờ một chút'  # "Just a moment" in Vietnamese
            ]
            
            return any(ind in page_source for ind in strict_indicators)
        except:
            return False
    
    def _wait_for_cloudflare(self, timeout: int = 60) -> bool:
        """Wait for Cloudflare challenge to be solved (manual or auto)"""
        self.log("⏳ Đang chờ vượt Cloudflare... (tự động hoặc bấm checkbox)")
        start = time.time()
        while time.time() - start < timeout:
            if not self._is_cloudflare_challenge():
                self.log("✅ Đã vượt Cloudflare!")
                time.sleep(2)
                return True
            time.sleep(2)
        self.log("⚠️ Timeout chờ Cloudflare")
        return False
    
    def _navigate_back_to_create(self):
        """Navigate back to create page after viewing/downloading content"""
        self.log("🔙 Quay lại trang tạo...")
        
        try:
            # Method 1: Press ESC to close any modal/overlay
            try:
                body = self.driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.ESCAPE)
                time.sleep(1)
                
                # Check if back on create page
                if self._find_prompt_input():
                    return True
            except:
                pass
            
            # Method 2: Click the Sora logo to go home
            try:
                logo = self.driver.find_element(By.CSS_SELECTOR, 
                    'a[href="/"], [aria-label="Sora"], [aria-label="Home"]')
                if logo.is_displayed():
                    logo.click()
                    time.sleep(2)
                    if self._find_prompt_input():
                        return True
            except:
                pass
            
            # Method 3: Navigate directly to base URL
            self.driver.get(self.BASE_URL)
            time.sleep(2)
            
            return self._find_prompt_input() is not None
            
        except Exception as e:
            self.log(f"⚠️ Error navigating back: {e}")
            # Fallback: just navigate to base URL
            self.driver.get(self.BASE_URL)
            time.sleep(2)
            return False
    
    def _find_prompt_input(self):
        """Find the prompt input field - Sora uses 'Describe your video...'"""
        selectors = [
            'textarea[placeholder*="Describe"]',
            'textarea[placeholder*="video"]',
            'div[contenteditable="true"]',
            '[role="textbox"]',
            'textarea',
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        return elem
            except Exception:
                continue
        return None
    
    # ==================== IMAGE UPLOAD ====================
    
    def upload_image(self, image_path: str) -> bool:
        """
        Upload reference image with proper modal handling.
        """
        if not image_path or not os.path.exists(image_path):
            self.log("⚠️ Không có ảnh để upload")
            return False
            
        self.log(f"📤 Đang upload ảnh: {os.path.basename(image_path)}")
        
        try:
            # Step 1: Find file input
            file_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
            
            if not file_inputs:
                self.log("⚠️ Không tìm thấy input file")
                return False
            
            # Make input visible and send file
            for file_input in file_inputs:
                try:
                    self.driver.execute_script("""
                        arguments[0].style.cssText = 'display:block !important; opacity:1 !important; visibility:visible !important; position:absolute !important;';
                    """, file_input)
                    
                    file_input.send_keys(image_path)
                    self.log("📤 Đã chọn file, đang chờ modal...")
                    break
                except Exception:
                    continue
            
            # Step 2: Wait for modal and handle it
            time.sleep(2)
            
            modal_result = self._handle_media_upload_agreement()
            
            if modal_result:
                self.log("✅ Upload ảnh hoàn tất")
                time.sleep(2)  # Wait for image to fully load
                return True
            else:
                # Modal might not appear if already agreed before
                # BUT we need to verify the image was actually uploaded
                self.log("⚠️ Modal không xuất hiện, kiểm tra xem ảnh đã upload chưa...")
                time.sleep(2)
                
                # Check if image preview appears in the storyboard/input area
                if self._verify_image_uploaded():
                    self.log("✅ Ảnh đã được upload (không cần modal)")
                    return True
                else:
                    self.log("❌ Ảnh CHƯA được upload - cần xử lý modal")
                    return False
                
        except Exception as e:
            self.log(f"❌ Lỗi upload: {e}")
            return False
    
    def _verify_image_uploaded(self) -> bool:
        """Check if an image has been uploaded by looking for preview elements"""
        try:
            # Look for image preview in the storyboard/input area
            preview_selectors = [
                'img[src*="blob:"]',  # Blob URLs for uploaded images
                'img[src*="data:"]',  # Data URLs
                '[data-testid*="preview"]',
                '[data-testid*="thumbnail"]',
                '.preview img',
                '.storyboard img',
            ]
            
            for selector in preview_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        self.log("✅ Tìm thấy preview ảnh")
                        return True
            
            return False
        except Exception:
            return False
    
    def _handle_media_upload_agreement(self) -> bool:
        """
        Handle the "Media upload agreement" modal.
        
        Steps:
        1. Check if modal is present
        2. Tick all checkboxes (4 total)
        3. Click Accept button
        4. Wait for modal to close
        """
        try:
            # Wait for modal to appear
            time.sleep(2)
            
            # Check if modal exists
            page_source = self.driver.page_source.lower()
            if 'media upload agreement' not in page_source:
                self.log("ℹ️ Không thấy modal agreement (có thể đã đồng ý trước đó)")
                return False
            
            self.log("📋 Tìm thấy modal Media upload agreement")
            
            # Step 1: Find and click ALL checkboxes
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, 
                'input[type="checkbox"], [role="checkbox"]')
            
            checked_count = 0
            for cb in checkboxes:
                try:
                    if cb.is_displayed():
                        # Try regular click first
                        try:
                            cb.click()
                            checked_count += 1
                        except Exception:
                            # Fallback to JS click
                            self.driver.execute_script("arguments[0].click();", cb)
                            checked_count += 1
                        time.sleep(0.3)
                except Exception:
                    pass
            
            self.log(f"✅ Đã tick {checked_count} checkbox")
            time.sleep(1)
            
            # Step 2: Find and click Accept button using XPath (more reliable for text matching)
            accept_clicked = False
            
            # Try XPath first - most reliable for finding by text
            try:
                accept_btn = self.driver.find_element(By.XPATH, 
                    "//button[normalize-space(text())='Accept' or normalize-space(text())='Agree']")
                if accept_btn.is_displayed() and accept_btn.is_enabled():
                    accept_btn.click()
                    accept_clicked = True
                    self.log("✅ Đã click Accept")
            except Exception:
                pass
            
            # Fallback: loop through all buttons
            if not accept_clicked:
                all_btns = self.driver.find_elements(By.TAG_NAME, 'button')
                for btn in all_btns:
                    try:
                        btn_text = btn.text.lower().strip()
                        if btn_text == 'accept' or btn_text == 'agree':
                            if btn.is_displayed() and btn.is_enabled():
                                btn.click()
                                accept_clicked = True
                                self.log("✅ Đã click Accept")
                                break
                    except Exception:
                        continue
            
            if not accept_clicked:
                self.log("⚠️ Không tìm thấy nút Accept")
                return False
            
            # Step 3: Wait for modal to close
            time.sleep(3)
            
            # Verify modal closed
            for _ in range(10):
                page_source = self.driver.page_source.lower()
                if 'media upload agreement' not in page_source:
                    self.log("✅ Modal đã đóng, ảnh đã upload xong")
                    return True
                time.sleep(1)
            
            return True
            
        except Exception as e:
            self.log(f"⚠️ Lỗi xử lý modal: {e}")
            return False
    
    # ==================== PROMPT INPUT ====================
    
    def enter_prompt(self, prompt: str) -> bool:
        """Enter prompt text into the input field"""
        self.log(f"📝 Nhập prompt: {prompt[:50]}...")
        
        try:
            input_elem = self._find_prompt_input()
            if not input_elem:
                self.log("❌ Không tìm thấy ô nhập prompt")
                return False
            
            # Scroll into view
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", input_elem)
            time.sleep(0.5)
            
            # Method 1: ActionChains (most reliable)
            try:
                actions = ActionChains(self.driver)
                actions.click(input_elem)
                actions.pause(0.3)
                # Clear existing content
                actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
                actions.send_keys(Keys.DELETE)
                actions.pause(0.2)
                # Type new prompt
                actions.send_keys(prompt)
                actions.perform()
                
                time.sleep(0.5)
                self.log("✅ Đã nhập prompt")
                return True
            except Exception as e1:
                self.log(f"⚠️ ActionChains failed: {e1}")
            
            # Method 2: JavaScript injection
            try:
                tag_name = input_elem.tag_name.lower()
                if tag_name in ('textarea', 'input'):
                    self.driver.execute_script("""
                        arguments[0].value = arguments[1];
                        arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                        arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                    """, input_elem, prompt)
                else:
                    # For contenteditable
                    self.driver.execute_script("""
                        arguments[0].innerText = arguments[1];
                        arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                    """, input_elem, prompt)
                
                time.sleep(0.5)
                self.log("✅ Đã nhập prompt (JS)")
                return True
            except Exception as e2:
                self.log(f"❌ JavaScript failed: {e2}")
                return False
                
        except Exception as e:
            self.log(f"❌ Lỗi nhập prompt: {e}")
            return False
    
    # ==================== GENERATE ====================
    
    def click_generate(self) -> bool:
        """Click the generate/submit button (arrow button ↑)"""
        self.log("🚀 Nhấn Generate...")
        
        time.sleep(1)
        
        try:
            # Get window height for bottom bar detection
            window_height = self.driver.execute_script("return window.innerHeight")
            bottom_threshold = window_height - 150
            
            # Method 1: Find by type=submit
            try:
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                if submit_btn.is_displayed() and submit_btn.is_enabled():
                    submit_btn.click()
                    self.log("✅ Đã click Generate")
                    time.sleep(2)
                    return True
            except Exception:
                pass
            
            # Method 2: Find arrow/up button with SVG in bottom bar
            try:
                buttons_with_svg = self.driver.find_elements(By.XPATH, "//button[.//svg]")
                
                for btn in buttons_with_svg:
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            location = btn.location
                            # Only click buttons in bottom bar
                            if location.get('y', 0) > bottom_threshold:
                                btn.click()
                                self.log("✅ Đã click Generate (SVG button)")
                                time.sleep(2)
                                return True
                    except Exception:
                        continue
            except Exception:
                pass
            
            # Method 3: Press Enter key
            try:
                input_elem = self._find_prompt_input()
                if input_elem:
                    input_elem.send_keys(Keys.ENTER)
                    self.log("✅ Đã nhấn Enter để submit")
                    time.sleep(2)
                    return True
            except Exception:
                pass
                
            self.log("❌ Không thể click Generate")
            return False
            
        except Exception as e:
            self.log(f"❌ Lỗi click Generate: {e}")
            return False
    
    # ==================== VIDEO SETTINGS ====================
    
    def configure_video_settings(self, type: str = None, aspect_ratio: str = None, resolution: str = None, 
                                  duration: str = None, variations: int = None) -> bool:
        """
        Configure video settings before generating.
        
        Args:
            type: "image" or "video" (media type)
            aspect_ratio: "16:9", "3:2", "1:1", "2:3", "9:16"
            resolution: "1080p", "720p", "480p"
            duration: "20s", "15s", "10s", "5s" or "20", "15", "10", "5"
            variations: 4, 2, 1 (number of video variations)
        """
        self.log("⚙️ Đang cấu hình video settings...")
        
        try:
            # Type (must be configured FIRST)
            if type:
                self._set_dropdown_option(type, "type")
                time.sleep(0.5)
            
            # Aspect Ratio
            if aspect_ratio:
                self._set_dropdown_option(aspect_ratio, "aspect")
                time.sleep(0.5)
            
            # Resolution (Only for Video)
            if resolution:
                if type and "image" in type.lower():
                     self.log("  ℹ️ Skip Resolution (Not available for Image)")
                else:
                     self._set_dropdown_option(resolution, "resolution")
                     time.sleep(0.5)
            
            # Duration (Only for Video)
            if duration:
                if type and "image" in type.lower():
                     self.log("  ℹ️ Skip Duration (Not available for Image)")
                else:
                     # Normalize duration format (remove 's' or 'seconds')
                     dur_text = duration.replace('s', '').replace('seconds', '').strip()
                     dur_text = f"{dur_text} seconds" if dur_text.isdigit() else duration
                     self._set_dropdown_option(dur_text, "duration")
                     time.sleep(0.5)
            
            # Variations
            if variations:
                suffix = "video"
                if type and "image" in type.lower():
                    suffix = "image"
                
                # Handle plural "videos"/"images" (usually 1 is singular, others plural)
                # But UI screenshot shows "4 images", "2 images", "1 image"
                # And "4 videos", "2 videos", "1 video"
                
                # Check for just number in case passing "videos" failed previously
                is_plural = str(variations) != "1"
                suffix += "s" if is_plural else ""
                
                var_text = f"{variations} {suffix}"
                self._set_dropdown_option(var_text, "variations")
                time.sleep(0.5)
            
            self.log("✅ Đã cấu hình video settings")
            return True
            
        except Exception as e:
            self.log(f"⚠️ Lỗi cấu hình settings: {e}")
            return False
    
    def _set_dropdown_option(self, value: str, option_type: str) -> bool:
        """
        Click on a dropdown button in the bottom bar, wait for modal, then select option.
        
        Flow:
        1. Find and click the dropdown button (Type, Aspect, Duration, Resolution, Variations)
        2. Wait for dropdown modal to appear
        3. Find and click the option with EXACT text match
        """
        try:
            # ===== STEP 1: FIND AND CLICK DROPDOWN BUTTON =====
            window_height = self.driver.execute_script("return window.innerHeight")
            bottom_threshold = window_height - 150
            
            all_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button, [role="button"], [role="combobox"]')
            
            # Filter to buttons in bottom bar
            bottom_bar_buttons = []
            for btn in all_buttons:
                try:
                    if btn.is_displayed():
                        location = btn.location
                        if location.get('y', 0) > bottom_threshold:
                            bottom_bar_buttons.append(btn)
                except:
                    continue
            
            self.log(f"  🔍 Tìm thấy {len(bottom_bar_buttons)} nút trong bottom bar")
            
            # Find the right button to click based on option_type
            button_clicked = False
            for btn in bottom_bar_buttons:
                try:
                    btn_text = btn.text.lower().strip()
                    aria_label = (btn.get_attribute('aria-label') or "").lower()
                    
                    should_click = False
                    
                    if option_type == "type":
                        # Type button shows current selection: "Image" or "Video"
                        if btn_text in ["image", "video"] or "type" in aria_label or "media" in aria_label:
                            should_click = True
                            
                    elif option_type == "aspect":
                        # Aspect button shows current ratio: "16:9", "3:2", etc.
                        if any(r in btn_text for r in ['16:9', '9:16', '1:1', '3:2', '2:3']) or "aspect" in aria_label or "ratio" in aria_label:
                            should_click = True
                            
                    elif option_type == "duration":
                        # Duration button shows: "5s", "10s", "15s", "20s"
                        if ('s' in btn_text and any(d in btn_text for d in ['5', '10', '15', '20']) and 'v' not in btn_text) or "duration" in aria_label:
                            should_click = True
                            
                    elif option_type == "resolution":
                        # Resolution button shows: "480p", "720p", "1080p"
                        if any(r in btn_text for r in ['480', '720', '1080', '360']) or "resolution" in aria_label or "quality" in aria_label:
                            should_click = True
                            
                    elif option_type == "variations":
                        # Variations button shows: "1v", "2v", "4v" or "1 video", "4 images", etc.
                        # Check for compact format (1v, 2v, 4v) or full format (1 video, 2 images)
                        has_digit = any(c.isdigit() for c in btn_text)
                        is_compact_v = ('v' in btn_text and has_digit and btn_text.replace(' ', '').endswith('v'))
                        is_full_format = has_digit and any(w in btn_text for w in ['video', 'image', 'videos', 'images'])
                        if is_compact_v or is_full_format or "variation" in aria_label or "count" in aria_label:
                            should_click = True
                    
                    if should_click:
                        btn.click()
                        self.log(f"  �️ Clicked {option_type} button: {btn_text or aria_label}")
                        button_clicked = True
                        break
                        
                except Exception:
                    continue
            
            if not button_clicked:
                self.log(f"  ⚠️ Không tìm thấy nút {option_type}")
                
                # For variations: Try fallback JavaScript method
                if option_type == "variations":
                    self.log(f"  🔄 Thử tìm variations button bằng JS...")
                    try:
                        # Look for combobox buttons with pattern like "1v", "2v", "4v"
                        js_find_variations_btn = """
                        (function() {
                            var buttons = document.querySelectorAll('button[role="combobox"]');
                            for (var i = 0; i < buttons.length; i++) {
                                var btn = buttons[i];
                                var text = btn.textContent.trim();
                                // Match patterns like "1v", "2v", "4v" or "1 video", "2 images"
                                if (/^\\d+v$/i.test(text.replace(/\\s+/g, '')) || 
                                    /\\d+\\s*(video|image|videos|images)/i.test(text)) {
                                    btn.click();
                                    return 'clicked: ' + text;
                                }
                            }
                            return 'not_found';
                        })();
                        """
                        result = self.driver.execute_script(js_find_variations_btn)
                        if result and result != 'not_found':
                            self.log(f"  ✓ Tìm thấy variations button bằng JS: {result}")
                            button_clicked = True
                    except Exception as e:
                        self.log(f"  ⚠️ JS fallback error: {e}")
                
                # If still not clicked after fallback, return False
                if not button_clicked:
                    return False
            
            # ===== STEP 2: WAIT FOR DROPDOWN MODAL =====
            time.sleep(0.8)  # Wait for modal animation
            
            # ===== STEP 3: FIND AND CLICK THE OPTION =====
            # Normalize the value we're looking for
            search_value = value.lower().strip()
            
            # Special handling for different option types
            if option_type == "type":
                # Just "image" or "video"
                if "image" in search_value:
                    search_value = "image"
                elif "video" in search_value:
                    search_value = "video"
                    
            elif option_type == "duration":
                # UI shows "X seconds" format
                # Input might be "5s", "10s", "5 seconds", etc.
                dur_num = ''.join(c for c in search_value if c.isdigit())
                if dur_num:
                    search_value = f"{dur_num} seconds"
                    
            elif option_type == "resolution":
                # UI shows "1080p", "720p", "480p" with extra text
                # Just need to match the resolution part
                for res in ['1080p', '720p', '480p', '360p']:
                    if res.replace('p', '') in search_value:
                        search_value = res
                        break
                        
            elif option_type == "variations":
                # UI shows "4 images", "2 images", "1 image" for image type
                # or "4 videos", "2 videos", "1 video" for video type
                # Value passed from configure_video_settings is already formatted
                # Just ensure clean format without extra spaces
                search_value = ' '.join(search_value.split())  # Normalize whitespace
            
            self.log(f"  🔎 Tìm option: '{search_value}'")
            
            # Method 1: Find by role="option" or role="menuitem"
            option_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[role="option"], [role="menuitem"], [role="menuitemradio"], [role="listbox"] > div')
            
            for opt in option_elements:
                try:
                    if not opt.is_displayed():
                        continue
                    
                    # Get text and normalize whitespace (icons can cause extra spaces)
                    opt_text = ' '.join(opt.text.lower().split())
                    
                    # Log visible options for debugging
                    if opt_text and len(opt_text) < 40:
                        self.log(f"    📋 Option visible: '{opt_text}'")
                    
                    # EXACT match or starts with (for resolution which has "8x slower" suffix)
                    if opt_text == search_value or opt_text.startswith(search_value + ' ') or opt_text.startswith(search_value):
                        opt.click()
                        self.log(f"  ✓ Set {option_type}: {value}")
                        time.sleep(0.3)
                        return True
                        
                except Exception:
                    continue
            
            # Method 2: JavaScript - find ALL visible elements and match text
            js_find_and_click = f"""
            (function() {{
                var searchValue = '{search_value}';
                
                // Helper function to normalize whitespace
                function normalizeText(text) {{
                    return text.replace(/\\s+/g, ' ').trim().toLowerCase();
                }}
                
                // Get all elements on page
                var allElements = document.querySelectorAll('*');
                
                // First pass: exact match
                for (var i = 0; i < allElements.length; i++) {{
                    var el = allElements[i];
                    var rect = el.getBoundingClientRect();
                    
                    // Must be visible and in upper part of screen (dropdown area)
                    if (rect.width === 0 || rect.height === 0) continue;
                    if (rect.top > window.innerHeight * 0.85) continue; // Skip bottom bar
                    if (rect.top < 0) continue; // Skip off-screen
                    
                    var style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    
                    // Get text content without nested elements' text (direct text only)
                    var directText = '';
                    for (var j = 0; j < el.childNodes.length; j++) {{
                        if (el.childNodes[j].nodeType === 3) {{ // TEXT_NODE
                            directText += el.childNodes[j].textContent;
                        }}
                    }}
                    directText = normalizeText(directText);
                    
                    // Also try full text content with normalized whitespace
                    var fullText = normalizeText(el.textContent);
                    
                    // EXACT match
                    if (directText === searchValue || fullText === searchValue) {{
                        el.click();
                        return 'exact: ' + fullText.substring(0, 30);
                    }}
                    
                    // Starts with match (for "1080p 8x slower" matching "1080p")
                    if (fullText.startsWith(searchValue + ' ') || fullText.startsWith(searchValue)) {{
                        // Verify it's a clickable option (not just any element)
                        var role = el.getAttribute('role');
                        var isOption = role === 'option' || role === 'menuitem' || role === 'menuitemradio';
                        var isClickable = el.tagName === 'BUTTON' || el.tagName === 'A' || el.onclick || el.style.cursor === 'pointer';
                        
                        if (isOption || isClickable || el.closest('[role="listbox"]') || el.closest('[role="menu"]')) {{
                            el.click();
                            return 'startswith: ' + fullText.substring(0, 30);
                        }}
                    }}
                }}
                
                // Second pass: partial match (search value contained in element text)
                for (var i = 0; i < allElements.length; i++) {{
                    var el = allElements[i];
                    var rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;
                    if (rect.top > window.innerHeight * 0.85) continue;
                    if (rect.top < 0) continue;
                    
                    var fullText = normalizeText(el.textContent);
                    
                    // Text must contain search value AND be relatively short (option-like)
                    if (fullText.includes(searchValue) && fullText.length < 40) {{
                        var role = el.getAttribute('role');
                        if (role === 'option' || role === 'menuitem' || role === 'menuitemradio') {{
                            el.click();
                            return 'partial: ' + fullText.substring(0, 30);
                        }}
                    }}
                }}
                
                return 'not_found';
            }})();
            """
            
            try:
                result = self.driver.execute_script(js_find_and_click)
                if result and result != 'not_found':
                    self.log(f"  ✓ Set {option_type}: {value} ({result})")
                    time.sleep(0.3)
                    return True
                else:
                    self.log(f"  ⚠️ Không tìm thấy option: {search_value}")
            except Exception as e:
                self.log(f"  ⚠️ JS error: {e}")
            
            # Close the dropdown if option not found (press Escape or click elsewhere)
            try:
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.3)
                self.log(f"  🔽 Đã đóng dropdown")
            except:
                pass
            
            return False
            
        except Exception as e:
            self.log(f"⚠️ Không thể set {option_type}: {e}")
            return False
    
    def wait_for_generation(self, prompt: str = None, timeout: int = 300, expected_count: int = 1) -> bool:
        """
        Wait for generation to complete based on item count or prompt matching.
        
        Args:
            prompt: Prompt content to verify correctness (optional)
            timeout: Max wait time in seconds
            expected_count: Number of variations expected to find (default 1)
        """
        self.log(f"⏳ Đang chờ tạo kết quả... (timeout: {timeout}s, expected: {expected_count} items)")
        start_time = time.time()
        
        # Wait for submission to process
        time.sleep(5)
        
        # Navigate to library page
        self.log("📂 Chuyển sang trang Library để theo dõi tiến trình...")
        self.driver.get(f"{self.BASE_URL}/library")
        time.sleep(3)
        
        # Snapshot current item IDs to identify NEW items uniquely
        initial_ids = set()
        try:
            # Look for both Success (/g/gen_) and Failed (/t/task_) items
            link_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/g/gen_"], a[href*="/t/task_"]')
            initial_ids = {el.get_attribute('href') for el in link_elements if el.get_attribute('href')}
        except: pass
        
        # Count initial items
        initial_count = self._count_video_items()
        self.log(f"📊 Số item hiện có: {initial_count}")
        
        last_count = initial_count
        refresh_interval = 15  # Refresh every 15 seconds to avoid Cloudflare
        last_refresh_time = time.time() - refresh_interval 
        
        while time.time() - start_time < timeout:
            try:
                elapsed = int(time.time() - start_time)
                current_time = time.time()
                
                # IMPORTANT: Priority Check - Find item matching prompt immediately
                if prompt:
                    matches = self._find_matching_items(prompt)
                    
                    # Filter for NEW items only (not in initial snapshot)
                    new_matches = []
                    for m in matches:
                        try:
                            href = m.get_attribute("href")
                            if not href and m.tag_name != "a":
                                try: href = m.find_element(By.TAG_NAME, "a").get_attribute("href")
                                except: pass
                            
                            # If we can't find href, assume it's new (unsafe?) or skip?
                            # ALL items must be NEW (not in initial_ids) to be selected
                            if href and href in initial_ids:
                                continue
                            new_matches.append(m)
                        except: pass
                    
                    if new_matches:
                        # Check if items are ready (not loading)
                        is_ready = True
                        for item in new_matches:
                            try:
                                # Check for loading indicators in text
                                txt = (item.text + " " + item.get_attribute("innerText")).lower()
                                loading_markers = ["%", "generating", "queue", "processing"]
                                if any(marker in txt for marker in loading_markers):
                                    is_ready = False
                                    self.log(f"⏳ Item đang xử lý... Chờ thêm.")
                                    break
                            except:
                                # Stale element, assume not ready or re-find needed
                                is_ready = False
                                break
                                
                        if is_ready:
                            # Check if enough items found
                            if len(new_matches) < expected_count:
                                self.log(f"⚠️ Mới tìm thấy {len(new_matches)}/{expected_count} items. Đợi thêm...")
                                continue
                            self.log(f"✅ Tìm thấy {len(new_matches)} kết quả mới đã hoàn thành!")
                            return True
                        # If not ready, continue waiting loop (refresh will happen)
                
                # Refresh page every 15 seconds
                if current_time - last_refresh_time >= refresh_interval:
                    self.log(f"⏳ Đã chờ {elapsed}s... Refreshing...")
                    self.driver.refresh()
                    time.sleep(3)
                    # Create JS scroll to top to ensure new items are rendered in virtual list
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(1)
                    last_refresh_time = time.time()
                    
                    # 1. SPECIAL CHECK: Any NEW failed/error items? (Don't rely on prompt match for errors)
                    try:
                        failed_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/t/task_"]')
                        for link in failed_links:
                            href = link.get_attribute("href")
                            if href and href not in initial_ids:
                                self.log(f"⚠️ Phát hiện tác vụ lỗi MỚI (ID: {href[-10:]})! Dừng chờ.")
                                return True # Treat as completion (will be handled as error in download)
                    except: pass

                    # 2. Re-check prompt matches immediately after refresh
                    if prompt:
                        matches = self._find_matching_items(prompt)
                        # Filter for NEW items only
                        new_matches = []
                        for m in matches:
                            try:
                                href = m.get_attribute("href")
                                if not href:
                                    try: href = m.find_element(By.TAG_NAME, "a").get_attribute("href")
                                    except: pass
                                
                                # ALL items must be NEW (not in initial_ids) to be selected
                                if href and href in initial_ids:
                                    continue
                                new_matches.append(m)
                            except: pass

                        if new_matches:
                            # Check if enough items found
                            if len(new_matches) < expected_count:
                                self.log(f"⚠️ Mới tìm thấy {len(new_matches)}/{expected_count} items. Đợi thêm...")
                                continue

                            # Check if error item
                            is_error = False
                            for m in new_matches:
                                try:
                                    href = m.get_attribute("href") or ""
                                    txt = m.text.lower()
                                    if "/t/task_" in href or "error" in txt:
                                        self.log("⚠️ Phát hiện kết quả bị Lỗi!")
                                        return True # Return true to proceed (and process_batch_download will handle failure)
                                except: pass
                            
                            self.log(f"✅ Tìm thấy {len(new_matches)} kết quả mới khớp prompt!")
                            return True
                
                # Check notification bell
                if self._check_notification_bell():
                    self.log("🔔 Notification bell có badge!")
                    time.sleep(1)
                    self.driver.refresh()
                    time.sleep(2)
                
                # Fallback: Count items (only if no prompt provided, or as debug)
                if not prompt:
                    current_count = self._count_video_items()
                    if current_count > initial_count:
                        self.log("✅ Có kết quả mới (dựa trên số lượng)!")
                        return True
                
            except Exception as e:
                self.log(f"⚠️ Check error: {e}")
            
            time.sleep(2)
        
        self.log("⏰ Timeout - chưa tìm thấy kết quả khớp")
        return False
    
    def _find_matching_items(self, prompt: str) -> list:
        """Find ALL video/image items that match the prompt"""
        try:
            # Normalize prompt: take first 100 chars (increased from 30), lowercase
            search_text = prompt[:100].lower().strip()
            
            # Selectors prioritized by DOM structure (Grid -> List)
            # This ensures we check the Top Grid (Failed/Active) and Top of History first
            selectors = [
                # 1. Top Grid (Active/Failed Tasks)
                'div.grid a[href*="/t/task_"]',
                'div.grid a[href*="/g/gen_"]',
                
                # 2. Virtual List (Target items inside data-index containers)
                # These are usually ordered by most recent
                'div[data-index] a[href*="/g/gen_"]',
                'div[data-index] a[href*="/t/task_"]',
                
                # 3. Fallback General Selectors (for older/different layouts)
                'a[href*="/g/gen_"]',        # Success link
                'a[href*="/t/task_"]',       # Failed task link
                '[class*="tile"]',           # Old tile structure
                '[data-testid*="item"]'
            ]
            
            found_items = []
            
            for selector in selectors:
                items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if not items: continue

                # Check top 10 items (newest usually first)
                for item in items[:15]:
                    if not item.is_displayed():
                        continue
                        
                    # Skip if already added
                    if item in found_items:
                        continue
                        
                    try:
                        # Strategy: Get full text context
                        text_content = ""
                        
                        # 1. If item is link, check ancestors for context
                        if item.tag_name == 'a':
                            try:
                                # Try to find a container div (go up multiple levels to cover grid/list structures)
                                # Level 1 (Tile/Group)
                                container_1 = item.find_element(By.XPATH, "./ancestor::div[contains(@class, 'flex') or contains(@class, 'group')][1]")
                                text_content += container_1.get_attribute('innerText')
                                
                                # Level 2 (Grid/Row)
                                container_2 = item.find_element(By.XPATH, "./ancestor::div[contains(@class, 'flex') or contains(@class, 'group')][2]")
                                text_content += " " + container_2.get_attribute('innerText')
                                
                                # Level 3 (Main Container - usually contains both Tile and Prompt info)
                                container_3 = item.find_element(By.XPATH, "./ancestor::div[contains(@class, 'flex') or contains(@class, 'group')][3]")
                                text_content += " " + container_3.get_attribute('innerText')
                            except:
                                pass
                        
                        # 2. Add item's own text
                        text_content += " " + item.text + " " + item.get_attribute('innerText')
                        
                        # 3. Check text match
                        if search_text in text_content.lower():
                            found_items.append(item)
                            continue
                            
                        # 4. Fallback: Check Alt Text of internal image
                        try:
                            img = item.find_element(By.TAG_NAME, 'img')
                            alt = img.get_attribute('alt')
                            if alt and search_text in alt.lower():
                                found_items.append(item)
                                continue
                        except:
                            pass
                            
                    except:
                        continue
            
            # Return list of matches
            return found_items
            
        except Exception as e:
            return []

    def _process_batch_download(self, prompt: str, variations: int, output_base_path: str) -> bool:
        """Download multiple variations looping through items"""
        self.log(f"📥 Bắt đầu download batch ({variations} items)...")
        success_count = 0
        
        # Variations can be int or str. Parse it safely
        try:
            limit = int(str(variations).split()[0])
        except:
            limit = 1
            
        # Limit to reasonable number
        limit = max(1, min(limit, 4))
        
        # Step 6: Wait for generation
        # Pass variations count so we wait for ALL items to appear
        wait_success = self.wait_for_generation(prompt=prompt, expected_count=variations)
        
        if not wait_success:
            self.log("❌ Timeout chờ tạo video")
            # Try to recover by navigating back
            self._navigate_back_to_create()
            time.sleep(3) # Wait for library to reload
            return False
        
        for i in range(limit):
            # 1. Find items matching prompt - Must RE-FIND every time because of page navigation
            items = self._find_matching_items(prompt)
            
            # If not enough items found, stop
            if not items or i >= len(items):
                self.log(f"⚠️ Chỉ tìm thấy {len(items)} items khớp prompt (cần {limit})")
                if i > 0: break # Downloaded some already
                
            # Get the correct item (newest first? Sora puts newest at top/left)
            # Index 0 is newest. If we want to download all, we should iterate.
            # Usually variations appear as adjacent items.
            target_item = items[i]
            
            try:
                # Check for error status (Task Failed)
                href = target_item.get_attribute("href") or ""
                if "/t/task_" in href:
                    self.log(f"⚠️ Item {i+1} là tác vụ lỗi (Task Failed). Bỏ qua.")
                    continue

                # 2. Click item using JS to avoid interception
                self.log(f"📹 Opening item {i+1}/{limit}...")
                self.driver.execute_script("arguments[0].click();", target_item)
                time.sleep(3)
                
                # 3. Determine filename
                # output_base_path is like ".../tom/tom"
                # If limit > 1, append index: ".../tom/tom_01.mp4"
                # If limit == 1, keep as is: ".../tom/tom.mp4"
                
                current_output = output_base_path
                if limit > 1:
                     current_output = f"{output_base_path}_{i+1:02d}"
                
                # Append extension (download_video will fix if image)
                current_output += ".mp4"
                
                # 4. Download
                if self.download_video(current_output):
                    success_count += 1
                    
                # 5. Back to library
                self._navigate_back_to_create()
                time.sleep(3) # Wait for library to reload
                
            except Exception as e:
                self.log(f"⚠️ Error downloading item {i+1}: {e}")
                self._navigate_back_to_create()
                time.sleep(2)
                
        return success_count > 0

    def _count_video_items(self) -> int:
        """Count number of video items on library page"""
        try:
            # Method 1: Tìm các link đến video (href chứa /g/gen_ hoặc /library)
            video_links = self.driver.find_elements(By.CSS_SELECTOR,
                'a[href*="/g/gen_"], a[href*="/library"]')
            
            # Method 2: Tìm các thumbnail images (có src chứa videos.openai.com)
            video_thumbnails = self.driver.find_elements(By.CSS_SELECTOR,
                'img[src*="videos.openai.com"], img[src*="vg-assets"]')
            
            # Method 3: Tìm các tile/container chứa video
            video_tiles = self.driver.find_elements(By.CSS_SELECTOR,
                '[class*="tile"], [class*="group/tile"], [data-index]')
            
            # Lấy số lượng lớn nhất từ các method (để đảm bảo đếm đúng)
            counts = []
            
            # Đếm video links (loại bỏ duplicate)
            unique_links = set()
            for link in video_links:
                try:
                    if link.is_displayed():
                        href = link.get_attribute('href')
                        if href and ('/g/gen_' in href or '/library' in href):
                            unique_links.add(href)
                except:
                    continue
            counts.append(len(unique_links))
            
            # Đếm thumbnails
            visible_thumbnails = sum(1 for thumb in video_thumbnails 
                                   if thumb.is_displayed() and 
                                   ('videos.openai.com' in thumb.get_attribute('src') or 
                                    'vg-assets' in thumb.get_attribute('src')))
            counts.append(visible_thumbnails)
            
            # Đếm tiles có chứa video (có img hoặc link bên trong)
            video_tile_count = 0
            for tile in video_tiles:
                try:
                    if tile.is_displayed():
                        # Kiểm tra xem tile có chứa video thumbnail không
                        imgs = tile.find_elements(By.CSS_SELECTOR, 
                            'img[src*="videos.openai.com"], img[src*="vg-assets"]')
                        links = tile.find_elements(By.CSS_SELECTOR,
                            'a[href*="/g/gen_"]')
                        if imgs or links:
                            video_tile_count += 1
                except:
                    continue
            counts.append(video_tile_count)
            
            # Trả về số lượng lớn nhất (để đảm bảo không bỏ sót)
            result = max(counts) if counts else 0
            return result
            
        except Exception as e:
            self.log(f"⚠️ Lỗi đếm video: {e}")
            return 0
    
    def _check_notification_bell(self) -> bool:
        """Check if notification bell has a badge (indicating video done)"""
        try:
            # Look for notification bell with badge/count
            # Bell icon usually has a number or dot when there's a notification
            
            # Method 1: Look for notification badge/count near bell icon
            badges = self.driver.find_elements(By.CSS_SELECTOR,
                '[aria-label*="notification"] [class*="badge"], '
                '[aria-label*="notification"] [class*="count"], '
                'button[aria-label*="Notification"] span, '
                '[class*="notification"] [class*="indicator"]')
            
            for badge in badges:
                try:
                    if badge.is_displayed():
                        text = badge.text.strip()
                        if text and (text.isdigit() or text == '•'):
                            return True
                except Exception:
                    continue
            
            # Method 2: Check if bell area has any visible badge
            bell_buttons = self.driver.find_elements(By.XPATH,
                "//button[contains(@aria-label, 'notification') or contains(@aria-label, 'Notification')]")
            
            for bell in bell_buttons:
                try:
                    if bell.is_displayed():
                        # Check for any child element that looks like a badge
                        children = bell.find_elements(By.CSS_SELECTOR, 'span, div')
                        for child in children:
                            text = child.text.strip()
                            if text and text.isdigit():
                                return True
                except Exception:
                    continue
            
            return False
        except Exception:
            return False
    
    def _has_recent_video(self, seconds: int) -> bool:
        """Check if there's a video created within last X seconds"""
        try:
            # Look for timestamp text on page
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            # Get current time
            import re
            from datetime import datetime
            
            # Look for time patterns like "1:14pm", "13:14"
            now = datetime.now()
            current_minute = now.hour * 60 + now.minute
            
            # Simple check: if page has "New Video" text, consider it new
            if 'New Video' in page_text:
                return True
            
            return False
        except Exception:
            return False
    
    def _click_first_video(self):
        """Click on the first/newest video in library (newest videos appear first)"""
        try:
            # Wait a bit for page to fully load
            time.sleep(2)
            
            # Find clickable video items - try multiple selectors
            video_items = []
            
            # Method 1: Look for video grid items
            items1 = self.driver.find_elements(By.CSS_SELECTOR,
                '[class*="media"], [class*="item"], [class*="card"], [class*="thumbnail"]')
            video_items.extend(items1)
            
            # Method 2: Look for elements containing video/img
            items2 = self.driver.find_elements(By.CSS_SELECTOR,
                'a[href*="/library"], a[href*="/video"]')
            video_items.extend(items2)
            
            # Remove duplicates and filter visible items
            seen = set()
            visible_items = []
            for item in video_items:
                try:
                    item_id = id(item)
                    if item_id not in seen and item.is_displayed():
                        seen.add(item_id)
                        # Check if it has image/video content
                        imgs = item.find_elements(By.CSS_SELECTOR, 'img, video')
                        if imgs:
                            visible_items.append(item)
                except Exception:
                    continue
            
            if not visible_items:
                self.log("⚠️ Không tìm thấy video items")
                return
            
            # Click the first item (newest video is usually first)
            first_item = visible_items[0]
            try:
                # Scroll into view first
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                    first_item)
                time.sleep(0.5)
                
                # Try clicking with JavaScript if normal click fails
                try:
                    first_item.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", first_item)
                
                self.log("📹 Mở video mới nhất để download...")
                time.sleep(3)
                return
            except Exception as e:
                self.log(f"⚠️ Không thể click video đầu tiên: {e}")
                
        except Exception as e:
            self.log(f"⚠️ Không thể click video: {e}")
    
    # ==================== DOWNLOAD ====================
    
    def download_video(self, output_path: str) -> bool:
        """
        Download the generated video from the video detail page.
        
        Strategy:
        1. Look for download button/link on video detail page
        2. If not found, look for video element and get source
        3. Filter out demo/sample URLs
        """
        self.log(f"📥 Đang download video...")
        
        # Log output path for debugging
        self.log(f"📂 Output path: {output_path}")
        
        # Ensure output directory exists
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                self.log(f"✅ Đã tạo/kiểm tra thư mục: {output_dir}")
        except Exception as e:
            self.log(f"⚠️ Lỗi tạo thư mục: {e}")
        
        time.sleep(2)
        
        try:
            download_buttons = self.driver.find_elements(By.XPATH,
                "//button[contains(@aria-label, 'ownload')] | "
                "//*[contains(@class, 'download')] | "
                "//button[.//svg]")
            
            # Filter to buttons in top-right area (download icon location)
            window_width = self.driver.execute_script("return window.innerWidth")
            for btn in download_buttons:
                try:
                    if btn.is_displayed():
                        location = btn.location
                        # Download button is usually in top-right area
                        if location.get('x', 0) > window_width * 0.7 and location.get('y', 0) < 150:
                            btn.click()
                            self.log("✅ Clicked download icon")
                            time.sleep(1)
                            
                            # Now look for "Video" option in the dropdown menu
                            video_options = self.driver.find_elements(By.XPATH,
                                "//button[contains(text(), 'Video')] | "
                                "//a[contains(text(), 'Video')] | "
                                "//*[contains(@class, 'menu')]//*[contains(text(), 'Video')]")
                            
                            for opt in video_options:
                                try:
                                    opt_text = opt.text.strip().lower()
                                    # Click on "Video" but not "Video with Watermark"
                                    if opt.is_displayed() and opt_text == 'video':
                                        opt.click()
                                        self.log("✅ Clicked 'Video' option")
                                        time.sleep(5)  # Wait for download to start
                                        return True
                                except Exception:
                                    continue
                            
                            # If no "Video" option found, try any visible option
                            menu_items = self.driver.find_elements(By.CSS_SELECTOR,
                                '[role="menuitem"], [role="option"]')
                            for item in menu_items:
                                if item.is_displayed() and 'video' in item.text.lower():
                                    if 'watermark' not in item.text.lower():
                                        item.click()
                                        self.log("✅ Clicked video download option")
                                        time.sleep(5)
                                        return True
                except Exception:
                    continue
            
            # Method 2: Find download link directly
            # Method 2: Find download link directly (Any video format)
            download_links = self.driver.find_elements(By.CSS_SELECTOR,
                'a[download], a[href*=".mp4"], a[href*=".mov"], a[href*=".webm"], a[href*="download"]')
            
            for link in download_links:
                if link.is_displayed():
                    href = link.get_attribute('href')
                    if href and self._is_valid_video_url(href):
                        return self._download_from_url(href, output_path)
            
            # Method 3: Get video src directly (but filter demo URLs)
            videos = self.driver.find_elements(By.CSS_SELECTOR, 'video[src], video source[src]')
            for video in videos:
                try:
                    src = video.get_attribute('src')
                    if src and self._is_valid_video_url(src):
                        return self._download_from_url(src, output_path)
                except Exception:
                    continue
            
            # Method 4: Try to find video in network requests via page source
            page_source = self.driver.page_source
            import re
            # Much broader regex for any common video format
            video_urls = re.findall(r'https?://[^\s"\']+\.(?:mp4|mov|webm|mkv)[^\s"\']*', page_source)
            for url in video_urls:
                if self._is_valid_video_url(url):
                    return self._download_from_url(url, output_path)

            # Method 5: Check for generated IMAGE content (if video not found)
            # Sora also generates images, which appear in <img> tags with specific sources
            images = self.driver.find_elements(By.CSS_SELECTOR, 
                'img[src*="videos.openai.com/api/vg-assets/"], img[src*="oaidalle"], img[class*="h-full w-full"]')
            
            for img in images:
                try:
                    if img.is_displayed():
                        src = img.get_attribute('src')
                        if src and src.startswith('http'):
                            # Ensure output path has correct extension
                            base, ext = os.path.splitext(output_path)
                            if ext.lower() in ['.mp4', '.mov', '.webm', '.mkv']:
                                # Switch extension to .png for images
                                image_path = f"{base}.png"
                                self.log(f"🖼️ Detected Image content. Switching extension: {output_path} -> {image_path}")
                                return self._download_from_url(src, image_path)
                            else:
                                return self._download_from_url(src, output_path)
                except Exception:
                    continue
            
            self.log("⚠️ Không tìm thấy link download hợp lệ (Video hoặc Image)")
            return False
            
        except Exception as e:
            self.log(f"❌ Lỗi download: {e}")
            return False
    
    def _is_valid_video_url(self, url: str) -> bool:
        """Check if URL is a valid generated video (not demo/sample)"""
        if not url or not url.startswith('http'):
            return False
        
        # Filter out known demo/sample URLs
        demo_patterns = [
            'starry-sky', 'sample', 'demo', 'example', 
            'placeholder', 'preview', 'thumbnail'
        ]
        
        url_lower = url.lower()
        for pattern in demo_patterns:
            if pattern in url_lower:
                self.log(f"⚠️ Bỏ qua URL demo: {url[:50]}...")
                return False
        
        return True
    
    def _download_from_url(self, url: str, output_path: str) -> bool:
        """Download file from URL"""
        try:
            self.log(f"📥 Downloading từ: {url[:60]}...")
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                self.log(f"📂 Đảm bảo thư mục tồn tại: {output_dir}")
            
            # Normalize path (handle Windows path issues)
            output_path = str(Path(output_path).resolve())
            self.log(f"💾 Lưu file tại: {output_path}")
            
            # Get cookies from browser
            cookies = {}
            for cookie in self.driver.get_cookies():
                cookies[cookie['name']] = cookie['value']
            
            response = requests.get(url, cookies=cookies, stream=True, timeout=120)
            response.raise_for_status()
            
            # Get content length for validation
            content_length = response.headers.get('Content-Length')
            if content_length:
                expected_size = int(content_length)
                self.log(f"📊 Kích thước file: {expected_size / 1024 / 1024:.2f} MB")
            
            # Download file
            downloaded_size = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            # Validate file was saved correctly
            if os.path.exists(output_path):
                actual_size = os.path.getsize(output_path)
                self.log(f"✅ Đã lưu file: {output_path}")
                self.log(f"📊 Kích thước thực tế: {actual_size / 1024 / 1024:.2f} MB")
                
                # Check if file size is reasonable (at least 1KB)
                if actual_size < 1024:
                    self.log(f"⚠️ File quá nhỏ ({actual_size} bytes), có thể download không thành công")
                    return False
                
                # If we know expected size, validate it
                if content_length and abs(actual_size - expected_size) > 1024:
                    self.log(f"⚠️ Kích thước file không khớp (expected: {expected_size}, actual: {actual_size})")
                    return False
                
                return True
            else:
                self.log(f"❌ File không tồn tại sau khi download: {output_path}")
                return False
            
        except Exception as e:
            self.log(f"❌ Download failed: {e}")
            # Clean up partial file if exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    self.log(f"🗑️ Đã xóa file không hoàn chỉnh")
                except Exception:
                    pass
            return False
    
    # ==================== MAIN WORKFLOW ====================
    
    def generate_video(self, prompt: str, image_paths: List[str] = None, output_path: str = "",
                       type: str = None, aspect_ratio: str = None, resolution: str = None,
                       duration: str = None, variations: int = None,
                       timeout: int = 300) -> bool:
    
        # Step 1: Navigate
        if not self.navigate_to_create():
            return False
        time.sleep(2)
        
        # Step 2: Configure video settings ONLY if different from last time
        # Normalize and build current settings dict
        current_settings = {
            "type": str(type).lower().strip() if type else "video",
            "aspect_ratio": str(aspect_ratio).strip() if aspect_ratio else "",
            "resolution": str(resolution).strip() if resolution else "",
            "duration": str(duration).strip() if duration else "",
            "variations": int(variations) if variations else 1
        }
        
        # Compare with last settings - only configure if different
        settings_human = ", ".join([f"{k}={v}" for k, v in current_settings.items() if v])
        
        settings_changed = current_settings != self._last_settings
        
        if settings_changed:
            if not self._last_settings:
                self.log(f"⚙️ Lần đầu cấu hình settings: {settings_human}")
            else:
                self.log(f"⚙️ Settings thay đổi! Diff:")
                for k in current_settings:
                    old_v = self._last_settings.get(k)
                    new_v = current_settings.get(k)
                    if old_v != new_v:
                        self.log(f"    - {k}: '{old_v}' -> '{new_v}'")
        
        if settings_changed and any(current_settings.values()):
            self.log("⚙️ Settings khác với lần trước, đang cấu hình...")
            self.configure_video_settings(
                type=current_settings["type"],
                aspect_ratio=current_settings["aspect_ratio"],
                resolution=current_settings["resolution"],
                duration=current_settings["duration"],
                variations=current_settings["variations"]
            )
            # Cache the new settings
            self._last_settings = current_settings.copy()
            time.sleep(1)
        else:
            self.log("⚙️ Settings giống lần trước, bỏ qua cấu hình")
        
        # Step 3: Upload images (if provided)
        if image_paths:
            for img_path in image_paths:
                if img_path:
                    if not self.upload_image(img_path):
                        self.log(f"⚠️ Upload ảnh thất bại ({os.path.basename(img_path)}), tiếp tục...")
                    time.sleep(1)
        
        # Step 4: Enter prompt
        if not self.enter_prompt(prompt):
            return False
        time.sleep(1)
        
        # Step 5: Click generate
        if not self.click_generate():
            return False
        
        # Step 6 & 7: Wait and Download
        download_success = False
        
        if output_path:
            # Use new batch download logic (HANDLES WAITING INTERNALLY)
            # This prevents double-waiting which causes timeout (snapshotting items twice)
            download_success = self._process_batch_download(prompt, variations, output_path)
        else:
            # Just wait if no download requested
            count = variations if variations else 1
            download_success = self.wait_for_generation(prompt=prompt, timeout=timeout, expected_count=count)
            
        # Always navigate back to be ready for next task
        self._navigate_back_to_create()
        
        return download_success
    
    def process_row(self, row) -> dict:
        """
        Process a single row/task from spreadsheet.
        Compatible with main_window.py task processing.
        
        Args:
            row: SheetRow object with prompt, image_path, output_path, etc.
            
        Returns:
            dict with success status and details
        """
        start_time = time.time()
        
        try:
            self.log(f"📋 Processing: {row.stt} - {row.prompt[:50]}...")
            
            # Determine output file path logic for Batch/Single download
            variations = getattr(row, 'variations', 1) or 1
            if isinstance(variations, str):
                try: 
                    # Handle "1 (default)" format if coming from standardized processing
                    variations = int(str(variations).split()[0])
                except: variations = 1
                
            output_dir = self.download_dir
            filename_base = f"sora_{row.stt}_{int(time.time())}"
            
            if row.save_name:
                # User wants specific name/folder: "tom" -> folder "tom", files "tom_01", "tom_02"...
                clean_name = os.path.splitext(row.save_name)[0] # remove extension
                
                # Create subfolder with same name
                output_dir = os.path.join(self.download_dir, clean_name)
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.log(f"📂 Created output directory: {output_dir}")
                except Exception as e:
                    self.log(f"⚠️ Could not create directory: {e}")
                    output_dir = self.download_dir # Fallback
                
                filename_base = clean_name
            
            # Use base path without extension for flexibility
            # download_video will append _01.png, _02.mp4 etc.
            output_path = os.path.join(output_dir, filename_base)
            
            # Run the main workflow with video settings
            success = self.generate_video(
                prompt=row.prompt,
                image_paths=getattr(row, 'image_paths', []) or ([row.image_path] if hasattr(row, 'image_path') and row.image_path else []),
                output_path=output_path,
                type=row.type,
                aspect_ratio=row.aspect_ratio,
                resolution=row.resolution,
                duration=row.duration,
                variations=variations, # Use the sanitized local variable
                timeout=300
            )
            
            duration = time.time() - start_time
            
            return {
                "success": success,
                "prompt": row.prompt,
                "output_path": output_path if success else None,
                "duration_seconds": duration,
                "error": None if success else "Generation failed"
            }
            
        except Exception as e:
            self.log(f"❌ Process error: {e}")
            return {
                "success": False,
                "prompt": row.prompt if hasattr(row, 'prompt') else "",
                "output_path": None,
                "duration_seconds": time.time() - start_time,
                "error": str(e)
            }
