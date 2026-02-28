# -*- coding: utf-8 -*-
"""
Test script: Mở 2 browser với 2 profile khác nhau, kiểm tra navigate tới Sora
Mô phỏng đúng flow của tool khi chạy multi-thread
"""
import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.browser import BrowserCore
from services.sora_service import SoraAutomationService

PROFILES = ["sora01", "sora011"]
STAGGER_DELAY = 8  # seconds between browser starts

results = {}

def test_browser(profile_name, thread_id, port):
    """Test one browser instance"""
    print(f"\n{'='*60}")
    print(f"[T{thread_id}] === STARTING: profile={profile_name}, port={port} ===")
    print(f"{'='*60}")
    
    browser = None
    try:
        # Step 1: Init browser (giống _process_task)
        print(f"[T{thread_id}] Step 1: Khởi tạo BrowserCore...")
        browser = BrowserCore(profile_name=profile_name, headless=False)
        
        # Step 2: Init browser with initial URL (giống _process_task)
        print(f"[T{thread_id}] Step 2: init_browser(initial_url='https://sora.chatgpt.com', port={port})...")
        browser.init_browser(initial_url="https://sora.chatgpt.com", port=port)
        
        current_url = browser.driver.current_url
        print(f"[T{thread_id}] Step 2 DONE: Current URL = {current_url}")
        
        # Step 3: Create SoraAutomationService (giống _process_task)
        print(f"[T{thread_id}] Step 3: Tạo SoraAutomationService...")
        sora = SoraAutomationService(
            browser=browser,
            log_callback=lambda msg, tid=thread_id, pn=profile_name: print(f"[T{tid}|{pn}] {msg}")
        )
        
        current_url = browser.driver.current_url
        print(f"[T{thread_id}] Step 3 DONE: Current URL = {current_url}")
        
        # Step 4: navigate_to_create (giống process_row)
        print(f"[T{thread_id}] Step 4: navigate_to_create()...")
        ok = sora.navigate_to_create()
        
        current_url = browser.driver.current_url
        print(f"[T{thread_id}] Step 4 DONE: navigate_to_create = {ok}, URL = {current_url}")
        
        # Step 5: Check prompt input
        print(f"[T{thread_id}] Step 5: Tìm prompt input...")
        prompt_input = sora._find_prompt_input()
        has_prompt = prompt_input is not None
        print(f"[T{thread_id}] Step 5 DONE: Has prompt input = {has_prompt}")
        
        results[thread_id] = {
            "profile": profile_name,
            "success": ok and has_prompt,
            "url": current_url,
            "navigate_ok": ok,
            "has_prompt": has_prompt
        }
        
        print(f"\n[T{thread_id}] ✅ TEST PASSED!" if (ok and has_prompt) else f"\n[T{thread_id}] ❌ TEST FAILED!")
        
    except Exception as e:
        print(f"[T{thread_id}] ❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        results[thread_id] = {
            "profile": profile_name,
            "success": False,
            "error": str(e)
        }
    
    # Giữ browser mở 10s để user xem
    print(f"[T{thread_id}] Browser sẽ mở thêm 15s để bạn kiểm tra...")
    time.sleep(15)
    
    if browser:
        try:
            browser.close()
            print(f"[T{thread_id}] Browser đã đóng.")
        except:
            pass


def main():
    print("="*60)
    print("TEST: Mở 2 browser với staggered start")
    print(f"Profiles: {PROFILES}")
    print(f"Stagger delay: {STAGGER_DELAY}s")
    print("="*60)
    
    threads = []
    for i, profile in enumerate(PROFILES):
        thread_id = i + 1
        port = 9221 + thread_id
        
        t = threading.Thread(
            target=test_browser, 
            args=(profile, thread_id, port),
            daemon=True
        )
        threads.append(t)
        
        t.start()
        
        # Stagger: đợi trước khi start thread tiếp theo
        if i < len(PROFILES) - 1:
            print(f"\n⏳ Đợi {STAGGER_DELAY}s trước khi mở browser tiếp...")
            time.sleep(STAGGER_DELAY)
    
    # Wait for all threads
    for t in threads:
        t.join(timeout=120)
    
    # Print results
    print("\n" + "="*60)
    print("KẾT QUẢ TỔNG HỢP:")
    print("="*60)
    
    all_passed = True
    for tid, result in sorted(results.items()):
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"  Thread {tid} ({result['profile']}): {status}")
        if result.get("url"):
            print(f"    URL: {result['url']}")
        if result.get("error"):
            print(f"    Error: {result['error']}")
        if not result.get("success"):
            all_passed = False
    
    print(f"\n{'✅ ALL TESTS PASSED!' if all_passed else '❌ SOME TESTS FAILED!'}")


if __name__ == "__main__":
    main()
