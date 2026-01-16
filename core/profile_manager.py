# -*- coding: utf-8 -*-
"""
Profile Manager - Quản lý profiles browser và trạng thái đăng nhập
"""

import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from config.settings import PROFILES_DIR

logger = logging.getLogger(__name__)


class ProfileStatus(Enum):
    """Trạng thái của profile"""
    UNKNOWN = "unknown"           # Chưa kiểm tra
    LOGGED_IN = "logged_in"       # Đã đăng nhập
    NOT_LOGGED_IN = "not_logged_in"  # Chưa đăng nhập
    NEEDS_RELOGIN = "needs_relogin"  # Cần đăng nhập lại (bị khóa/logout)
    CHECKING = "checking"         # Đang kiểm tra


@dataclass
class ProfileInfo:
    """Thông tin về một profile"""
    name: str
    status: ProfileStatus = ProfileStatus.UNKNOWN
    last_checked: Optional[str] = None
    last_used: Optional[str] = None
    error_message: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "last_checked": self.last_checked,
            "last_used": self.last_used,
            "error_message": self.error_message
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'ProfileInfo':
        return ProfileInfo(
            name=data.get("name", ""),
            status=ProfileStatus(data.get("status", "unknown")),
            last_checked=data.get("last_checked"),
            last_used=data.get("last_used"),
            error_message=data.get("error_message", "")
        )


class ProfileManager:
    """Quản lý profiles browser"""
    
    STATUS_FILE = "profiles_status.json"
    
    def __init__(self):
        self.profiles: Dict[str, ProfileInfo] = {}
        self.status_file = os.path.join(PROFILES_DIR, self.STATUS_FILE)
        self._load_status()
        self._scan_profiles()
    
    def _load_status(self):
        """Load trạng thái từ file"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, info in data.items():
                        self.profiles[name] = ProfileInfo.from_dict(info)
                logger.info(f"Đã load {len(self.profiles)} profiles")
            except Exception as e:
                logger.error(f"Lỗi load status file: {e}")
    
    def _save_status(self):
        """Lưu trạng thái vào file"""
        try:
            os.makedirs(PROFILES_DIR, exist_ok=True)
            data = {name: info.to_dict() for name, info in self.profiles.items()}
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Lỗi save status file: {e}")
    
    def _scan_profiles(self):
        """Quét thư mục profiles"""
        if not os.path.exists(PROFILES_DIR):
            os.makedirs(PROFILES_DIR, exist_ok=True)
            return
        
        # Tìm các profile directories
        for item in os.listdir(PROFILES_DIR):
            if item == self.STATUS_FILE:
                continue
            
            profile_path = os.path.join(PROFILES_DIR, item)
            if os.path.isdir(profile_path):
                if item not in self.profiles:
                    # Profile mới, chưa có trong status
                    self.profiles[item] = ProfileInfo(name=item)
        
        # Xóa profiles không còn tồn tại
        existing = set(os.listdir(PROFILES_DIR)) - {self.STATUS_FILE}
        for name in list(self.profiles.keys()):
            if name not in existing:
                del self.profiles[name]
        
        self._save_status()
    
    def get_all_profiles(self) -> List[ProfileInfo]:
        """Lấy danh sách tất cả profiles"""
        self._scan_profiles()
        return list(self.profiles.values())
    
    def get_logged_in_profiles(self) -> List[ProfileInfo]:
        """Lấy danh sách profiles đã đăng nhập"""
        return [p for p in self.profiles.values() if p.status == ProfileStatus.LOGGED_IN]
    
    def get_available_profiles(self) -> List[ProfileInfo]:
        """Lấy danh sách profiles có thể chạy (logged in)"""
        return self.get_logged_in_profiles()
    
    def get_profile(self, name: str) -> Optional[ProfileInfo]:
        """Lấy thông tin profile theo tên"""
        return self.profiles.get(name)
    
    def set_status(self, name: str, status: ProfileStatus, error_message: str = ""):
        """Cập nhật trạng thái profile"""
        if name in self.profiles:
            self.profiles[name].status = status
            self.profiles[name].error_message = error_message
            self.profiles[name].last_checked = datetime.now().isoformat()
            self._save_status()
            logger.info(f"Profile {name}: {status.value}")
    
    def mark_as_logged_in(self, name: str):
        """Đánh dấu profile đã đăng nhập"""
        self.set_status(name, ProfileStatus.LOGGED_IN)
    
    def mark_as_not_logged_in(self, name: str):
        """Đánh dấu profile chưa đăng nhập"""
        self.set_status(name, ProfileStatus.NOT_LOGGED_IN)
    
    def mark_as_needs_relogin(self, name: str, reason: str = ""):
        """Đánh dấu profile cần đăng nhập lại"""
        self.set_status(name, ProfileStatus.NEEDS_RELOGIN, reason)
    
    def mark_as_used(self, name: str):
        """Đánh dấu profile vừa được sử dụng"""
        if name in self.profiles:
            self.profiles[name].last_used = datetime.now().isoformat()
            self._save_status()
    
    def create_profile(self, name: str) -> bool:
        """Tạo profile mới"""
        if name in self.profiles:
            return False
        
        profile_path = os.path.join(PROFILES_DIR, name)
        os.makedirs(profile_path, exist_ok=True)
        
        self.profiles[name] = ProfileInfo(
            name=name,
            status=ProfileStatus.NOT_LOGGED_IN
        )
        self._save_status()
        logger.info(f"Đã tạo profile: {name}")
        return True
    
    def delete_profile(self, name: str) -> bool:
        """Xóa profile"""
        import shutil
        
        if name not in self.profiles:
            return False
        
        profile_path = os.path.join(PROFILES_DIR, name)
        if os.path.exists(profile_path):
            try:
                shutil.rmtree(profile_path)
            except Exception as e:
                logger.error(f"Lỗi xóa profile {name}: {e}")
                return False
        
        del self.profiles[name]
        self._save_status()
        logger.info(f"Đã xóa profile: {name}")
        return True
    
    def get_status_icon(self, status: ProfileStatus) -> str:
        """Lấy icon cho trạng thái"""
        icons = {
            ProfileStatus.UNKNOWN: "❓",
            ProfileStatus.LOGGED_IN: "✅",
            ProfileStatus.NOT_LOGGED_IN: "❌",
            ProfileStatus.NEEDS_RELOGIN: "⚠️",
            ProfileStatus.CHECKING: "🔄"
        }
        return icons.get(status, "?")
    
    def get_status_text(self, status: ProfileStatus) -> str:
        """Lấy text cho trạng thái"""
        texts = {
            ProfileStatus.UNKNOWN: "Chưa kiểm tra",
            ProfileStatus.LOGGED_IN: "Đã đăng nhập",
            ProfileStatus.NOT_LOGGED_IN: "Chưa đăng nhập",
            ProfileStatus.NEEDS_RELOGIN: "Cần đăng nhập lại",
            ProfileStatus.CHECKING: "Đang kiểm tra..."
        }
        return texts.get(status, "Không rõ")
