"""
Application settings and configuration
"""
import os
import json
from pathlib import Path

import sys

# Base directories
# Version
VERSION = "1.0.2"

# Base directories
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    # Application code is in _internal or bundled
    APP_EXEC_DIR = Path(sys.executable).parent
    
    # Persistent data goes to %APPDATA%
    DATA_ROOT = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / "SoraTool"
    BASE_DIR = APP_EXEC_DIR
else:
    # Running as script
    BASE_DIR = Path(__file__).parent.parent
    DATA_ROOT = BASE_DIR
    APP_EXEC_DIR = BASE_DIR

CONFIG_DIR = DATA_ROOT / "config"
DOWNLOADS_DIR = DATA_ROOT / "downloads"
LOGS_DIR = DATA_ROOT / "logs"
CHROME_CACHE_DIR = DATA_ROOT / "chrome_cache"
PROFILES_DIR = str(DATA_ROOT / "data" / "profiles")

# Create directories if not exist
for dir_path in [DATA_ROOT, CONFIG_DIR, DOWNLOADS_DIR, LOGS_DIR, CHROME_CACHE_DIR, Path(PROFILES_DIR)]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Data Migration (Run only once if local data exists and remote is empty)
def migrate_data():
    if getattr(sys, 'frozen', False):
        local_data = APP_EXEC_DIR / "data"
        local_config = APP_EXEC_DIR / "config"
        
        # Check if we have local data but haven't migrated it to DATA_ROOT yet
        if local_data.exists() and not (DATA_ROOT / "data").exists():
            import shutil
            try:
                print(f"Migrating data from {local_data} to {DATA_ROOT / 'data'}")
                shutil.copytree(local_data, DATA_ROOT / "data", dirs_exist_ok=True)
                if local_config.exists():
                    shutil.copytree(local_config, DATA_ROOT / "config", dirs_exist_ok=True)
            except Exception as e:
                print(f"Migration error: {e}")

migrate_data()

# Browser settings for Playwright
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
PAGE_LOAD_TIMEOUT = 60
ELEMENT_TIMEOUT = 30
HEADLESS_MODE = False

# Sora URLs
SORA_URL = "https://sora.chatgpt.com"
SORA_LOGIN_URL = "https://sora.chatgpt.com"
SORA_CREATE_URL = "https://sora.chatgpt.com"

# Default settings
DEFAULT_SETTINGS = {
    "max_threads": 4,
    "thread_delay_seconds": 2,
    "wait_timeout_seconds": 300,
    "auto_download": True,
    "download_format": "mp4",
    "default_aspect_ratio": "16:9",
    "default_duration": "5s",
    "check_interval_seconds": 10,
}

# Settings file path
SETTINGS_FILE = CONFIG_DIR / "app_settings.json"


def load_settings() -> dict:
    """Load settings from file or return defaults"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                return {**DEFAULT_SETTINGS, **saved}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving settings: {e}")


# Profiles storage
PROFILES_FILE = CONFIG_DIR / "profiles.json"


def load_profiles() -> dict:
    """Load saved browser profiles"""
    if PROFILES_FILE.exists():
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_profiles(profiles: dict):
    """Save browser profiles"""
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving profiles: {e}")
