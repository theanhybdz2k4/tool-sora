import os
import psutil
import logging

logger = logging.getLogger(__name__)

def kill_browser_processes():
    """Kill all Playwright/Chromium processes to free up memory"""
    targets = ["chromium", "chrome.exe", "playwright"]
    killed_count = 0
    
    logger.info("Starting browser process cleanup...")
    
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info['name'].lower()
            if any(target in name for target in targets):
                logger.info(f"Killing process: {name} (PID: {proc.info['pid']})")
                proc.kill()
                killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    logger.info(f"Cleanup finished. Killed {killed_count} processes.")
    return killed_count

def check_memory_usage():
    """Returns memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)
