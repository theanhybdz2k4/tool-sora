# -*- coding: utf-8 -*-
"""
Test script - Test IMAGE type trên Sora
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.browser import BrowserCore
from services.sora_service import SoraAutomationService
from services.sheets_service import SheetRow

def log(msg):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def main():
    log("🧪 === TEST IMAGE TYPE ===")
    
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Test IMAGE
    task = SheetRow(
        row_index=1,
        stt="1",
        prompt="A cute cat sitting on a windowsill looking at the rain outside, watercolor style",
        save_name="test_image",
        output_path=output_dir,
        type="image",
        aspect_ratio="1:1",
        duration="",
        resolution="",
        variations=1
    )
    
    log(f"📋 Task: type={task.type}, ratio={task.aspect_ratio}")
    log(f"   Prompt: {task.prompt[:60]}...")
    
    profile_name = "sora01"
    log(f"🌐 Khởi tạo browser: {profile_name}")
    
    browser = None
    try:
        browser = BrowserCore(profile_name=profile_name, headless=False)
        driver = browser.init_browser(initial_url="https://sora.chatgpt.com")
        
        if not driver:
            log("❌ Không thể khởi tạo browser!")
            return
        
        log(f"✅ Browser OK (title={driver.title})")
        
        sora = SoraAutomationService(
            browser=browser,
            download_dir=output_dir,
            log_callback=log
        )
        
        log("✅ SoraService OK")
        
        # Chạy task
        result = sora.process_row(task)
        
        if result.get("success"):
            log(f"✅ TEST IMAGE THÀNH CÔNG! Duration: {result.get('duration_seconds', 0):.1f}s")
        else:
            log(f"❌ TEST IMAGE THẤT BẠI: {result.get('error')}")
        
    except Exception as e:
        log(f"❌ LỖI: {e}")
        import traceback
        traceback.print_exc()
    finally:
        log("🧹 Dọn dẹp...")
        if browser:
            try:
                input("Nhấn Enter để đóng browser...")
            except:
                pass
            browser.close()
    
    log("🧪 === KẾT THÚC TEST ===")

if __name__ == "__main__":
    main()
