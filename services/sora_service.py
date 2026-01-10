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
        
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Navigate to Sora immediately
        self.log("🌐 Đang mở sora.chatgpt.com...")
        self.driver.get(self.BASE_URL)
        time.sleep(3)
        
        
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
        
        The old Sora interface is more reliable for automation.
        Look for "Switch to old Sora" in the menu and click it.
        """
        self.log("🔄 Kiểm tra và chuyển sang Old Sora...")
        
        try:
            # Check if already on old Sora (look for indicators)
            page_source = self.driver.page_source.lower()
            if 'open new sora' in page_source:
                self.log("✅ Đang ở Old Sora")
                return True
            
            # Look for "Switch to old Sora" link/button
            # Method 1: Find by text using XPath
            try:
                switch_elem = self.driver.find_element(By.XPATH, 
                    "//*[contains(text(), 'Switch to old Sora') or contains(text(), 'switch to old sora')]")
                if switch_elem.is_displayed():
                    switch_elem.click()
                    self.log("✅ Đã click 'Switch to old Sora'")
                    time.sleep(3)
                    return True
            except Exception:
                pass
            
            # Method 2: Look in sidebar/menu
            try:
                # First click on profile/menu to open sidebar
                menu_btns = self.driver.find_elements(By.CSS_SELECTOR, 
                    '[aria-label*="menu" i], [aria-label*="profile" i], button svg')
                for btn in menu_btns:
                    try:
                        if btn.is_displayed():
                            btn.click()
                            time.sleep(1)
                            break
                    except Exception:
                        continue
                
                # Now look for Switch to old Sora in the opened menu
                time.sleep(1)
                switch_elem = self.driver.find_element(By.XPATH, 
                    "//*[contains(text(), 'Switch to old Sora')]")
                if switch_elem.is_displayed():
                    switch_elem.click()
                    self.log("✅ Đã click 'Switch to old Sora' từ menu")
                    time.sleep(3)
                    return True
            except Exception:
                pass
            
            # Method 3: Try clicking any link/button containing "old"
            try:
                elements = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'old') and contains(text(), 'Sora')]")
                for elem in elements:
                    if elem.is_displayed():
                        elem.click()
                        self.log("✅ Đã switch to old Sora")
                        time.sleep(3)
                        return True
            except Exception:
                pass
            
            self.log("ℹ️ Không thấy switch option, có thể đã ở Old Sora")
            return True
            
        except Exception as e:
            self.log(f"⚠️ Lỗi switch Sora version: {e}")
            return True  # Continue anyway
    
    def navigate_to_create(self) -> bool:
        """Navigate to video creation page"""
        self.log("🎬 Đang mở trang tạo video...")
        
        try:
            # First, switch to old Sora if needed
            self.switch_to_old_sora()
            time.sleep(2)
            
            # Check if already on create page
            if self._find_prompt_input():
                self.log("✅ Đã ở trang tạo video")
                return True
            
            # Navigate to main page
            self.driver.get(self.BASE_URL)
            time.sleep(3)
            
            # Switch to old Sora again after navigation
            self.switch_to_old_sora()
            time.sleep(2)
            
            # Wait for prompt input to appear (max 15 seconds)
            for _ in range(15):
                if self._find_prompt_input():
                    self.log("✅ Đã vào trang tạo video")
                    return True
                time.sleep(1)
                
            self.log("⚠️ Không tìm thấy ô nhập prompt")
            return False
            
        except Exception as e:
            self.log(f"❌ Lỗi navigation: {e}")
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
        Click on a dropdown option in the bottom bar and select a value.
        
        IMPORTANT: Only clicks buttons in the bottom bar area to avoid
        accidentally clicking on video thumbnails.
        """
        try:
            # Get window height to calculate bottom bar area
            window_height = self.driver.execute_script("return window.innerHeight")
            bottom_threshold = window_height - 150  # Bottom 150px is the bar
            
            # Find all buttons and filter by position
            all_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button, [role="button"]')
            
            # Filter to only buttons in the bottom bar
            bottom_bar_buttons = []
            for btn in all_buttons:
                try:
                    if btn.is_displayed():
                        location = btn.location
                        if location.get('y', 0) > bottom_threshold:
                            bottom_bar_buttons.append(btn)
                except Exception:
                    continue
            
            self.log(f"  🔍 Tìm thấy {len(bottom_bar_buttons)} nút trong bottom bar")
            
            # Click the appropriate button based on option type
            for btn in bottom_bar_buttons:
                try:
                    btn_text = btn.text.lower().strip()
                    aria_label = btn.get_attribute('aria-label') or ""
                    aria_label = aria_label.lower()
                    role = btn.get_attribute("role")
                    
                    if option_type == "type":
                        # Require role="combobox"
                        if role != "combobox":
                            continue

                        # Look for Type buttons: Image or Video or aria-label="Media type"
                        # EXCLUDE "search" to avoid "search for similar images"
                        if ("type" in aria_label or "media" in aria_label) and "search" not in aria_label:
                             btn.click()
                             self.log(f"  🎨 Clicked type button (by aria): {aria_label}")
                             time.sleep(0.5)
                             break
                        # Text check
                        if btn_text == "image" or btn_text == "video":
                            btn.click()
                            self.log(f"  🎨 Clicked type button: {btn_text}")
                            time.sleep(0.5)
                            break
                        elif ("image" in btn_text or "video" in btn_text) and "search" not in btn_text and "similar" not in btn_text:
                            btn.click()
                            self.log(f"  🎨 Clicked type button: {btn_text}")
                            time.sleep(0.5)
                            break
                            
                    elif option_type == "aspect":
                        # aria-label="Aspect ratio"
                        if "aspect" in aria_label or "ratio" in aria_label:
                            btn.click()
                            self.log(f"  📐 Clicked aspect button (by aria): {aria_label}")
                            time.sleep(0.5)
                            break
                        # Text check
                        if any(ratio in btn_text for ratio in ['16:9', '9:16', '1:1', '3:2', '2:3']):
                            btn.click()
                            self.log(f"  📐 Clicked aspect button: {btn_text}")
                            time.sleep(0.5)
                            break
                            
                    elif option_type == "resolution":
                        # aria-label="Resolution" or "Quality"
                        if "resolution" in aria_label or "quality" in aria_label:
                            btn.click()
                            self.log(f"  📺 Clicked resolution button (by aria): {aria_label}")
                            time.sleep(0.5)
                            break
                        # Text check
                        if any(res in btn_text for res in ['1080', '720', '480', '360']):
                            btn.click()
                            self.log(f"  📺 Clicked resolution button: {btn_text}")
                            time.sleep(0.5)
                            break
                            
                    elif option_type == "duration":
                        # aria-label="Duration"
                        if "duration" in aria_label:
                            btn.click()
                            self.log(f"  ⏱️ Clicked duration button (by aria): {aria_label}")
                            time.sleep(0.5)
                            break
                        # Text check: ensure it has 's' AND a number, AND NO 'v' (to avoid confusion)
                        if 's' in btn_text and 'v' not in btn_text and any(d in btn_text for d in ['5', '10', '15', '20']):
                            btn.click()
                            self.log(f"  ⏱️ Clicked duration button: {btn_text}")
                            time.sleep(0.5)
                            break
                            
                    elif option_type == "variations":
                        # aria-label="Variations" or "Video count"
                        if "variation" in aria_label or "count" in aria_label:
                             btn.click()
                             self.log(f"  🎬 Clicked variations button (by aria): {aria_label}")
                             time.sleep(0.5)
                             break
                        # Text check: 1v, 2v, 1 video... ensure NO 's' (unless "videos") to avoid Duration
                        # Strict check for "v" format or "video" format
                        if ('video' in btn_text and any(c.isdigit() for c in btn_text)) or \
                           ('v' in btn_text and 's' not in btn_text and any(c.isdigit() for c in btn_text) and len(btn_text) < 5):
                            btn.click()
                            self.log(f"  🎬 Clicked variations button: {btn_text}")
                            time.sleep(0.5)
                            break
                            
                except Exception:
                    continue
                            
                except Exception:
                    continue
            
            # Now find and click the option in the dropdown menu
            time.sleep(0.5)
            
            # Look for dropdown options that match the value
            value_lower = value.lower()
            
            # Special handling for type option - normalize value
            type_value = None
            if option_type == "type":
                # Normalize value: "image" or "video"
                type_value = value_lower.strip()
                if type_value not in ["image", "video"]:
                    # Try to extract from value if it contains the word
                    if "image" in type_value:
                        type_value = "image"
                    elif "video" in type_value:
                        type_value = "video"
                    else:
                        self.log(f"  ⚠️ Invalid type value: {value}")
                        return False
            
            # Try role-based selectors first (more specific)
            dropdown_items = self.driver.find_elements(By.CSS_SELECTOR, 
                '[role="option"], [role="menuitem"], [role="menuitemradio"]')
            
            for item in dropdown_items:
                try:
                    item_text = item.text.lower().strip()
                    if option_type == "type":
                        # For type, match exactly "image" or "video"
                        if item_text == type_value or (type_value == "image" and "image" in item_text) or (type_value == "video" and "video" in item_text):
                            if item.is_displayed():
                                item.click()
                                self.log(f"  ✓ Set {option_type}: {value}")
                                time.sleep(0.3)
                                return True
                    else:
                        # For other options, use existing logic
                        if value_lower in item_text or item_text in value_lower:
                            if item.is_displayed():
                                item.click()
                                self.log(f"  ✓ Set {option_type}: {value}")
                                time.sleep(0.3)
                                return True
                except Exception:
                    continue
            
            # Fallback: look for any clickable element with matching text
            try:
                # Construct XPath to find text case-insensitive
                if option_type == "type" and type_value:
                    # Specific handling for type to ensure we don't click wrong things
                    # Using translate for case-insensitive matching
                    xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{type_value}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                elif option_type == "variations":
                    # For variations, we might be looking for "2 videos" or "4 videos"
                    # Also handle just the number if passed
                    search_term = value_lower
                    if search_term.isdigit():
                        search_term = f"{search_term} video" # append ' video' if just a digit
                    
                    xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{search_term}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                else:
                    xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{value_lower}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                
                for elem in elements:
                    if elem.is_displayed():
                        # Check it's in the dropdown area (popup)
                        location = elem.location
                        # Simple check: if y < bottom_threshold, it might be the dropdown menu which usually spawns ABOVE the bar
                        # But some dropdowns might spawn differently. 
                        # We just check if it's clickable and visible.
                        
                        elem_text = elem.text.lower().strip()
                        
                        if option_type == "type" and type_value:
                             # Verify it's actually Image or Video option
                            if (type_value == "image" and ("image" in elem_text and "video" not in elem_text)) or \
                               (type_value == "video" and ("video" in elem_text and "image" not in elem_text)):
                                elem.click()
                                self.log(f"  ✓ Set {option_type} (fallback): {value}")
                                return True
                        elif option_type == "variations":
                             if value_lower in elem_text:
                                elem.click()
                                self.log(f"  ✓ Set {option_type} (fallback): {value}")
                                return True
                        else:
                            elem.click()
                            self.log(f"  ✓ Set {option_type} (fallback): {value}")
                            return True
            except Exception as e:
                self.log(f"  ⚠️ Fallback selection failed: {e}")
                pass
            
            return False
            
        except Exception as e:
            self.log(f"⚠️ Không thể set {option_type}: {e}")
            return False
    
    def wait_for_generation(self, timeout: int = 300) -> bool:
        """
        Wait for video generation to complete on Library page.
        
        Strategy:
        1. Navigate to /library 
        2. Look for video items that are LOADING (have spinner/progress indicator)
        3. Wait until loading finishes (spinner disappears)
        4. Click on the completed video to open it
        5. Store the video URL for download
        """
        self.log(f"⏳ Đang chờ tạo video... (timeout: {timeout}s)")
        start_time = time.time()
        
        # Wait for submission to process
        time.sleep(5)
        
        # Navigate to library page
        self.log("📂 Chuyển sang trang Library để theo dõi tiến trình...")
        self.driver.get(f"{self.BASE_URL}/library")
        time.sleep(3)
        
        # Count initial video items
        initial_count = self._count_video_items()
        self.log(f"📊 Số video hiện có: {initial_count}")
        
        last_count = initial_count
        refresh_interval = 5 # Refresh every 5 seconds 
        last_refresh_time = time.time() - refresh_interval 
        
        while time.time() - start_time < timeout:
            try:
                elapsed = int(time.time() - start_time)
                current_time = time.time()
                
                # Refresh page every 5 seconds to check progress
                if current_time - last_refresh_time >= refresh_interval:
                    self.log(f"⏳ Đã chờ {elapsed}s... Refreshing...")
                    self.driver.refresh()
                    time.sleep(2)  # Wait for page to load
                    last_refresh_time = time.time()  # Update after refresh completes
                
                # Check notification bell for completion indicator
                if self._check_notification_bell():
                    self.log("🔔 Notification bell có badge - video đã xong!")
                    time.sleep(1)
                    self.driver.refresh()
                    time.sleep(2)
                    self._click_first_video()
                    return True
                
                # Count current video items
                current_count = self._count_video_items()
                
                if current_count > initial_count:
                    # New video appeared!
                    self.log(f"✅ Video mới xuất hiện! ({initial_count} → {current_count})")
                    time.sleep(1)
                    
                    # Click on first video to open it
                    self._click_first_video()
                    return True
                
                # Log progress periodically (every 30 seconds)
                if elapsed > 0 and elapsed % 30 == 0:
                    self.log(f"⏳ Đang chờ video... ({current_count} video trong library)")
                
            except Exception as e:
                self.log(f"⚠️ Check error: {e}")
            
            time.sleep(2)  # Check every 2 seconds
        
        self.log("⏰ Timeout - video chưa hoàn thành")
        return False
    
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
        
        # Step 2: Configure video settings FIRST (before any input)
        # Type must be configured first, then other settings
        if any([type, aspect_ratio, resolution, duration, variations]):
            self.configure_video_settings(
                type=type,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                duration=duration,
                variations=variations
            )
            time.sleep(1)
        
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
        
        # Step 6: Wait for generation
        if not self.wait_for_generation(timeout):
            return False
        
        # Step 7: Download (if output path provided)
        if output_path:
            return self.download_video(output_path)
        
        return True
    
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
            
            # Determine output file path - đơn giản hóa: dùng trực tiếp row.output_path nếu có
            # (đã được xử lý đầy đủ trong sheets_service.py)
            output_path = ""
            if row.output_path:
                # output_path đã được xử lý đầy đủ trong sheets_service.py, dùng trực tiếp
                output_path = row.output_path
            elif row.save_name:
                # Fallback: nếu không có output_path, tạo từ download_dir và save_name
                save_name_with_ext = row.save_name if row.save_name.lower().endswith('.mp4') else f"{row.save_name}.mp4"
                output_path = str(Path(self.download_dir) / save_name_with_ext)
            else:
                # Fallback: tạo tên file tự động
                output_path = str(Path(self.download_dir) / f"sora_{row.stt}_{int(time.time())}.mp4")
            
            # Run the main workflow with video settings
            success = self.generate_video(
                prompt=row.prompt,
                image_paths=getattr(row, 'image_paths', []) or ([row.image_path] if hasattr(row, 'image_path') and row.image_path else []),
                output_path=output_path,
                type=getattr(row, 'type', None),
                aspect_ratio=getattr(row, 'aspect_ratio', None),
                resolution=getattr(row, 'resolution', None),
                duration=getattr(row, 'duration', None),
                variations=getattr(row, 'variations', None),
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
