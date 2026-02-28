import undetected_chromedriver as uc
import threading
import time
import os

def run_browser(thread_id):
    print(f"[{thread_id}] Starting initialization...")
    start_time = time.time()
    
    options = uc.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    # Each thread needs its own user-data-dir
    profile_dir = os.path.join(os.getcwd(), f"test_profile_{thread_id}")
    options.add_argument(f"--user-data-dir={profile_dir}")
    
    # Try with user_multi_procs=True, use_subprocess=True
    driver = uc.Chrome(
        options=options, 
        user_multi_procs=True, 
        use_subprocess=True
    )
    
    elapsed = time.time() - start_time
    print(f"[{thread_id}] Initialized in {elapsed:.2f}s")
    
    driver.get("https://example.com")
    print(f"[{thread_id}] Title: {driver.title}")
    
    time.sleep(2)
    driver.quit()
    print(f"[{thread_id}] Closed.")

t1 = threading.Thread(target=run_browser, args=(1,))
t2 = threading.Thread(target=run_browser, args=(2,))
t1.start()
t2.start()
t1.join()
t2.join()
