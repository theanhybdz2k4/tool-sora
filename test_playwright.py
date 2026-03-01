import os
import sys
import time

# Thêm directory hiện tại vào sys.path để import được core và services
sys.path.append(os.getcwd())

from core.browser import BrowserCore
from services.sora_service import SoraAutomationService

def test_sora_playwright():
    print("🚀 Khởi động test Sora với Playwright...")
    browser = None
    try:
        browser = BrowserCore(headless=False)
        if not browser.init_browser():
            print("❌ Không thể khởi tạo browser")
            return

        sora = SoraAutomationService(browser=browser)
        
        print(f"🌐 Đang ở URL: {browser.page.url}")
        print(f"📄 Title: {browser.page.title()}")
        
        print("🔍 Kiểm tra login status...")
        if sora.is_logged_in():
            print("✅ Đã đăng nhập")
        else:
            print("❌ Chưa đăng nhập (Có thể cần đăng nhập thủ công nếu profile mới)")
            
        # Thử navigate sang library
        print("📂 Chuyển sang Library...")
        browser.page.goto("https://sora.chatgpt.com/library")
        time.sleep(3)
        print(f"✅ Đang ở: {browser.page.url}")
        
    except Exception as e:
        print(f"💥 Lỗi test: {e}")
    finally:
        if browser:
            print("👋 Đóng browser...")
            browser.close()

if __name__ == "__main__":
    test_sora_playwright()
