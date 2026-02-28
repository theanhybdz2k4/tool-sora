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
                 log_callback: Optional[Callable] = None, check_interval: int = 10):
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
        self.check_interval = check_interval
        self.wait = WebDriverWait(self.driver, 30)
        
        # Cache flags to avoid redundant operations
        self._switched_to_old_sora = False  # Only switch once per session
        self._last_settings = {}  # Cache last configured settings
        
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Navigate to Sora - LUÔN navigate để tránh stale URL từ Chrome profile cache
        # driver.current_url có thể trả về URL cũ từ session trước dù browser đang ở New Tab
        self.log("🌐 Đang mở sora.chatgpt.com...")
        for nav_retry in range(3):
            try:
                self.driver.get(self.BASE_URL)
                time.sleep(5)
                # Verify bằng page title/content, KHÔNG tin current_url
                page_title = self.driver.title.lower()
                page_source_snippet = self.driver.page_source[:2000].lower() if self.driver.page_source else ""
                real_url = self.driver.current_url.lower()
                
                if 'sora' in page_title or 'sora' in page_source_snippet or 'sora.chatgpt.com' in real_url:
                    self.log(f"✅ Đã navigate đến Sora thành công (URL: {real_url})")
                    break
                elif 'auth.openai.com' in real_url or 'login' in real_url:
                    self.log(f"✅ Đang ở trang đăng nhập OpenAI")
                    break
                else:
                    self.log(f"⚠️ Navigate lần {nav_retry+1} - trang chưa load đúng (title='{self.driver.title}', url='{real_url}')")
                    time.sleep(3 * (nav_retry + 1))
            except Exception as nav_e:
                self.log(f"⚠️ Lỗi navigate lần {nav_retry+1}: {nav_e}")
                time.sleep(3 * (nav_retry + 1))
        
        # PROACTIVE: Switch to old Sora immediately after login/opening
        self.log("🔍 Đang thực hiện kiểm tra giao diện Old Sora...")
        try:
            if self.switch_to_old_sora():
                self._switched_to_old_sora = True
            else:
                self.log("⚠️ Không thể xác định hoặc chuyển đổi giao diện trong lúc khởi tạo.")
        except Exception as e:
            self.log(f"⚠️ Lỗi switch Old Sora trong init: {e}")
        time.sleep(1)
        
        
    # ==================== LOGIN CHECK ====================
    
    def is_logged_in(self) -> bool:
        """
        Check if user is logged into Sora with high accuracy.
        Uses multiple indicators: current URL, library links, prompt input, and profile buttons.
        """
        # Thử kiểm tra tối đa 3 lần với khoảng nghỉ ngắn để đợi page load
        for attempt in range(3):
            try:
                current_url = self.driver.current_url.lower()
                
                # Indicator 1: Nếu còn ở trang auth.openai.com hoặc login.openai.com thì chắc chắn chưa đăng nhập
                if 'auth.openai.com' in current_url or 'login.openai.com' in current_url:
                    return False
                
                # Indicator 2: Kiểm tra existence của Library link hoặc Dashboard links
                # Đây là các link chỉ có sau khi login
                logged_in_links = [
                    'a[href="/library"]',
                    'a[href="/explore"]',
                    '[aria-label="Settings"]',
                    'button img[src*="avatar"]' # User profile avatar
                ]
                
                for selector in logged_in_links:
                    if self.driver.find_elements(By.CSS_SELECTOR, selector):
                        return True
                
                # Indicator 3: Kiểm tra Prompt Input (cả New và Old Sora)
                prompt_input = self._find_prompt_input()
                if prompt_input:
                    return True
                
                # Indicator 4: Page source check (fallback)
                page_source = self.driver.page_source.lower()
                if 'describe your video' in page_source or 'storyboard' in page_source or 'sign out' in page_source:
                    return True
                
                # Nếu chưa thấy gì, đợi 2s rồi check lại (phòng hờ mạng chậm)
                if attempt < 2:
                    time.sleep(2)
                    
            except Exception as e:
                # Nếu lỗi session id ở đây, thử recover nhẹ
                if "invalid session id" in str(e).lower():
                    self.log("⚠️ Mất session khi check login, đang bỏ qua...")
                continue
                
        return False
            
    def wait_for_manual_login(self, timeout: int = 300) -> bool:
        """Wait for user to manually log in with robust check"""
        self.log("⏳ Đang chờ đăng nhập thủ công...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self.is_logged_in():
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
        """
        self.log("🔄 Kiểm tra và chuyển sang Old Sora...")
        
        # Try up to 3 times to switch
        for attempt in range(3):
            try:
                # Check for Old Sora indicators
                page_source = self.driver.page_source.lower()
                if 'describe your image' in page_source or 'open new sora' in page_source:
                    self.log("✅ Đang ở giao diện Old Sora")
                    return True
                
                # Check for New Sora Indicators and Switch
                # Method 1: Settings button by aria-label
                try:
                    settings_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Settings"]')
                    if settings_btn.is_displayed():
                        settings_btn.click()
                        time.sleep(1.5)
                        
                        switch_item = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Switch to old Sora')]")
                        switch_item.click()
                        self.log("✅ Đã click 'Switch to old Sora' từ Settings")
                        time.sleep(3)
                        continue # Re-check in next iteration
                except: pass
                
                # Method 2: JS injection for direct menu item click
                try:
                    js_switch = """
                    (function() {
                        var items = document.querySelectorAll('[role="menuitem"], button, span');
                        for (var i = 0; i < items.length; i++) {
                            if (items[i].textContent.includes('Switch to old Sora')) {
                                items[i].click(); return true;
                            }
                        }
                        return false;
                    })();
                    """
                    if self.driver.execute_script(js_switch):
                        self.log("✅ Đã click 'Switch to old Sora' via JS")
                        time.sleep(3)
                        continue
                except: pass
                
                # Method 3: Force URL if possible (OpenAI sometimes supports this)
                # self.driver.get("https://sora.chatgpt.com/?v=old") # Hypothetical
                
            except Exception as e:
                self.log(f"⚠️ Lần thử {attempt+1} lỗi: {e}")
            
            time.sleep(2)
            
        self.log("⚠️ Không tìm thấy hoặc không chuyển được sang Old Sora")
        return False
    
    def navigate_to_create(self) -> bool:
        """Navigate to video creation page - ENHANCED"""
        self.log("🌐 Đang điều hướng đến trang tạo...")
        
        for attempt in range(3):
            try:
                # 1. Verify thực sự đang ở Sora bằng page title/content (không tin URL)
                page_title = self.driver.title.lower()
                real_url = self.driver.current_url.lower()
                
                actually_on_sora = ('sora' in page_title or 
                                   'sora.chatgpt.com' in real_url and 
                                   'chrome://' not in real_url and
                                   'google.com' not in real_url)
                
                if not actually_on_sora:
                    self.log(f"  ⚠️ Không ở Sora thực sự (title='{self.driver.title}', url='{real_url}'), navigate lại...")
                    self.driver.get(self.BASE_URL)
                    time.sleep(5)
                    # Verify lại
                    page_title = self.driver.title.lower()
                    real_url = self.driver.current_url.lower()
                    if 'sora' not in page_title and 'sora.chatgpt.com' not in real_url:
                        self.log(f"  ❌ Vẫn không vào được Sora (title='{self.driver.title}')")
                        time.sleep(3)
                        continue
                
                # 2. Subpage handling - re-read URL trước khi check
                real_url = self.driver.current_url.lower()
                sora_subpages = ['/explore', '/library', '/video/', '/image/', '/settings']
                if any(sub in real_url for sub in sora_subpages):
                    self.log(f"  🔄 Đang ở subpage ({real_url}), chuyển về trang tạo...")
                    self.driver.get(self.BASE_URL)
                    time.sleep(3)
                
                # 3. Handle interface version
                if not self._switched_to_old_sora:
                    if self.switch_to_old_sora():
                        self._switched_to_old_sora = True
                    time.sleep(2)
                
                # 4. Final verification: Does prompt input exist?
                if self._find_prompt_input():
                    self.log("✅ Đã ở trang tạo video")
                    return True
                
                # 5. Không tìm thấy prompt input -> thử navigate lại hoàn toàn
                self.log(f"  ❌ Không thấy prompt input, navigate về trang chính...")
                self.driver.get(self.BASE_URL)
                time.sleep(5)
                
                # 6. Handle Cloudflare if blocked
                if self._is_cloudflare_challenge():
                    self.log("⚠️ Phát hiện Cloudflare challenge!")
                    if self._wait_for_cloudflare():
                        continue
                
                # Re-check prompt input after full navigate
                if self._find_prompt_input():
                    self.log("✅ Đã ở trang tạo video")
                    return True
                    
                self.log(f"  ⏳ Chờ trang load (Lần {attempt+1}/3)...")
                time.sleep(3)
                
            except Exception as e:
                self.log(f"❌ Lỗi navigation lần {attempt+1}: {e}")
                try:
                    self.driver.get(self.BASE_URL)
                    time.sleep(5)
                except: pass
                
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
        if not image_path:
            self.log("⚠️ Không có ảnh để upload (đường dẫn trống)")
            return False
            
        if not os.path.exists(image_path):
            self.log(f"⚠️ Không tìm thấy file ảnh: {image_path}")
            # Try to check if it's just the filename and look in Image directory
            filename = os.path.basename(image_path)
            alt_path = Path("Image") / filename
            if alt_path.exists():
                image_path = str(alt_path.absolute())
                self.log(f"🔍 Đã tìm thấy ảnh thay thế tại: {image_path}")
            else:
                self.log(f"❌ File ảnh thực sự không tồn tại: {filename}")
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
        for _ in range(5):
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
            except: pass
            time.sleep(1)
        return False
    
    def _handle_media_upload_agreement(self) -> bool:
        """
        Handle the "Media upload agreement" modal.
        """
        self.log("⏳ Checking for Media upload agreement modal...")
        
        # Wait up to 10 seconds for modal
        modal_found = False
        for _ in range(5):
            page_source = self.driver.page_source.lower()
            if 'media upload agreement' in page_source:
                modal_found = True
                break
            time.sleep(2)
        
        if not modal_found:
            self.log("ℹ️ Không thấy modal agreement (có thể đã đồng ý trước đó)")
            return False

        self.log("📋 Tìm thấy modal Media upload agreement")
        
        try:
            # Step 1: Find and click ALL checkboxes
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"], [role="checkbox"]')
            for cb in checkboxes:
                try:
                    if cb.is_displayed():
                        self.driver.execute_script("arguments[0].click();", cb)
                        time.sleep(0.3)
                except: pass
            
            # Step 2: Click Accept button
            accept_selectors = [
                "//button[normalize-space(text())='Accept']",
                "//button[normalize-space(text())='Agree']",
                "button.bg-primary" # Common style for primary action
            ]
            
            for selector in accept_selectors:
                try:
                    if selector.startswith("//"): btn = self.driver.find_element(By.XPATH, selector)
                    else: btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if btn.is_displayed():
                        btn.click()
                        self.log("✅ Đã click Accept")
                        time.sleep(2)
                        return True
                except: continue

            # JS Fallback
            self.driver.execute_script("""
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    var t = btns[i].textContent.toLowerCase();
                    if (t.includes('accept') || t.includes('agree')) {
                        btns[i].click(); return true;
                    }
                }
            """)
            
            time.sleep(3)
            return 'media upload agreement' not in self.driver.page_source.lower()
            
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
        
        try:
            # Wait for generate button to become enabled (Sora needs time after prompt input)
            generate_btn = None
            for wait_attempt in range(10):  # Wait up to ~10s
                time.sleep(1)
                
                # Find all buttons in bottom bar
                window_height = self.driver.execute_script("return window.innerHeight")
                bottom_threshold = window_height - 150
                
                # Method 1: type=submit
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                    if submit_btn.is_displayed():
                        is_disabled = (submit_btn.get_attribute("disabled") is not None or 
                                      submit_btn.get_attribute("data-disabled") == "true" or
                                      not submit_btn.is_enabled())
                        if not is_disabled:
                            generate_btn = submit_btn
                            break
                        elif wait_attempt >= 5:
                            # After 5s, force click even if disabled
                            generate_btn = submit_btn
                            break
                except Exception:
                    pass
                
                # Method 2: Arrow button with SVG in bottom bar
                try:
                    buttons_with_svg = self.driver.find_elements(By.XPATH, "//button[.//svg]")
                    for btn in buttons_with_svg:
                        try:
                            if not btn.is_displayed(): continue
                            location = btn.location
                            if location.get('y', 0) < bottom_threshold: continue
                            
                            # Look for the send/submit button (usually has arrow up SVG)
                            btn_html = btn.get_attribute("outerHTML") or ""
                            if 'sr-only' in btn_html and ('create' in btn_html.lower() or 'video' in btn_html.lower() or 'image' in btn_html.lower()):
                                is_disabled = (btn.get_attribute("disabled") is not None or 
                                              btn.get_attribute("data-disabled") == "true")
                                if not is_disabled or wait_attempt >= 5:
                                    generate_btn = btn
                                    break
                        except: continue
                except Exception:
                    pass
                
                if generate_btn:
                    break
                    
                if wait_attempt < 9:
                    self.log(f"  ⏳ Đợi nút Generate sẵn sàng... ({wait_attempt+1}/10)")
            
            # Try clicking the found button
            if generate_btn:
                try:
                    generate_btn.click()
                    self.log("✅ Đã click Generate")
                    time.sleep(2)
                    return True
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", generate_btn)
                        self.log("✅ Đã click Generate (JS)")
                        time.sleep(2)
                        return True
                    except Exception:
                        pass
            
            # Fallback: Press Enter key on prompt input
            try:
                input_elem = self._find_prompt_input()
                if input_elem:
                    input_elem.send_keys(Keys.ENTER)
                    self.log("✅ Đã nhấn Enter để submit")
                    time.sleep(2)
                    return True
            except Exception:
                pass
            
            # Last resort: JS click on any generate-looking button
            js_result = self.driver.execute_script("""
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var btn = buttons[i];
                    var text = (btn.textContent || '').toLowerCase();
                    var sr = btn.querySelector('.sr-only');
                    var srText = sr ? sr.textContent.toLowerCase() : '';
                    if (srText.includes('create') || srText.includes('generate') || srText.includes('video') || srText.includes('image')) {
                        btn.removeAttribute('disabled');
                        btn.setAttribute('data-disabled', 'false');
                        btn.click();
                        return true;
                    }
                }
                return false;
            """)
            if js_result:
                self.log("✅ Đã click Generate (JS force)")
                time.sleep(2)
                return True
                
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
            resolution: "1080p", "720p", "480p", "360p"
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
                # Store Variations setting
                self._last_settings['variations'] = variations
                
                # Broad text for search: just use the number and media type keyword
                # e.g. "1 image" or "4 videos"
                # We'll use a flexible search in _set_dropdown_option
                media_keyword = "image" if type and "image" in type.lower() else "video"
                var_text = f"{variations}" # We'll search for the number first
                
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
        Improved with scroll-into-view and JS fallback for intercepted clicks.
        """
        self.log(f"⚙️ Setting {option_type} to '{value}'...")
        
        for main_attempt in range(3):
            try:
                # Step 1: Find and click the button
                window_height = self.driver.execute_script("return window.innerHeight")
                bottom_threshold = window_height - 200 # Slightly wider for safety
                
                buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button, [role="button"], [role="combobox"]')
                target_btn = None
                
                for btn in buttons:
                    try:
                        if not btn.is_displayed(): continue
                        # Filter buttons in the bottom composer area
                        if btn.location.get('y', 0) < bottom_threshold: continue
                        
                        text = btn.text.lower()
                        aria = (btn.get_attribute('aria-label') or "").lower()
                        
                        # Match by text or aria-label
                        if option_type == "type":
                            if text in ["image", "video"] or "type" in aria:
                                target_btn = btn
                        elif option_type == "aspect":
                            if any(r in text for r in ['16:9', '9:16', '1:1', '3:2', '2:3']) or "aspect" in aria:
                                target_btn = btn
                        elif option_type == "duration":
                            if (('s' in text and any(d in text for d in ['5', '10', '15', '20'])) or "duration" in aria):
                                target_btn = btn
                        elif option_type == "resolution":
                            if (any(r in text for r in ['360', '480', '720', '1080']) or "resolution" in aria):
                                target_btn = btn
                        elif option_type == "variations":
                            # Button for variations MUST have 'v' or 'variation' OR a number,
                            # but it MUST NOT be just 'image' or 'video' (which is the type button)
                            is_media_type = text in ['image', 'video']
                            has_v = 'v' in text.replace(' ', '') or "variation" in aria
                            has_number = any(str(v) in text for v in [1, 2, 4])
                            
                            if (has_v or (has_number and not is_media_type)) and text != "image" and text != "video":
                                target_btn = btn
                        
                        if target_btn: break
                    except: continue

                if not target_btn:
                    self.log(f"  ⚠️ Lần thử {main_attempt+1}: Không tìm thấy nút {option_type}")
                    time.sleep(2)
                    continue

                # Ensure button is in view and try to click
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                    time.sleep(0.5)
                    target_btn.click()
                except Exception as e:
                    if "click intercepted" in str(e).lower():
                        self.log(f"  ⚠️ Click bị chặn, thử click bằng JS...")
                        self.driver.execute_script("arguments[0].click();", target_btn)
                    else:
                        raise e

                time.sleep(1.5)

                # Step 2: Find and click the option
                search_val = value.lower().strip()
                # Simple normalization for duration
                if option_type == "duration" and search_val.isdigit(): search_val = f"{search_val} seconds"
                
                # Broad selector for dropdown options
                options = self.driver.find_elements(By.CSS_SELECTOR, '[role="option"], [role="menuitem"], .radix-dropdown-menu-item, button, div[role="menuitem"]')
                option_clicked = False
                
                # First pass: strict match
                for opt in options:
                    try:
                        if not opt.is_displayed(): continue
                        opt_text = opt.text.lower().replace('✓', '').strip()
                        
                        # Check if this is the target option
                        is_match = False
                        if option_type == "variations":
                            # Match "1" with "1 image", "1 variation", "1v" etc.
                            valid_terms = [search_val, f"{search_val} ", f"{search_val}v", f"{search_val} image", f"{search_val} video", f"{search_val} variation"]
                            if any(term == opt_text or opt_text == term + 's' for term in valid_terms):
                                is_match = True
                        else:
                            if search_val == opt_text or opt_text == search_val:
                                is_match = True

                        if is_match:
                            # Check if already selected
                            if "✓" in opt.text or "selected" in opt.text.lower() or opt.get_attribute("aria-selected") == "true":
                                self.log(f"  ✅ {option_type} '{value}' đã được chọn")
                                try:
                                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                                except: pass
                                return True
                            
                            # Try clicking the option
                            try:
                                opt.click()
                            except:
                                self.driver.execute_script("arguments[0].click();", opt)
                                
                            self.log(f"  ✅ Đã chọn {option_type}: {value}")
                            option_clicked = True
                            break
                    except: continue

                if option_clicked: return True
                
                # Second pass: broader check if strict failed
                for opt in options:
                    try:
                        if not opt.is_displayed(): continue
                        if search_val in opt.text.lower():
                             self.driver.execute_script("arguments[0].click();", opt)
                             self.log(f"  ✅ Đã chọn {option_type}: {value} (fallback)")
                             return True
                    except: continue

                if option_clicked: return True
                
                # JS Fallback for finding and clicking option
                js_click = f"""
                (function() {{
                    var search = '{search_val}';
                    var type = '{option_type}';
                    var items = document.querySelectorAll('[role="option"], [role="menuitem"], button, div, span');
                    for (var i = 0; i < items.length; i++) {{
                        var txt = items[i].textContent.toLowerCase().replace('✓', '').trim();
                        if (items[i].offsetParent !== null) {{
                            var isMatch = false;
                            if (type === 'variations') {{
                                if (txt === search || txt === search + ' image' || txt === search + ' images' || 
                                    txt === search + ' video' || txt === search + ' videos' || 
                                    txt === search + 'v' || txt === search + ' variation' || txt === search + ' variations') isMatch = true;
                            }} else {{
                                if (txt === search || txt.includes(search)) isMatch = true;
                            }}
                            
                            if (isMatch) {{
                                items[i].click(); return true;
                            }}
                        }}
                    }}
                    return false;
                }})();
                """
                if self.driver.execute_script(js_click):
                    self.log(f"  ✅ Đã chọn {option_type}: {value} (via JS)")
                    return True

                # Escape if menu still open
                try:
                    self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                except: pass
                
                self.log(f"  ⚠️ Lần thử {main_attempt+1}: Không click được option {search_val}")
                time.sleep(2)
                
            except Exception as e:
                self.log(f"  ❌ Lỗi dropdown lần {main_attempt+1}: {e}")
                time.sleep(2)
        
        return False
    
    def wait_for_generation(self, prompt: str = None, timeout: int = 400, expected_count: int = 1, initial_ids: set = None, task: Optional[any] = None) -> Optional[List[str]]:
        """
        Wait for generation to complete and return list of HREFs for NEW items.
        """
        self.log(f"⏳ Đang chờ tạo kết quả... (timeout: {timeout}s, expected: {expected_count} items)")
        start_time = time.time()
        
        # Snapshot current item IDs if not provided
        if initial_ids is None:
            initial_ids = set()
            try:
                if "/library" not in self.driver.current_url:
                    self.driver.get(f"{self.BASE_URL}/library")
                    time.sleep(3)
                link_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/g/gen_"], a[href*="/t/task_"]')
                initial_ids = {el.get_attribute('href') for el in link_elements if el.get_attribute('href')}
            except: pass
        
        # Ensure we are in library for monitoring
        if "/library" not in self.driver.current_url:
            self.log("📂 Chuyển sang trang Library để theo dõi...")
            self.driver.get(f"{self.BASE_URL}/library")
            time.sleep(3)
        
        last_status_msg = ""
        last_status_time = 0
        log_debounce_sec = 10
        refresh_interval = 25
        last_refresh_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Find matching items (robust matcher)
                matches = self._find_matching_items(prompt, task=task)
                
                # Filter for NEW items
                new_matches = []
                for m in matches:
                    try:
                        href = m.get_attribute("href") or m.find_element(By.TAG_NAME, "a").get_attribute("href")
                        if href and href not in initial_ids:
                            new_matches.append(m)
                    except: pass
                
                if new_matches:
                    # Check loading state
                    is_ready = True
                    loading_reason = ""
                    
                    for item in new_matches:
                        try:
                            # 1. Check for failed/error status
                            href = item.get_attribute("href") or ""
                            txt = (item.text + " " + item.get_attribute("innerText")).lower()
                            if "/t/task_" in href or "error" in txt:
                                self.log(f"⚠️ Phát hiện item bị LỖI (ID: {href[-10:] if href else 'N/A'})")
                                # Return IDs even if failed, so caller can decide
                                return [href] if href else None

                            # 2. Check for loading indicators
                            loading_markers = ["generating", "queue", "processing", "loading", "%"]
                            found_marker = next((m for m in loading_markers if m in txt), None)
                            if found_marker:
                                is_ready = False
                                loading_reason = f"đang {found_marker}"
                                break
                            
                            spinners = item.find_elements(By.CSS_SELECTOR, ".animate-spin, .loading, [class*='spinner']")
                            if spinners:
                                is_ready = False
                                loading_reason = "đang xử lý (spinner)"
                                break
                        except:
                            is_ready = False
                            break
                    
                    if is_ready:
                        if len(new_matches) >= expected_count:
                            self.log(f"✅ Đã có {len(new_matches)} kết quả mới sẵn sàng!")
                            first = new_matches[0]
                            meta = []
                            if getattr(first, '_sora_res', None): meta.append(first._sora_res)
                            if getattr(first, '_sora_dur', None): meta.append(f"{first._sora_dur}s")
                            meta_str = f" [{', '.join(meta)}]" if meta else ""
                            time_str = f" lúc {first._sora_time}" if getattr(first, '_sora_time', None) else ""
                            self.log(f"  📌 Khớp: '{getattr(first, '_sora_prompt', '---')[:40]}...'{meta_str}{time_str}")
                            
                            res_hrefs = []
                            for m in new_matches:
                                try:
                                    h = m.get_attribute("href") or m.find_element(By.TAG_NAME, "a").get_attribute("href")
                                    if h: res_hrefs.append(h)
                                except: pass
                            return res_hrefs if res_hrefs else None
                        else:
                            status_msg = f"⏳ Tìm thấy {len(new_matches)}/{expected_count} items mới. Chờ thêm..."
                    else:
                        status_msg = f"⏳ Item mới đã xuất hiện nhưng {loading_reason}..."
                    
                    if status_msg != last_status_msg or (time.time() - last_status_time > log_debounce_sec):
                        self.log(status_msg)
                        last_status_msg = status_msg
                        last_status_time = time.time()
                else:
                    elapsed = int(time.time() - start_time)
                    if elapsed > 0 and elapsed % 20 == 0:
                        self.log(f"⏳ Đang soát Library... ({elapsed}s)")
                
                # Periodic refresh
                if time.time() - last_refresh_time >= refresh_interval:
                    self.log(f"🔄 Refreshing Library... ({int(time.time() - start_time)}s)")
                    self.driver.refresh()
                    time.sleep(3)
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    last_refresh_time = time.time()
                else:
                    time.sleep(self.check_interval)
                    
            except Exception as e:
                err_str = str(e).lower()
                if "invalid session id" in err_str or "connection refused" in err_str:
                    self.log("❌ Mất kết nối với trình duyệt.")
                    return None
                self.log(f"⚠️ Warning in wait_loop: {e}")
                time.sleep(5)
                
        self.log("⏰ Hết thời gian chờ kết quả!")
        return None

    def _find_matching_items(self, prompt: str, task: Optional[any] = None) -> list:
        """Robust item matching using specific structure of library footer"""
        try:
            # 1. Normalize requirements
            q_prompt = prompt[:40].lower().strip()
            q_type = str(task.type).lower().strip() if task and hasattr(task, 'type') else "video"
            q_res = str(task.resolution).lower().strip() if task and hasattr(task, 'resolution') else ""
            q_dur = str(task.duration).lower().replace('s', '').strip() if task and hasattr(task, 'duration') else ""
            
            is_image = q_type == "image"
            
            log_meta = []
            if not is_image:
                if q_res: log_meta.append(q_res)
                if q_dur: log_meta.append(f"{q_dur}s")
            
            meta_str = f" [{', '.join(log_meta)}]" if log_meta else " [image]"
            self.log(f"🔍 Tìm item: '{q_prompt}...'{meta_str}")
            
            # 2. Get all containers with data-index
            containers = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-index]')
            found = []
            
            for container in containers[:15]: # Only check top 15 results
                try:
                    if not container.is_displayed(): continue
                    
                    # Cấu trúc Sora: footer chi tiết nằm trong flex-col gap-1 hoặc group v.v.
                    # Ta sẽ lấy toàn bộ text của container và parse
                    full_text = container.text.lower()
                    
                    # 3. Check Prompt (MANDATORY)
                    if q_prompt not in full_text:
                        continue
                        
                    # 4. Extract and check Metadata from the footer labels
                    # In the provided HTML, resolution, duration and time are in separate <div> siblings
                    item_res = ""
                    item_dur = ""
                    item_time = ""
                    
                    # Look for children of the metadata footer div
                    # Structure usually involves many small divs
                    child_divs = container.find_elements(By.CSS_SELECTOR, "div.flex-col.gap-1 > div")
                    if not child_divs: # Fallback: any div inside
                        child_divs = container.find_elements(By.CSS_SELECTOR, "div div")
                        
                    for div in child_divs:
                        text = div.text.lower().strip()
                        if not text: continue
                        
                        # Identify by patterns
                        if 'p' in text and any(r in text for r in ['360', '480', '720', '1080']):
                            item_res = text
                        elif 's' in text and len(text) <= 5 and any(d in text for d in ['5', '10', '15', '20']):
                            item_dur = text.replace('s', '').strip()
                        elif ':' in text and ('pm' in text or 'am' in text or len(text) <= 8):
                            item_time = text
                    
                    # 5. Verify metadata if task provided (SKIP for images)
                    if task and not is_image:
                        # Resolution check
                        if q_res and item_res and q_res not in item_res:
                            self.log(f"  ⏭️ Bỏ qua item: lệch Res ({item_res} vs {q_res})")
                            continue
                        # Duration check
                        if q_dur and item_dur and q_dur != item_dur:
                            self.log(f"  ⏭️ Bỏ qua item: lệch Duration ({item_dur}s vs {q_dur}s)")
                            continue
                            
                    # 6. Find links
                    links = container.find_elements(By.CSS_SELECTOR, 'a[href*="/g/gen_"], a[href*="/t/task_"]')
                    for link in links:
                        try:
                            # Attach metadata to the link object for logging
                            link._sora_prompt = full_text.split('\n')[0] # Usually first line is name/prompt
                            link._sora_res = item_res
                            link._sora_dur = item_dur
                            link._sora_time = item_time
                            found.append(link)
                        except: pass
                        
                except Exception as e_row:
                    continue
                    
            return found
            
        except Exception as e:
            self.log(f"⚠️ Error finding items: {e}")
            return []

    def _process_batch_download(self, prompt: str, variations: int, output_base_path: str, initial_ids: set = None, task: Optional[any] = None) -> bool:
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
        # wait_for_generation now returns the list of NEW item HREFs
        new_item_hrefs = self.wait_for_generation(prompt=prompt, expected_count=limit, initial_ids=initial_ids, task=task)
        
        if not new_item_hrefs:
            self.log("❌ Không tìm thấy kết quả mới sau khi chờ")
            # Try to recover by navigating back
            self._navigate_back_to_create()
            time.sleep(3) # Wait for library to reload
            return False
            
        self.log(f"🔍 Đã xác định được {len(new_item_hrefs)} items để tải")
        
        for i in range(min(limit, len(new_item_hrefs))):
            target_href = new_item_hrefs[i]
            
            try:
                # 1. Find item by HREF - This is MUCH more reliable than prompt matching in a loop
                try:
                    target_item = self.driver.find_element(By.CSS_SELECTOR, f'a[href="{target_href}"]')
                except:
                    # If not found (maybe virtual list scrolled), try to re-find matching items once
                    current_matches = self._find_matching_items(prompt)
                    target_item = None
                    for m in current_matches:
                        try:
                            if m.get_attribute("href") == target_href:
                                target_item = m
                                break
                        except: continue
                
                if not target_item:
                    self.log(f"⚠️ Không tìm thấy item {i+1} với link: {target_href}")
                    continue
            
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
                # If limit > 1, append index: ".../tom/tom_01" (extension handled later)
                current_output = output_base_path
                if limit > 1:
                     current_output = f"{output_base_path}_{i+1:02d}"
                
                # Default extension to .mp4 (will be corrected by _download_from_url if it's an image)
                current_output += ".mp4"
                
                # 4. Download
                # download_video will call _download_from_url which handles extension correction
                if self.download_video(current_output):
                    success_count += 1
                    self.log(f"✅ Downloaded variation {i+1}")
                else:
                    self.log(f"⚠️ Failed to download variation {i+1}")
                    
                # 5. Back to library (only if there are more to download)
                if i < limit - 1:
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
            
            # Check Content-Type to correct extension if needed
            content_type = response.headers.get('Content-Type', '').lower()
            base, ext = os.path.splitext(output_path)
            
            if 'image' in content_type and ext.lower() not in ['.png', '.jpg', '.jpeg', '.webp']:
                output_path = f"{base}.png"
                self.log(f"🖼️ Detected image content type, changing extension to .png")
            elif 'video' in content_type and ext.lower() not in ['.mp4', '.mov', '.webm']:
                output_path = f"{base}.mp4"
                self.log(f"📹 Detected video content type, changing extension to .mp4")
                
            self.log(f"💾 Lưu file tại: {output_path}")
            
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
                       timeout: int = 300, task: Optional[any] = None) -> bool:
    
        # PRE-GENERATION SNAPSHOT: Capture current items so we can identify the NEW ones later
        # We do this FIRST to avoid navigating away from /create after uploads
        initial_ids = set()
        try:
            self.log("📋 Ghi nhớ danh sách video cũ từ Library...")
            self.driver.get(f"{self.BASE_URL}/library")
            time.sleep(3)
            link_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/g/gen_"], a[href*="/t/task_"]')
            initial_ids = {el.get_attribute('href') for el in link_elements if el.get_attribute('href')}
        except Exception as e:
            self.log(f"⚠️ Không thể chụp snapshot library: {e}")

        # Step 1: Navigate to Create
        if not self.navigate_to_create():
            return False
        time.sleep(2)
        
        # Step 2: Configure video settings ONLY if different from last time
        current_settings = {
            "type": str(type).lower().strip() if type else "video",
            "aspect_ratio": str(aspect_ratio).strip() if aspect_ratio else "",
            "resolution": str(resolution).strip() if resolution else "",
            "duration": str(duration).strip() if duration else "",
            "variations": int(variations) if variations else 1
        }
        
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
            download_success = self._process_batch_download(prompt, variations, output_path, initial_ids=initial_ids, task=task)
        else:
            # Just wait if no download requested
            count = variations if variations else 1
            download_success = self.wait_for_generation(prompt=prompt, timeout=timeout, expected_count=count, initial_ids=initial_ids, task=task)
            
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
                
            output_dir = row.output_path if hasattr(row, 'output_path') and row.output_path else self.download_dir
            filename_base = f"sora_{row.stt}_{int(time.time())}"
            
            if row.save_name:
                # User wants specific name/folder: "tom" -> folder "tom", files "tom_01", "tom_02"...
                clean_name = os.path.splitext(row.save_name)[0] # remove extension
                
                # Create subfolder with same name
                output_dir = os.path.join(output_dir, clean_name)
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.log(f"📂 Created output directory: {output_dir}")
                except Exception as e:
                    self.log(f"⚠️ Could not create directory: {e}")
                    output_dir = row.output_path if hasattr(row, 'output_path') and row.output_path else self.download_dir # Fallback
                
                filename_base = clean_name
            
            # Use base path without extension for flexibility
            # download_video will append _01.png, _02.mp4 etc.
            output_path = os.path.join(output_dir, filename_base)
            
            # Run the main workflow with video settings and retry logic
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                if attempt > 0:
                    self.log(f"🔄 Đang thử lại tác vụ... (Lần {attempt+1}/{max_retries})")
                    # Dọn dẹp/làm mới trang trước khi thử lại
                    try:
                        self.driver.get(self.BASE_URL)
                        time.sleep(5)
                        # Verify đã vào được Sora chưa
                        check_url = self.driver.current_url.lower()
                        if 'sora.chatgpt.com' not in check_url:
                            self.log(f"⚠️ Chưa vào được Sora (đang ở {check_url}), thử lại navigate...")
                            self.driver.get(self.BASE_URL)
                            time.sleep(5)
                    except Exception as nav_err:
                        self.log(f"⚠️ Lỗi khi navigate lại: {nav_err}")
                        time.sleep(3)
                    
                    # Reset settings cache để force re-configure
                    self._last_settings = {}
                    
                success = self.generate_video(
                    prompt=row.prompt,
                    image_paths=getattr(row, 'image_paths', []) or ([row.image_path] if hasattr(row, 'image_path') and row.image_path else []),
                    output_path=output_path,
                    type=row.type,
                    aspect_ratio=row.aspect_ratio,
                    resolution=row.resolution,
                    duration=row.duration,
                    variations=variations, # Use the sanitized local variable
                    timeout=300,
                    task=row # Pass the whole row as task for metadata verification
                )
                
                if success:
                    break
                else:
                    self.log(f"⚠️ Thử lần {attempt+1}/{max_retries} thất bại.")
                    time.sleep(2)
            
            duration = time.time() - start_time
            
            return {
                "success": success,
                "prompt": row.prompt,
                "output_path": output_path if success else None,
                "duration_seconds": duration,
                "error": None if success else f"Generation failed after {max_retries} attempts"
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
