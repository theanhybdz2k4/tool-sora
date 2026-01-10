"""
JavaScript snippets for Sora automation
Extracted from sora_service.py for better maintainability and readability
"""


class SoraScripts:
    """Collection of JavaScript snippets used in Sora automation"""
    
    @staticmethod
    def find_open_new_sora_button():
        """Check if 'Open New Sora' button exists (indicates old Sora interface)
        
        Old Sora có:
        - Text "Open New Sora" trong div với class "flex items-center gap-2.5"
        - SVG với viewBox="0 0 100 100" và class="h-6 w-6 shrink-0"
        - Path có fill="url(#paint0_linear_1_881)" hoặc fill="url(#paint0_linear_...)"
        - linearGradient với id chứa "paint0_linear"
        """
        return """
            // Phương pháp 1: Tìm div với class "flex items-center gap-2.5" chứa text "Open New Sora"
            var divs = document.querySelectorAll('div');
            for (var div of divs) {
                if (div.offsetParent === null) continue;
                
                var text = (div.textContent || '').trim();
                if (text.includes('Open New Sora')) {
                    var classAttr = div.getAttribute('class') || '';
                    // Check class chứa "flex items-center gap"
                    if (classAttr.includes('flex') && classAttr.includes('items-center') && classAttr.includes('gap')) {
                        // Tìm SVG trong div này
                        var svg = div.querySelector('svg');
                        if (svg) {
                            var viewBox = svg.getAttribute('viewBox') || '';
                            // Check viewBox="0 0 100 100"
                            if (viewBox === '0 0 100 100') {
                                // Check path có fill="url(#paint0_linear_...)"
                                var paths = svg.querySelectorAll('path');
                                for (var path of paths) {
                                    var fill = path.getAttribute('fill') || '';
                                    if (fill.includes('paint0_linear')) {
                                        // Verify có linearGradient
                                        var defs = svg.querySelector('defs');
                                        if (defs) {
                                            var gradient = defs.querySelector('linearGradient[id*="paint0_linear"]');
                                            if (gradient) {
                                                return true;  // Đây là Old Sora!
                                            }
                                        }
                                        // Nếu có fill với paint0_linear thì cũng OK
                                        return true;
                                    }
                                }
                                // Nếu có viewBox="0 0 100 100" thì cũng OK (đặc trưng của Old Sora)
                                return true;
                            }
                        }
                    }
                }
            }
            
            // Phương pháp 2: Tìm bất kỳ element nào có text "Open New Sora" và SVG viewBox="0 0 100 100"
            var allElements = document.querySelectorAll('*');
            for (var elem of allElements) {
                if (elem.offsetParent === null) continue;
                
                var text = (elem.textContent || '').trim();
                if (text.includes('Open New Sora')) {
                    // Tìm SVG trong element hoặc parent
                    var svg = elem.querySelector('svg');
                    if (!svg && elem.parentElement) {
                        svg = elem.parentElement.querySelector('svg');
                    }
                    
                    if (svg) {
                        var viewBox = svg.getAttribute('viewBox') || '';
                        if (viewBox === '0 0 100 100') {
                            // Check path có fill với paint0_linear
                            var paths = svg.querySelectorAll('path');
                            for (var path of paths) {
                                var fill = path.getAttribute('fill') || '';
                                if (fill.includes('paint0_linear')) {
                                    return true;
                                }
                            }
                            // Nếu có viewBox="0 0 100 100" thì cũng OK
                            return true;
                        }
                    }
                }
            }
            
            return false;
        """
    
    @staticmethod
    def find_three_dot_menu():
        """Find 3-dot menu button (Settings button) in New Sora
        
        Nút Settings có:
        - aria-label="Settings"
        - SVG với 2 paths:
          - Path 1: M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16M2 12C2 6.477... (circle)
          - Path 2: M13.3 12a1.3 1.3 0 1 1-2.6 0 M17.3 12a1.3... M9.3 12a1.3... (3 dots trong 1 path)
        - viewBox="0 0 24 24"
        - Class: h-5 w-5
        """
        return """
            // Phương pháp 1: Tìm bằng aria-label="Settings" (ưu tiên cao nhất)
            var settingsBtns = document.querySelectorAll('button[aria-label="Settings"]');
            for (var btn of settingsBtns) {
                if (btn.offsetParent === null) continue;
                
                var svg = btn.querySelector('svg');
                if (!svg) continue;
                
                // Verify viewBox
                var viewBox = svg.getAttribute('viewBox') || '';
                if (viewBox !== '0 0 24 24') continue;
                
                // Verify paths
                var paths = svg.querySelectorAll('path');
                if (paths.length < 2) continue;
                
                var path1 = paths[0].getAttribute('d') || '';
                var path2 = paths[1].getAttribute('d') || '';
                
                // Path 1: Circle - phải chứa M12 4a8 8 0 và M2 12C2
                var hasCircle = (path1.includes('M12 4a8 8 0') || path1.includes('M2 12C2 6.477')) &&
                                (path1.includes('0 16') || path1.includes('6.477'));
                
                // Path 2: 3 dots - phải chứa cả 3 dots trong 1 path
                var hasThreeDots = path2.includes('M13.3 12a1.3') && 
                                   path2.includes('M17.3 12a1.3') && 
                                   path2.includes('M9.3 12a1.3') &&
                                   path2.includes('a1.3 1.3 0 1 1-2.6 0');
                
                if (hasCircle && hasThreeDots) {
                    return btn;
                }
            }
            
            // Phương pháp 2: Tìm tất cả button và check SVG pattern (fallback)
            var allBtns = document.querySelectorAll('button');
            
            for (var btn of allBtns) {
                if (btn.offsetParent === null) continue;
                
                var svg = btn.querySelector('svg');
                if (!svg) continue;
                
                var viewBox = svg.getAttribute('viewBox') || '';
                if (viewBox !== '0 0 24 24') continue;
                
                var paths = svg.querySelectorAll('path');
                if (paths.length < 2) continue;
                
                var path1 = paths[0].getAttribute('d') || '';
                var path2 = paths[1].getAttribute('d') || '';
                
                // Check pattern chính xác
                var hasCircle = path1.includes('M12 4a8 8 0') && 
                               (path1.includes('M2 12C2 6.477') || path1.includes('0 16'));
                
                var hasThreeDots = path2.includes('M13.3 12a1.3') && 
                                  path2.includes('M17.3 12a1.3') && 
                                  path2.includes('M9.3 12a1.3');
                
                if (hasCircle && hasThreeDots) {
                    return btn;
                }
            }
            
            return null;
        """
    
    @staticmethod
    def click_switch_to_old_sora():
        """Find and click 'Switch to old Sora' option in menu
        
        Menu item có:
        - role="menuitem"
        - Text "Switch to old Sora"
        - Nằm trong menu với data-radix-menu-content hoặc role="menu"
        """
        return """
            // Phương pháp 1: Tìm trong menu đã mở (ưu tiên)
            var menus = document.querySelectorAll('[role="menu"][data-state="open"], [data-radix-menu-content][data-state="open"]');
            for (var menu of menus) {
                if (menu.offsetParent === null) continue;
                
                // Tìm tất cả menuitem trong menu này
                var items = menu.querySelectorAll('[role="menuitem"]');
                for (var item of items) {
                    if (item.offsetParent === null) continue;
                    
                    var text = (item.textContent || '').trim();
                    // Tìm chính xác "Switch to old Sora"
                    if (text === 'Switch to old Sora' || text === 'Switch old Sora' ||
                        (text.toLowerCase().includes('switch') && text.toLowerCase().includes('old sora'))) {
                        // Scroll vào view
                        item.scrollIntoView({block: 'center', behavior: 'instant'});
                        // Click
                        item.click();
                        return 'clicked_in_menu';
                    }
                }
            }
            
            // Phương pháp 2: Tìm tất cả menuitem có text "Switch to old Sora"
            var allMenuItems = document.querySelectorAll('[role="menuitem"]');
            for (var item of allMenuItems) {
                if (item.offsetParent === null) continue;
                
                var text = (item.textContent || '').trim();
                if (text === 'Switch to old Sora' || text === 'Switch old Sora' ||
                    (text.toLowerCase().includes('switch') && text.toLowerCase().includes('old sora'))) {
                    item.scrollIntoView({block: 'center', behavior: 'instant'});
                    item.click();
                    return 'clicked_direct';
                }
            }
            
            // Phương pháp 3: Tìm bất kỳ element nào có text
            var allElements = document.querySelectorAll('*');
            for (var elem of allElements) {
                if (elem.offsetParent === null) continue;
                var text = (elem.textContent || '').trim();
                
                if (text === 'Switch to old Sora' || text === 'Switch old Sora') {
                    // Kiểm tra xem có phải clickable không
                    var tagName = elem.tagName.toLowerCase();
                    if (tagName === 'div' || tagName === 'button' || tagName === 'a' ||
                        elem.getAttribute('role') === 'menuitem') {
                        elem.scrollIntoView({block: 'center', behavior: 'instant'});
                        elem.click();
                        return 'clicked_element';
                    }
                }
            }
            
            return null;
        """
    
    @staticmethod
    def find_add_media_button():
        """Find + button or 'Attach media' button"""
        return """
            // Sora 1: Find + button near prompt
            var promptArea = document.querySelector('[placeholder*="Describe"], [placeholder*="video"], textarea, [contenteditable="true"]');
            if (promptArea) {
                // Find parent row containing the prompt
                var row = promptArea.parentElement;
                while (row && row !== document.body) {
                    // Look for buttons in this container
                    var btns = row.querySelectorAll('button');
                    for (var btn of btns) {
                        if (btn.offsetParent === null) continue;
                        
                        var text = btn.textContent.trim();
                        var svg = btn.querySelector('svg');
                        
                        // Check if it's a + button (small, has SVG, position on left)
                        if (svg && text === '' || text === '+') {
                            // Check for plus icon path
                            var path = svg ? svg.querySelector('path') : null;
                            if (path) {
                                var d = path.getAttribute('d') || '';
                                // Plus icon patterns
                                if (d.includes('M12') || d.includes('v4') || d.includes('h4') ||
                                    d.includes('M6') || d.includes('M5') || d.includes('1 1v')) {
                                    btn.click();
                                    return 'found_plus';
                                }
                            }
                        }
                    }
                    row = row.parentElement;
                }
            }
            
            // Sora 2: Find button with "Attach media" span
            var allBtns = document.querySelectorAll('button');
            for (var btn of allBtns) {
                var span = btn.querySelector('span');
                if (span && span.textContent.toLowerCase().includes('attach')) {
                    if (btn.offsetParent !== null) {
                        btn.click();
                        return 'found_attach';
                    }
                }
            }
            
            return false;
        """
    
    @staticmethod
    def click_upload_from_device():
        """Click 'Upload from device' in dropdown menu"""
        return """
            // Tìm menu item "Upload from device"
            var items = document.querySelectorAll('*');
            
            for (var item of items) {
                if (item.offsetParent === null) continue;
                
                var text = (item.textContent || '').toLowerCase().trim();
                
                // Match "Upload from device"
                if (text === 'upload from device' || 
                    text.includes('upload from device')) {
                    item.click();
                    return 'upload_device';
                }
            }
            
            // Fallback: Try clicking by partial match
            for (var item of items) {
                if (item.offsetParent === null) continue;
                var text = (item.textContent || '').toLowerCase();
                
                if (text.includes('from device') || 
                    (text.includes('upload') && !text.includes('library'))) {
                    item.click();
                    return 'partial_match';
                }
            }
            
            return false;
        """
    
    @staticmethod
    def check_image_loaded():
        """Check if uploaded image is visible and loaded"""
        return """
            var imgs = document.querySelectorAll('img');
            for (var img of imgs) {
                var src = img.src || '';
                if (src.startsWith('blob:') || src.includes('openai') || 
                    src.includes('oaiusercontent') || src.includes('sora')) {
                    if (img.offsetParent !== null && img.naturalWidth > 0) {
                        return true;
                    }
                }
            }
            return false;
        """
    
    @staticmethod
    def check_loading_spinner():
        """Check for loading spinner on image preview"""
        return """
            // Find image preview containers
            var previewAreas = document.querySelectorAll(
                '[class*="preview"], [class*="storyboard"], [class*="media"], ' +
                '[class*="thumbnail"], [class*="upload"]'
            );
            
            for (var area of previewAreas) {
                if (area.offsetParent === null) continue;
                
                // Check for loading indicators inside
                var spinners = area.querySelectorAll(
                    '[class*="loading"], [class*="spinner"], [class*="progress"], ' +
                    'svg[class*="animate"], circle, .loading, progress, ' +
                    '[aria-busy="true"], [class*="uploading"]'
                );
                
                for (var spinner of spinners) {
                    if (spinner.offsetParent !== null) {
                        return true;  // Still loading
                    }
                }
                
                // Also check for animated SVG (spinning circle)
                var svgs = area.querySelectorAll('svg');
                for (var svg of svgs) {
                    var style = window.getComputedStyle(svg);
                    if (style.animation && style.animation !== 'none') {
                        return true;  // Animated = loading
                    }
                }
            }
            
            return false;  // No loading found
        """
    
    @staticmethod
    def find_element_by_text(text, element_types="*"):
        """Generic function to find element by text content"""
        return f"""
            var elements = document.querySelectorAll('{element_types}');
            for (var elem of elements) {{
                if (elem.offsetParent === null) continue;
                var elemText = (elem.textContent || '').toLowerCase().trim();
                if (elemText.includes('{text.lower()}')) {{
                    return elem;
                }}
            }}
            return null;
        """
    
    # ==================== OLD SORA SPECIFIC SELECTORS ====================
    
    @staticmethod
    def find_prompt_textarea_old():
        """Tìm textarea mô tả video trong OLD Sora"""
        return """
            // Tìm textarea với placeholder "Describe your video..."
            var textarea = document.querySelector('textarea[placeholder*="Describe your video"]');
            if (textarea && textarea.offsetParent !== null) {
                return textarea;
            }
            
            // Fallback: tìm textarea trong composer area
            var textareas = document.querySelectorAll('textarea');
            for (var ta of textareas) {
                if (ta.offsetParent === null) continue;
                var placeholder = ta.getAttribute('placeholder') || '';
                if (placeholder.toLowerCase().includes('describe') || 
                    placeholder.toLowerCase().includes('video')) {
                    return ta;
                }
            }
            
            return null;
        """
    
    @staticmethod
    def find_attach_media_button_old():
        """Tìm nút attach media trong OLD Sora"""
        return """
            // Phương pháp 1: Tìm bằng aria-label
            var btn = document.querySelector('button[aria-label="Attach media"]');
            if (btn && btn.offsetParent !== null) return btn;
            
            // Phương pháp 2: Tìm bằng sr-only text
            var allBtns = document.querySelectorAll('button');
            for (var b of allBtns) {
                if (b.offsetParent === null) continue;
                var srOnly = b.querySelector('span.sr-only');
                if (srOnly && srOnly.textContent.toLowerCase().includes('attach media')) {
                    return b;
                }
            }
            
            // Phương pháp 3: Tìm nút + gần textarea
            var textarea = document.querySelector('textarea[placeholder*="Describe"]');
            if (textarea) {
                var parent = textarea.parentElement;
                while (parent && parent !== document.body) {
                    var btns = parent.querySelectorAll('button');
                    for (var btn of btns) {
                        if (btn.offsetParent === null) continue;
                        var svg = btn.querySelector('svg');
                        if (svg && btn.textContent.trim() === '') {
                            // Nút có SVG và không có text = nút icon
                            var path = svg.querySelector('path');
                            if (path) {
                                var d = path.getAttribute('d') || '';
                                // Pattern của icon + (plus)
                                if (d.includes('M12') || d.includes('v') || d.includes('h')) {
                                    return btn;
                                }
                            }
                        }
                    }
                    parent = parent.parentElement;
                }
            }
            
            return null;
        """
    
    @staticmethod
    def find_submit_button_old():
        """Tìm nút Create Video trong OLD Sora"""
        return """
            var allBtns = document.querySelectorAll('button');
            
            // Phương pháp 1: Tìm bằng sr-only text "Create video"
            for (var btn of allBtns) {
                if (btn.offsetParent === null) continue;
                var srOnly = btn.querySelector('span.sr-only');
                if (srOnly && srOnly.textContent.toLowerCase().includes('create video')) {
                    return {
                        element: btn,
                        disabled: btn.getAttribute('data-disabled') === 'true' || btn.disabled
                    };
                }
            }
            
            // Phương pháp 2: Tìm nút với icon arrow lên ở cuối composer
            for (var btn of allBtns) {
                if (btn.offsetParent === null) continue;
                var svg = btn.querySelector('svg');
                if (svg) {
                    var path = svg.querySelector('path');
                    if (path) {
                        var d = path.getAttribute('d') || '';
                        // Pattern của arrow up icon
                        if (d.includes('11.293 5.293') || d.includes('M11.293')) {
                            return {
                                element: btn,
                                disabled: btn.getAttribute('data-disabled') === 'true' || btn.disabled
                            };
                        }
                    }
                }
            }
            
            // Phương pháp 3: Tìm nút cuối cùng trong composer area
            var composer = document.querySelector('[class*="composer"]');
            if (composer) {
                var btns = composer.querySelectorAll('button');
                var lastBtn = null;
                for (var btn of btns) {
                    if (btn.offsetParent !== null) lastBtn = btn;
                }
                if (lastBtn) {
                    return {
                        element: lastBtn,
                        disabled: lastBtn.getAttribute('data-disabled') === 'true' || lastBtn.disabled
                    };
                }
            }
            
            return null;
        """
    
    @staticmethod
    def enter_text_and_trigger_events():
        """Set text value và trigger các events cần thiết"""
        return """
            var textarea = arguments[0];
            var text = arguments[1];
            
            // Set value
            textarea.value = text;
            
            // Trigger input event
            var inputEvent = new Event('input', { bubbles: true, cancelable: true });
            textarea.dispatchEvent(inputEvent);
            
            // Trigger change event
            var changeEvent = new Event('change', { bubbles: true, cancelable: true });
            textarea.dispatchEvent(changeEvent);
            
            // Trigger keyboard events
            var keydownEvent = new KeyboardEvent('keydown', { bubbles: true });
            textarea.dispatchEvent(keydownEvent);
            
            var keyupEvent = new KeyboardEvent('keyup', { bubbles: true });
            textarea.dispatchEvent(keyupEvent);
            
            return true;
        """
    
    @staticmethod
    def click_element_safely():
        """Click element một cách an toàn với scroll vào view"""
        return """
            var element = arguments[0];
            
            // Scroll vào view
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Wait a bit
            await new Promise(r => setTimeout(r, 100));
            
            // Click
            element.click();
            
            return true;
        """

    @staticmethod
    def make_file_input_visible():
        """Make hidden file input visible for interaction"""
        return """
            arguments[0].style.display = 'block';
            arguments[0].style.opacity = '1';
            arguments[0].style.visibility = 'visible';
            arguments[0].style.position = 'absolute';
            arguments[0].style.top = '0';
            arguments[0].style.left = '0';
        """
