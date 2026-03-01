# Selenium dependencies removed - using Playwright-based BrowserCore
import os
import time
import requests
import logging
from pathlib import Path
from typing import Optional, Callable, List



class SoraAutomationService:
    """Automate Sora video generation"""
    
    BASE_URL = "https://sora.chatgpt.com"
    
    def __init__(self, browser=None, download_dir: str = None, 
                 log_callback: Optional[Callable] = None, check_interval: int = 10):
        if browser is not None:
            self.browser = browser
            self.page = browser.page # Playwright Page
        else:
            raise ValueError("Browser (Playwright-based BrowserCore) must be provided")
        
        self.download_dir = download_dir or str(Path.cwd() / "downloads")
        self.log = log_callback or print
        self.check_interval = check_interval

        
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
                self.page.goto(self.BASE_URL, wait_until="domcontentloaded")
                time.sleep(5)
                # Verify bằng page title/content
                page_title = self.page.title().lower()
                real_url = self.page.url.lower()
                
                if 'sora' in page_title or 'sora.chatgpt.com' in real_url:
                    self.log(f"✅ Đã navigate đến Sora thành công (URL: {real_url})")
                    break
                elif 'auth.openai.com' in real_url or 'login' in real_url:
                    self.log(f"✅ Đang ở trang đăng nhập OpenAI")
                    break
                else:
                    self.log(f"⚠️ Navigate lần {nav_retry+1} - trang chưa load đúng (title='{page_title}', url='{real_url}')")
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
        """
        for attempt in range(3):
            try:
                current_url = self.page.url.lower()
                if 'auth.openai.com' in current_url or 'login.openai.com' in current_url:
                    return False
                
                logged_in_selectors = [
                    'a[href="/library"]',
                    'a[href="/explore"]',
                    'button[aria-label="Settings"]',
                    'button img[src*="avatar"]'
                ]
                
                for selector in logged_in_selectors:
                    if self.page.query_selector(selector):
                        return True
                
                if self._find_prompt_input():
                    return True
                
                content = self.page.content().lower()
                if 'describe your video' in content or 'storyboard' in content or 'sign out' in content:
                    return True
                
                if attempt < 2:
                    time.sleep(2)
            except Exception as e:
                self.log(f"⚠️ Lỗi checking login: {e}")
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
        """Chuyển sang giao diện Old Sora"""
        self.log("🔄 Kiểm tra và chuyển sang Old Sora...")
        
        for attempt in range(3):
            try:
                content = self.page.content().lower()
                if 'describe your image' in content or 'open new sora' in content:
                    self.log("✅ Đang ở giao diện Old Sora")
                    return True
                
                # Method 1: Settings button
                settings_btn = self.page.query_selector('button[aria-label="Settings"]')
                if settings_btn and settings_btn.is_visible():
                    settings_btn.click()
                    time.sleep(1.5)
                    
                    switch_item = self.page.query_selector("//*[contains(text(), 'Switch to old Sora')]")
                    if switch_item:
                        switch_item.click()
                        self.log("✅ Đã click 'Switch to old Sora' từ Settings")
                        time.sleep(3)
                        continue
                
                # Method 2: JS injection
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
                if self.page.evaluate(js_switch):
                    self.log("✅ Đã click 'Switch to old Sora' via JS")
                    time.sleep(3)
                    # Re-check
                    content_after = self.page.content().lower()
                    if 'describe your image' in content_after or 'open new sora' in content_after:
                        return True
            except Exception as e:
                self.log(f"⚠️ Lần thử {attempt+1} lỗi: {e}")
            time.sleep(2)
            
        self.log("⚠️ Không tìm thấy hoặc không chuyển được sang Old Sora")
        return False
    
    def navigate_to_create(self) -> bool:
        """Navigate to video creation page"""
        self.log("🌐 Đang điều hướng đến trang tạo...")
        
        for attempt in range(3):
            try:
                page_title = self.page.title().lower()
                real_url = self.page.url.lower()
                
                actually_on_sora = ('sora' in page_title or 'sora.chatgpt.com' in real_url)
                
                if not actually_on_sora:
                    self.page.goto(self.BASE_URL, wait_until="domcontentloaded")
                    time.sleep(5)
                
                if not self._switched_to_old_sora:
                    if self.switch_to_old_sora():
                        self._switched_to_old_sora = True
                    time.sleep(2)
                
                if self._find_prompt_input():
                    self.log("✅ Đã ở trang tạo video")
                    return True
                
                self.page.goto(self.BASE_URL, wait_until="domcontentloaded")
                time.sleep(5)
                
                if self._is_cloudflare_challenge():
                    if self._wait_for_cloudflare():
                        continue
                
                if self._find_prompt_input():
                    return True
                    
                time.sleep(3)
            except Exception as e:
                self.log(f"❌ Lỗi navigation lần {attempt+1}: {e}")
                try: self.page.goto(self.BASE_URL)
                except: pass
        return False

    
    def _is_cloudflare_challenge(self) -> bool:
        """Check if Cloudflare challenge page is displayed"""
        try:
            title = self.page.title().lower()
            if 'just a moment' in title or 'attention required' in title:
                return True
            
            content = self.page.content().lower()
            strict_indicators = [
                'xác minh bạn là con người',
                'verify you are human',
                'checking your browser before',
                'please wait while we verify',
                'chờ một chút'
            ]
            return any(ind in content for ind in strict_indicators)
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
        """Quay lại trang tạo"""
        self.log("🔙 Quay lại trang tạo...")
        try:
            # Press ESC
            self.page.keyboard.press("Escape")
            time.sleep(1)
            if self._find_prompt_input(): return True
            
            # Click Logo
            logo = self.page.query_selector('a[href="/"], [aria-label="Sora"], [aria-label="Home"]')
            if logo and logo.is_visible():
                logo.click()
                time.sleep(2)
                if self._find_prompt_input(): return True
            
            # Direct Navigate
            self.page.goto(self.BASE_URL)
            time.sleep(2)
            return self._find_prompt_input() is not None
        except Exception as e:
            self.log(f"⚠️ Error navigating back: {e}")
            self.page.goto(self.BASE_URL)
            time.sleep(2)
            return False

    
    def _find_prompt_input(self):
        """Tìm ô nhập prompt"""
        selectors = [
            'textarea[placeholder*="Describe"]',
            'textarea[placeholder*="video"]',
            'div[contenteditable="true"]',
            '[role="textbox"]',
            'textarea',
        ]
        for selector in selectors:
            try:
                elem = self.page.query_selector(selector)
                if elem and elem.is_visible():
                    return elem
            except: continue
        return None

    
    # ==================== IMAGE UPLOAD ====================
    
    def upload_image(self, image_path: str) -> bool:
        """Upload ảnh tham chiếu"""
        if not image_path or not os.path.exists(image_path):
            self.log("⚠️ File ảnh không tồn tại")
            return False
            
        self.log(f"📤 Đang upload ảnh: {os.path.basename(image_path)}")
        try:
            # Playwright make it easier to set input files
            file_input = self.page.query_selector('input[type="file"]')
            if not file_input:
                self.log("⚠️ Không tìm thấy input file")
                return False
            
            file_input.set_input_files(image_path)
            self.log("📤 Đã chọn file, đang chờ modal...")
            time.sleep(2)
            
            self._handle_media_upload_agreement()
            time.sleep(2)
            
            if self._verify_image_uploaded():
                self.log("✅ Upload ảnh hoàn tất")
                return True
            else:
                self.log("❌ Ảnh CHƯA được upload")
                return False
        except Exception as e:
            self.log(f"❌ Lỗi upload: {e}")
            return False

    
    def _verify_image_uploaded(self) -> bool:
        """Kiểm tra xem ảnh đã được upload thành công chưa"""
        for _ in range(5):
            try:
                preview_selectors = [
                    'img[src*="blob:"]', 
                    'img[src*="data:"]',
                    '[data-testid*="preview"]',
                    '[data-testid*="thumbnail"]',
                    '.preview img',
                    '.storyboard img',
                ]
                for selector in preview_selectors:
                    if self.page.query_selector(selector):
                        self.log("✅ Tìm thấy preview ảnh")
                        return True
            except: pass
            time.sleep(1)
        return False
    
    def _handle_media_upload_agreement(self) -> bool:
        """Xử lý modal 'Media upload agreement'"""
        self.log("⏳ Kiểm tra modal Media upload agreement...")
        
        try:
            # Chờ text xuất hiện
            if 'media upload agreement' not in self.page.content().lower():
                self.log("ℹ️ Không thấy modal agreement")
                return False

            self.log("📋 Tìm thấy modal Media upload agreement")
            
            # Click all checkboxes
            checkboxes = self.page.query_selector_all('input[type="checkbox"], [role="checkbox"]')
            for cb in checkboxes:
                try: cb.click()
                except: pass
            
            # Click Accept
            accept_btns = self.page.query_selector_all("button")
            for btn in accept_btns:
                text = btn.inner_text().lower()
                if 'accept' in text or 'agree' in text:
                    btn.click()
                    self.log("✅ Đã click Accept")
                    time.sleep(2)
                    return True
            
            return False
        except Exception as e:
            self.log(f"⚠️ Lỗi xử lý modal: {e}")
            return False
    
    # ==================== PROMPT INPUT ====================
    
    def enter_prompt(self, prompt: str) -> bool:
        """Nhập prompt vào ô input - dùng fill() + dispatch events cho React"""
        self.log(f"📝 Nhập prompt: {prompt[:50]}...")
        try:
            input_elem = self._find_prompt_input()
            if not input_elem:
                self.log("❌ Không tìm thấy ô nhập prompt")
                return False
            
            # Click để focus
            input_elem.click()
            time.sleep(0.3)
            
            # Dùng fill() cho nhanh
            input_elem.fill(prompt)
            time.sleep(0.3)
            
            # Dispatch events để React nhận ra thay đổi và enable submit button
            self.page.evaluate("""
            (function() {
                var el = document.querySelector('textarea, [role="textbox"], div[contenteditable="true"]');
                if (el) {
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    // React 18 native input setter trick
                    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value');
                    if (nativeInputValueSetter && nativeInputValueSetter.set) {
                        nativeInputValueSetter.set.call(el, el.value);
                    }
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }
            })()
            """)
            time.sleep(0.5)
            
            self.log("✅ Đã nhập prompt")
            return True
        except Exception as e:
            self.log(f"❌ Lỗi nhập prompt: {e}")
            return False

    
    # ==================== GENERATE ====================
    
    def click_generate(self) -> bool:
        """Click nút Generate/Create/Remix - chờ button enable trước khi click"""
        self.log("🚀 Nhấn Generate...")
        try:
            # Chờ submit button enable (tối đa 5s)
            submit_btn = None
            for wait in range(10):
                btns = self.page.query_selector_all('button')
                for btn in btns:
                    try:
                        # Check data-disabled attribute
                        is_disabled = btn.get_attribute('disabled') or btn.get_attribute('data-disabled') == 'true'
                        if is_disabled:
                            continue
                        
                        text = btn.inner_text().lower().strip()
                        
                        # Nút "Remix" (khi có image upload)
                        if text == 'remix':
                            submit_btn = btn
                            break
                        
                        # Nút "Create image/video" (sr-only text, chỉ có prompt)
                        sr = btn.query_selector('.sr-only')
                        if sr:
                            sr_text = sr.inner_text().lower()
                            if 'create' in sr_text:
                                submit_btn = btn
                                break
                    except: continue
                
                if submit_btn:
                    break
                time.sleep(0.5)
            
            if submit_btn:
                submit_btn.click()
                btn_text = submit_btn.inner_text().strip() or 'Create'
                self.log(f"✅ Đã click {btn_text}")
                time.sleep(2)
                return True
            
            # Fallback: JS force click bất kỳ nút nào có text create/remix
            js_click = """
            (function() {
                var btns = document.querySelectorAll('button');
                for (var btn of btns) {
                    var sr = btn.querySelector('.sr-only');
                    var text = ((sr ? sr.textContent : '') + ' ' + btn.textContent).toLowerCase();
                    if (text.includes('create') || text.includes('remix')) {
                        btn.disabled = false;
                        btn.removeAttribute('disabled');
                        btn.removeAttribute('data-disabled');
                        btn.click(); 
                        return true;
                    }
                }
                return false;
            })()
            """
            if self.page.evaluate(js_click):
                self.log("✅ Đã click Generate (JS force)")
                time.sleep(2)
                return True
            
            self.log("❌ Không tìm thấy nút Generate/Remix")
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
                     # Normalize duration format: Sora UI shows "20s", "15s", "10s", "5s"
                     dur_text = duration.replace('seconds', '').replace(' ', '').strip()
                     if not dur_text.endswith('s'):
                         dur_text = f"{dur_text}s"
                     self._set_dropdown_option(dur_text, "duration")
                     time.sleep(0.5)
            
            # Variations
            if variations:
                # Store Variations setting
                self._last_settings['variations'] = variations
                
                # Dropdown hiển thị: "4 videos", "2 videos", "1 video" hoặc "X images"
                media_keyword = "image" if type and "image" in type.lower() else "video"
                if int(variations) == 1:
                    var_text = f"1 {media_keyword}"
                else:
                    var_text = f"{variations} {media_keyword}s"
                
                self._set_dropdown_option(var_text, "variations")
                time.sleep(0.5)
            
            self.log("✅ Đã cấu hình video settings")
            return True
            
        except Exception as e:
            self.log(f"⚠️ Lỗi cấu hình settings: {e}")
            return False
    
    def _set_dropdown_option(self, value: str, option_type: str) -> bool:
        """Thiết lập option trong dropdown - dựa trên cấu trúc thực tế của Sora UI
        
        Sora UI sử dụng button[role='combobox'] cho mỗi setting.
        Thứ tự các button (khi ở mode Video): Type, Aspect, Resolution, Duration, Variations
        Thứ tự các button (khi ở mode Image): Type, Aspect, Variations
        Dropdown options có role='option'
        """
        self.log(f"⚙️ Setting {option_type} to '{value}'...")
        
        # Mapping option_type -> index trong danh sách combobox buttons
        # Video mode (6 buttons): Type(0), Aspect(1), Resolution(2), Duration(3), Variations(4), Presets(5)
        # Image mode (4 buttons): Type(0), Aspect(1), Variations(2), Presets(3)
        # Presets luôn là button CUỐI CÙNG → Variations là button ÁP CHÓT (-2)
        type_to_index = {
            "type": 0,        # Luôn là button đầu tiên
            "aspect": 1,      # Button thứ 2
            "resolution": 2,  # Button thứ 3 (chỉ Video mode)
            "duration": 3,    # Button thứ 4 (chỉ Video mode)
            "variations": -2, # Luôn là button ÁP CHÓT (trước Presets)
        }
        
        search_val = value.lower().strip()
        
        for attempt in range(3):
            try:
                # Lấy tất cả combobox buttons
                buttons = self.page.query_selector_all('button[role="combobox"]')
                if not buttons:
                    self.log(f"  ⚠️ Không tìm thấy combobox buttons")
                    time.sleep(1)
                    continue
                
                # Xác định button index
                btn_index = type_to_index.get(option_type, 0)
                if btn_index < 0:
                    btn_index = len(buttons) + btn_index  # -2 -> len-2 (áp chót)
                
                if btn_index < 0 or btn_index >= len(buttons):
                    self.log(f"  ⚠️ Button index {btn_index} ngoài phạm vi ({len(buttons)} buttons)")
                    return False
                
                target_btn = buttons[btn_index]
                current_text = target_btn.inner_text().strip()
                self.log(f"  📌 Button #{btn_index}: '{current_text}'")
                
                # Click để mở dropdown
                target_btn.click()
                time.sleep(0.5)
                
                # Tìm và click option trong dropdown
                options = self.page.query_selector_all('div[role="option"]')
                if not options:
                    # Thử lại với selector khác
                    options = self.page.query_selector_all('[role="option"]')
                
                for opt in options:
                    opt_text = opt.inner_text().lower().strip()
                    # Match chính xác hoặc contains
                    if search_val == opt_text or search_val in opt_text or opt_text.startswith(search_val):
                        opt.click()
                        time.sleep(0.3)
                        self.log(f"  ✅ Đã chọn {option_type}: {value}")
                        return True
                
                # Không tìm thấy option -> đóng dropdown
                self.log(f"  ⚠️ Không tìm thấy option '{value}' trong dropdown")
                self.page.keyboard.press("Escape")
                time.sleep(0.5)
                
            except Exception as e:
                self.log(f"  ⚠️ Lỗi dropdown lần {attempt+1}: {e}")
                try:
                    self.page.keyboard.press("Escape")
                except: pass
                time.sleep(1)
        
        return False

    
    def wait_for_generation(self, prompt: str = None, timeout: int = 400, expected_count: int = 1, initial_ids: set = None, task: Optional[any] = None) -> Optional[List[str]]:
        """Đợi kết quả tạo hoàn tất:
        Phase 1: Chờ task MỚI xuất hiện ở data-index="1" (phải thấy /t/task_ trước)
        Phase 2: Chờ task đó chuyển thành /g/gen_ (hoàn tất)
        """
        self.log(f"⏳ Đang chờ tạo kết quả... (timeout: {timeout}s)")
        start_time = time.time()
        task_started = False
        had_progress = False  # Đã từng thấy % chưa
        
        # Navigate đến library
        if "/library" not in self.page.url:
            self.page.goto(f"{self.BASE_URL}/library", wait_until="domcontentloaded")
            time.sleep(5)
        else:
            self.page.reload(wait_until="domcontentloaded")
            time.sleep(5)
        
        last_reload_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                elapsed = int(time.time() - start_time)
                first_item = self.page.query_selector('div[data-index="1"]')
                
                if not first_item:
                    self.log(f"⏳ Chờ library render... ({elapsed}s)")
                    time.sleep(3)
                    continue
                
                task_link = first_item.query_selector('a[href*="/t/task_"]')
                gen_link = first_item.query_selector('a[href*="/g/gen_"]')
                
                # ===== PHASE 1: Chờ task MỚI xuất hiện =====
                if not task_started:
                    if task_link:
                        task_started = True
                        self.log(f"🔄 Task mới phát hiện! Đang xử lý... ({elapsed}s)")
                    elif gen_link:
                        self.log(f"⏳ Chờ task mới xuất hiện... ({elapsed}s)")
                        time.sleep(5)
                        self.page.reload(wait_until="domcontentloaded")
                        time.sleep(5)
                        last_reload_time = time.time()
                        continue
                    else:
                        time.sleep(3)
                        continue
                
                # ===== PHASE 2: Chờ task hoàn tất =====
                if gen_link:
                    # HOÀN TẤT!
                    gen_links = first_item.query_selector_all('a[href*="/g/gen_"]')
                    hrefs = list(dict.fromkeys([
                        link.get_attribute('href') for link in gen_links 
                        if link.get_attribute('href')
                    ]))
                    if hrefs:
                        self.log(f"✅ Hoàn tất! {len(hrefs)} kết quả!")
                        return hrefs[:expected_count]
                
                if task_link:
                    # Check lỗi
                    item_text = first_item.inner_text()
                    if 'unexpected error' in item_text.lower() or 'violate' in item_text.lower():
                        self.log(f"❌ Task bị lỗi: {item_text[:100]}")
                        return None
                    
                    # Check progress
                    progress = first_item.query_selector('div.absolute')
                    has_pct = False
                    if progress:
                        pct = progress.inner_text().strip()
                        if pct.endswith('%'):
                            has_pct = True
                            had_progress = True
                            self.log(f"🔄 Đang tạo... {pct} ({elapsed}s)")
                    
                    if not has_pct:
                        if had_progress:
                            # Đã thấy % trước đó nhưng giờ mất → task có thể đã xong!
                            self.log(f"🔄 Progress biến mất, reload check... ({elapsed}s)")
                            self.page.reload(wait_until="domcontentloaded")
                            time.sleep(5)
                            last_reload_time = time.time()
                            had_progress = False  # Reset để không reload liên tục
                            continue
                        else:
                            self.log(f"🔄 Đang xử lý... ({elapsed}s)")
                
                time.sleep(5)
                
                # Reload mỗi 45s
                if time.time() - last_reload_time > 45:
                    self.page.reload(wait_until="domcontentloaded")
                    time.sleep(5)
                    last_reload_time = time.time()
                    
            except Exception as e:
                self.log(f"⚠️ Warning: {e}")
                time.sleep(5)
        
        self.log(f"❌ Timeout sau {timeout}s")
        return None
    
    def _get_generation_progress(self) -> Optional[str]:
        """Lấy progress % của task đang chạy"""
        try:
            # Sora hiển thị % trong div nằm giữa circle SVG
            progress_divs = self.page.query_selector_all('div.absolute')
            for div in progress_divs:
                text = div.inner_text().strip()
                if text and text.endswith('%'):
                    return text
        except: pass
        return None

    def _find_matching_items(self, prompt: str = None) -> List[any]:
        """Tìm các item ĐÃ HOÀN TẤT (có link /g/gen_)"""
        found = []
        try:
            containers = self.page.query_selector_all('a[href*="/g/gen_"]')

            for container in containers:
                try:
                    text = container.inner_text().lower()
                    if prompt and prompt.lower() not in text:
                        continue
                    found.append(container)
                except: continue
            return found
        except:
            return []


    def _process_batch_download(self, prompt: str, variations: int, output_base_path: str, initial_ids: set = None, task: Optional[any] = None) -> bool:
        """Download batch các biến thể - tối ưu giảm reload"""
        self.log(f"📥 Bắt đầu download batch ({variations} items)...")
        success_count = 0
        limit = max(1, min(int(variations), 4))
        
        new_item_hrefs = self.wait_for_generation(prompt=prompt, expected_count=limit, initial_ids=initial_ids, task=task)
        if not new_item_hrefs:
            self.log("❌ Không tìm thấy kết quả mới")
            return False
        
        for i, href in enumerate(new_item_hrefs[:limit]):
            try:
                self.log(f"📹 Downloading item {i+1}/{limit}...")
                
                # Navigate trực tiếp đến detail page thay vì click
                detail_url = f"{self.BASE_URL}{href}" if href.startswith('/') else href
                self.page.goto(detail_url, wait_until="domcontentloaded")
                time.sleep(3)
                
                out_path = f"{output_base_path}_{i+1:02d}.mp4" if limit > 1 else f"{output_base_path}.mp4"
                if self.download_video(out_path):
                    success_count += 1
                    
            except Exception as e:
                self.log(f"⚠️ Lỗi download item {i+1}: {e}")
        
        # Quay lại trang tạo 1 lần duy nhất sau khi download xong tất cả
        self._navigate_back_to_create()
        return success_count > 0
    
    def _count_video_items(self) -> int:
        """Đếm số lượng video/ảnh trong library"""
        try:
            links = self.page.query_selector_all('a[href*="/g/gen_"]')
            return len(links)
        except Exception as e:
            self.log(f"⚠️ Lỗi đếm video: {e}")
            return 0
    
    def _check_notification_bell(self) -> bool:
        """Kiểm tra chuông thông báo có badge không"""
        try:
            badge = self.page.query_selector('[aria-label*="notification"] [class*="badge"], button[aria-label*="Notification"] span')
            if badge and badge.is_visible():
                text = badge.inner_text().strip()
                return bool(text and (text.isdigit() or text == '•'))
            return False
        except:
            return False
    
    def _has_recent_video(self, seconds: int) -> bool:
        """Kiểm tra xem có video mới tạo không"""
        try:
            content = self.page.content().lower()
            return 'new video' in content or 'just now' in content
        except:
            return False
    
    def _click_first_video(self):
        """Click vào video đầu tiên trong library"""
        try:
            time.sleep(2)
            first_item = self.page.query_selector('a[href*="/g/gen_"]')
            if first_item:
                first_item.scroll_into_view_if_needed()
                first_item.click()
                self.log("📹 Đã click video đầu tiên")
                time.sleep(3)
                return True
            return False
        except Exception as e:
            self.log(f"⚠️ Không thể click video: {e}")
            return False
    
    # ==================== DOWNLOAD ====================
    
    def download_video(self, output_path: str) -> bool:
        """Download video/ảnh từ detail page bằng Playwright"""
        self.log(f"📥 Đang download kết quả lưu vào: {output_path}")
        
        try:
            # Method 1: Tìm nút download (circle-arrow-down icon) trên toolbar
            # Sora UI: icon download nằm ở top-right toolbar
            download_selectors = [
                'button[aria-label*="ownload"]',
                'a[download]',
                'button[aria-label*="Save"]',
            ]
            
            for selector in download_selectors:
                download_btn = self.page.query_selector(selector)
                if download_btn and download_btn.is_visible():
                    try:
                        with self.page.expect_download(timeout=30000) as download_info:
                            download_btn.click()
                        download = download_info.value
                        download.save_as(output_path)
                        self.log(f"✅ Download thành công!")
                        return True
                    except Exception as e:
                        self.log(f"⚠️ Download button failed: {e}")
                        continue
            
            # Method 2: Tìm video/img source trực tiếp và download qua URL
            video = self.page.query_selector('video[src]')
            if video:
                src = video.get_attribute('src')
                if src and self._is_valid_video_url(src):
                    return self._download_from_url(src, output_path)
            
            # Method 3: Tìm img source (cho Image mode)
            img = self.page.query_selector('img[src*="dalle"], img[src*="generation"], img[src*="openai"]')
            if img:
                src = img.get_attribute('src')
                if src and src.startswith('http'):
                    # Đổi extension sang .png cho image
                    base, ext = os.path.splitext(output_path)
                    if ext.lower() in ['.mp4', '.mov', '.webm']:
                        output_path = f"{base}.png"
                    return self._download_from_url(src, output_path)
            
            # Method 4: JS fallback - tìm bất kỳ button download nào
            js_download = """
            (function() {
                var btns = document.querySelectorAll('button, a');
                for (var i = 0; i < btns.length; i++) {
                    var label = (btns[i].getAttribute('aria-label') || '').toLowerCase();
                    var text = (btns[i].textContent || '').toLowerCase();
                    if (label.includes('download') || text.includes('download')) {
                        btns[i].click(); return true;
                    }
                }
                return false;
            })();
            """
            if self.page.evaluate(js_download):
                time.sleep(5)
                return True
                
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
            
            # Get cookies from browser context
            cookies = {}
            for cookie in self.page.context.cookies():
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
        """Main workflow - không cần snapshot, check data-index=0 trong library"""
        
        # BƯỚC 1: Navigate đến trang tạo (nếu chưa ở đó)
        if not self._find_prompt_input():
            if not self.navigate_to_create(): return False
        
        # BƯỚC 2: Configure settings
        current_settings = {
            "type": str(type).lower().strip() if type else "video",
            "aspect_ratio": str(aspect_ratio).strip() if aspect_ratio else "",
            "resolution": str(resolution).strip() if resolution else "",
            "duration": str(duration).strip() if duration else "",
            "variations": variations if variations else 1
        }
        
        if current_settings != self._last_settings:
            self.configure_video_settings(**current_settings)
            self._last_settings = current_settings.copy()
        
        # BƯỚC 3: Upload images
        if image_paths:
            for img in image_paths: 
                if img: self.upload_image(img)
        
        # BƯỚC 4: Nhập prompt
        if not self.enter_prompt(prompt): return False
        
        # BƯỚC 5: Click Generate
        if not self.click_generate(): return False
        
        # BƯỚC 6: Wait & Download
        if output_path:
            return self._process_batch_download(prompt, variations, output_path, None, task)
        else:
            return self.wait_for_generation(prompt, timeout, variations, None, task)

    
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
                
            # Determine output directory (parent folder, NOT the file path)
            if hasattr(row, 'output_path') and row.output_path:
                # output_path from excel is a FILE path like .../Output/cyber_city.mp4
                # We need the DIRECTORY part only
                output_dir = os.path.dirname(row.output_path)
                if not output_dir:
                    output_dir = self.download_dir
            else:
                output_dir = self.download_dir
            
            filename_base = f"sora_{row.stt}_{int(time.time())}"
            
            # Determine save name: from save_name field or from output_path filename
            save_name = None
            if hasattr(row, 'save_name') and row.save_name:
                save_name = row.save_name
            elif hasattr(row, 'savename') and row.savename:
                save_name = row.savename
            elif hasattr(row, 'output_path') and row.output_path:
                # Extract filename from output_path: .../cyber_city.mp4 -> cyber_city
                save_name = os.path.basename(row.output_path)
            
            if save_name:
                clean_name = os.path.splitext(save_name)[0]  # remove extension
                
                # Create subfolder with same name
                output_dir = os.path.join(output_dir, clean_name)
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.log(f"📂 Created output directory: {output_dir}")
                except Exception as e:
                    self.log(f"⚠️ Could not create directory: {e}")
                    output_dir = self.download_dir
                
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
                    try:
                        self.page.goto(self.BASE_URL)
                        time.sleep(5)
                    except: pass
                    self._last_settings = {}
                    
                success = self.generate_video(
                    prompt=row.prompt,
                    image_paths=getattr(row, 'image_paths', []) or ([row.image_path] if hasattr(row, 'image_path') and row.image_path else []),
                    output_path=output_path,
                    type=row.type,
                    aspect_ratio=row.aspect_ratio,
                    resolution=row.resolution,
                    duration=row.duration,
                    variations=variations,
                    timeout=300,
                    task=row
                )
                if success: break

            
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
