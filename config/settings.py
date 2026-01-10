"""
Application settings and configuration
"""
import os
import json
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
DOWNLOADS_DIR = BASE_DIR / "downloads"
LOGS_DIR = BASE_DIR / "logs"
CHROME_CACHE_DIR = BASE_DIR / "chrome_cache"

# Create directories if not exist
for dir_path in [DOWNLOADS_DIR, LOGS_DIR, CHROME_CACHE_DIR]:
    dir_path.mkdir(exist_ok=True)

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
