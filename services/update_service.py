import os
import sys
import json
import requests
import subprocess
import threading
from pathlib import Path
from config.settings import VERSION, BASE_DIR, APP_EXEC_DIR

class UpdateService:
    UPDATE_URL = "https://raw.githubusercontent.com/theanhybdz2k4/tool-sora/main/update.json"  # Example URL
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.update_info = None

    def log(self, message):
        if self.log_callback:
            self.log_callback(f"[Update] {message}")
        else:
            print(f"[Update] {message}")

    def check_for_updates(self):
        """Checks if a new version is available"""
        try:
            self.log("Đang kiểm tra cập nhật...")
            response = requests.get(self.UPDATE_URL, timeout=10)
            if response.status_code == 200:
                self.update_info = response.json()
                latest_version = self.update_info.get("version")
                if latest_version and latest_version > VERSION:
                    self.log(f"Phát hiện bản cập nhật mới: {latest_version}")
                    return True
                else:
                    self.log("Bạn đang sử dụng bản mới nhất.")
            else:
                self.log(f"Không thể kiểm tra cập nhật (HTTP {response.status_code})")
        except Exception as e:
            self.log(f"Lỗi kiểm tra cập nhật: {e}")
        return False

    def download_and_prepare_update(self, progress_callback=None):
        """Downloads the update and prepares the updater script"""
        if not self.update_info:
            return False
            
        download_url = self.update_info.get("download_url")
        if not download_url:
            self.log("Lỗi: Không tìm thấy link tải bản cập nhật.")
            return False
            
        try:
            self.log(f"Đang tải bản cập nhật từ: {download_url}")
            # Download to a temporary location
            update_zip = BASE_DIR / "update_package.zip"
            
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(update_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded / total_size)
            
            self.log("Tải xuống hoàn tất. Đang chuẩn bị trình cập nhật...")
            self._create_updater_script(update_zip)
            return True
        except Exception as e:
            self.log(f"Lỗi tải cập nhật: {e}")
            return False

    def _create_updater_script(self, zip_path):
        """Creates a batch script to replace files and restart the app"""
        updater_path = BASE_DIR / "updater.bat"
        exe_path = sys.executable
        app_name = os.path.basename(exe_path)
        
        # Simple updater script: 
        # 1. Wait for app to close
        # 2. Extract ZIP (using PowerShell)
        # 3. Clean up
        # 4. Restart app
        
        script = f"""@echo off
echo Dang cap nhat Sora Automation Tool...
timeout /t 2 /nobreak > nul

:WAIT
tasklist | find /i "{app_name}" > nul
if %errorlevel% == 0 (
    echo Dang cho ung dung dong lai...
    timeout /t 1 /nobreak > nul
    goto WAIT
)

echo Dang giai nen ban cap nhat...
powershell -Command "Expand-Archive -Path '{zip_path}' -DestinationPath '{BASE_DIR}' -Force"

echo Dang xoa tep tam...
del "{zip_path}"

echo Cap nhat thanh cong! Dang khoi dong lai...
start "" "{exe_path}"
del "%~f0"
"""
        with open(updater_path, "w", encoding="cp437") as f:
            f.write(script)
        
        self.log(f"Trình cập nhật đã sẵn sàng: {updater_path}")

    def run_update(self):
        """Launches the updater script and exits the current process"""
        updater_path = BASE_DIR / "updater.bat"
        if updater_path.exists():
            self.log("Đang khởi động trình cập nhật...")
            subprocess.Popen([str(updater_path)], shell=True)
            sys.exit(0)
        else:
            self.log("Lỗi: Không tìm thấy trình cập nhật.")
            return False
