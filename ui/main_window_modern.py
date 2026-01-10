"""
Modern UI for Sora Automation Tool
Features: Dark theme, glassmorphism, smooth animations, premium design
"""
import customtkinter as ctk
from tkinter import messagebox, filedialog, scrolledtext
import threading
import queue
import os
import sys
from pathlib import Path
from typing import List, Dict, Callable
import tkinter as tk

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    load_settings, save_settings, load_profiles, save_profiles,
    DOWNLOADS_DIR, LOGS_DIR, CHROME_CACHE_DIR, BASE_DIR
)
from core.browser import BrowserCore
from core.thread_pool import ThreadPoolManager, Task, TaskStatus
from services.sheets_service import ExcelService, SheetRow, create_template_excel
from services.sora_service import SoraAutomationService, GenerationStatus

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ModernColors:
    """Modern color palette for the application"""
    # Backgrounds
    BG_PRIMARY = "#1a1d2e"
    BG_SECONDARY = "#16213e"
    BG_CARD = "#0f3460"
    
    # Accents
    ACCENT_PRIMARY = "#3282b8"
    ACCENT_SECONDARY = "#00d9ff"
    ACCENT_HOVER = "#4a9fd8"
    
    # Status colors
    SUCCESS = "#27ae60"
    WARNING = "#f39c12"
    ERROR = "#e74c3c"
    INFO = "#3498db"
    
    # Text
    TEXT_PRIMARY = "#ecf0f1"
    TEXT_SECONDARY = "#95a5a6"
    TEXT_MUTED = "#7f8c8d"
    
    # UI Elements
    BORDER = "#2c3e50"
    HOVER = "#34495e"


class ModernButton(ctk.CTkButton):
    """Custom button with hover effects"""
    def __init__(self, master, **kwargs):
        # Set default styling
        defaults = {
            "corner_radius": 8,
            "border_width": 0,
            "fg_color": ModernColors.ACCENT_PRIMARY,
            "hover_color": ModernColors.ACCENT_HOVER,
            "text_color": ModernColors.TEXT_PRIMARY,
            "font": ("Segoe UI", 12, "bold"),
            "height": 40,
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class ModernCard(ctk.CTkFrame):
    """Card-style container with glassmorphism effect"""
    def __init__(self, master, **kwargs):
        defaults = {
            "corner_radius": 12,
            "fg_color": ModernColors.BG_CARD,
            "border_width": 1,
            "border_color": ModernColors.BORDER,
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class SoraToolModernApp:
    """Modern Sora Tool Application with premium UI"""
    
    def __init__(self):
        # Create main window
        self.root = ctk.CTk()
        self.root.title("🎬 Sora Tool v2.0.0")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)
        
        # Configure grid weight
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # State
        self.settings = load_settings()
        self.profiles = load_profiles()
        self.tasks: List[SheetRow] = []
        self.is_running = False
        self.thread_pool: ThreadPoolManager = None
        self.browser_instances: Dict[int, BrowserCore] = {}
        self.sora_instances: Dict[int, SoraAutomationService] = {}
        
        # Message queue for thread-safe logging
        self.log_queue = queue.Queue()
        
        # Build UI
        self._build_ui()
        
        # Start log consumer
        self._process_log_queue()
        
    def _build_ui(self):
        """Build the modern UI"""
        # Main container with gradient background
        main_container = ctk.CTkFrame(self.root, fg_color=ModernColors.BG_PRIMARY)
        main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Header
        self._build_header(main_container)
        
        # Content area with tabs
        self._build_content(main_container)
        
    def _build_header(self, parent):
        """Build modern header with gradient"""
        header = ctk.CTkFrame(parent, height=80, fg_color=ModernColors.BG_SECONDARY, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(1, weight=1)
        
        # Logo and title
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="w", padx=30, pady=20)
        
        title = ctk.CTkLabel(
            title_frame,
            text="🎬 Sora Automation Tool",
            font=("Segoe UI", 28, "bold"),
            text_color=ModernColors.TEXT_PRIMARY
        )
        title.pack(side="left")
        
        version = ctk.CTkLabel(
            title_frame,
            text="v2.0.0",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        )
        version.pack(side="left", padx=10)
        
        # Status indicator
        self.status_indicator = ctk.CTkLabel(
            header,
            text="● Sẵn sàng",
            font=("Segoe UI", 14),
            text_color=ModernColors.SUCCESS
        )
        self.status_indicator.grid(row=0, column=1, sticky="e", padx=30)
        
    def _build_content(self, parent):
        """Build content area with modern tabs"""
        content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Create tabview
        self.tabview = ctk.CTkTabview(
            content_frame,
            fg_color=ModernColors.BG_SECONDARY,
            segmented_button_fg_color=ModernColors.BG_CARD,
            segmented_button_selected_color=ModernColors.ACCENT_PRIMARY,
            segmented_button_selected_hover_color=ModernColors.ACCENT_HOVER,
            segmented_button_unselected_color=ModernColors.BG_CARD,
            segmented_button_unselected_hover_color=ModernColors.HOVER,
            corner_radius=12,
        )
        self.tabview.grid(row=0, column=0, sticky="nsew")
        
        # Add tabs
        self.tab_control = self.tabview.add("🎮 Đăng nhập & Tài khoản")
        self.tab_execute = self.tabview.add("⚡ Execute Media Workflow")
        self.tab_tasks = self.tabview.add("📋 Tiến trình")
        self.tab_settings = self.tabview.add("⚙️ Cấu hình")
        self.tab_help = self.tabview.add("❓ Help")
        
        # Build tab contents
        self._build_control_tab()
        self._build_execute_tab()
        self._build_tasks_tab()
        self._build_settings_tab()
        self._build_help_tab()
        
    def _build_control_tab(self):
        """Build login & account tab"""
        tab = self.tab_control
        tab.grid_columnconfigure(0, weight=1)
        
        # Account Card
        account_card = ModernCard(tab)
        account_card.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        account_card.grid_columnconfigure(1, weight=1)
        
        # Card header
        header = ctk.CTkLabel(
            account_card,
            text="👤 Quản lý Tài khoản",
            font=("Segoe UI", 18, "bold"),
            text_color=ModernColors.TEXT_PRIMARY
        )
        header.grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 10))
        
        # Profile selection
        ctk.CTkLabel(
            account_card,
            text="Profile:",
            font=("Segoe UI", 14),
            text_color=ModernColors.TEXT_SECONDARY
        ).grid(row=1, column=0, sticky="w", padx=20, pady=10)
        
        self.profile_combo = ctk.CTkComboBox(
            account_card,
            width=300,
            height=40,
            font=("Segoe UI", 12),
            dropdown_font=("Segoe UI", 12),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
            button_color=ModernColors.ACCENT_PRIMARY,
            button_hover_color=ModernColors.ACCENT_HOVER,
        )
        self.profile_combo.grid(row=1, column=1, sticky="w", padx=10, pady=10)
        self._refresh_profiles()
        
        # Profile buttons
        btn_frame = ctk.CTkFrame(account_card, fg_color="transparent")
        btn_frame.grid(row=1, column=2, sticky="e", padx=20, pady=10)
        
        ModernButton(
            btn_frame,
            text="➕ Thêm",
            width=100,
            command=self._add_profile
        ).pack(side="left", padx=5)
        
        ModernButton(
            btn_frame,
            text="🗑️ Xóa",
            width=100,
            fg_color=ModernColors.ERROR,
            hover_color="#c0392b",
            command=self._remove_profile
        ).pack(side="left", padx=5)
        
        # Login button (prominent)
        login_btn = ModernButton(
            account_card,
            text="🔐 Đăng nhập Sora",
            height=50,
            font=("Segoe UI", 14, "bold"),
            fg_color=ModernColors.ACCENT_SECONDARY,
            hover_color="#00b8d4",
            command=self._open_browser_login
        )
        login_btn.grid(row=2, column=0, columnspan=3, sticky="ew", padx=20, pady=(10, 20))
        
    def _build_execute_tab(self):
        """Build execution workflow tab"""
        tab = self.tab_execute
        tab.grid_columnconfigure(0, weight=1)
        
        # Data Source Card
        data_card = ModernCard(tab)
        data_card.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        data_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            data_card,
            text="📊 Data Source",
            font=("Segoe UI", 18, "bold"),
            text_color=ModernColors.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(20, 10))
        
        # Source type
        self.source_type = tk.StringVar(value="excel")
        
        source_frame = ctk.CTkFrame(data_card, fg_color="transparent")
        source_frame.grid(row=1, column=0, columnspan=3, sticky="w", padx=20, pady=10)
        
        ctk.CTkRadioButton(
            source_frame,
            text="Excel File",
            variable=self.source_type,
            value="excel",
            font=("Segoe UI", 12),
            fg_color=ModernColors.ACCENT_PRIMARY,
            hover_color=ModernColors.ACCENT_HOVER,
        ).pack(side="left", padx=10)
        
        ctk.CTkRadioButton(
            source_frame,
            text="Google Sheets",
            variable=self.source_type,
            value="gsheet",
            font=("Segoe UI", 12),
            fg_color=ModernColors.ACCENT_PRIMARY,
            hover_color=ModernColors.ACCENT_HOVER,
        ).pack(side="left", padx=10)
        
        # File selection
        ctk.CTkLabel(
            data_card,
            text="Google Sheet URL:",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).grid(row=2, column=0, sticky="w", padx=20, pady=10)
        
        self.gsheet_url = tk.StringVar()
        ctk.CTkEntry(
            data_card,
            textvariable=self.gsheet_url,
            height=40,
            font=("Segoe UI", 12),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
        ).grid(row=2, column=1, sticky="ew", padx=10, pady=10)
        
        # Action buttons
        btn_row = ctk.CTkFrame(data_card, fg_color="transparent")
        btn_row.grid(row=2, column=2, sticky="e", padx=20, pady=10)
        
        ModernButton(
            btn_row,
            text="📂 Import từ Sheet",
            width=150,
            command=self._load_tasks
        ).pack(side="left", padx=5)
        
        ModernButton(
            btn_row,
            text="📥 Import Excel",
            width=150,
            fg_color=ModernColors.INFO,
            hover_color="#2980b9",
            command=self._browse_excel
        ).pack(side="left", padx=5)
        
        ModernButton(
            btn_row,
            text="📄 Tải Template",
            width=150,
            fg_color=ModernColors.WARNING,
            hover_color="#e67e22",
            command=self._download_template
        ).pack(side="left", padx=5)
        
        # Task count
        self.task_count_label = ctk.CTkLabel(
            data_card,
            text="Chưa có tasks",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        )
        self.task_count_label.grid(row=3, column=0, columnspan=3, sticky="w", padx=20, pady=(5, 20))
        
        # Settings Card
        settings_card = ModernCard(tab)
        settings_card.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        settings_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            settings_card,
            text="⚙️ Cấu hình",
            font=("Segoe UI", 18, "bold"),
            text_color=ModernColors.TEXT_PRIMARY
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=20, pady=(20, 10))
        
        # Settings row 1
        settings_row1 = ctk.CTkFrame(settings_card, fg_color="transparent")
        settings_row1.grid(row=1, column=0, columnspan=4, sticky="ew", padx=20, pady=10)
        
        # Type
        ctk.CTkLabel(
            settings_row1,
            text="Type:",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 10))
        
        self.type_var = tk.StringVar(value="Video")
        ctk.CTkComboBox(
            settings_row1,
            variable=self.type_var,
            values=["Video", "Image"],
            width=120,
            height=35,
            font=("Segoe UI", 11),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
        ).pack(side="left", padx=10)
        
        # Aspect Ratio
        ctk.CTkLabel(
            settings_row1,
            text="Aspect Ratio:",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(side="left", padx=(30, 10))
        
        self.aspect_var = tk.StringVar(value="9:16")
        ctk.CTkComboBox(
            settings_row1,
            variable=self.aspect_var,
            values=["9:16", "16:9", "1:1"],
            width=120,
            height=35,
            font=("Segoe UI", 11),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
        ).pack(side="left", padx=10)
        
        # Outputs
        ctk.CTkLabel(
            settings_row1,
            text="Outputs:",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(side="left", padx=(30, 10))
        
        self.outputs_var = tk.StringVar(value="1")
        ctk.CTkComboBox(
            settings_row1,
            variable=self.outputs_var,
            values=["1", "2", "3", "4"],
            width=80,
            height=35,
            font=("Segoe UI", 11),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
        ).pack(side="left", padx=10)
        
        # Resolution
        ctk.CTkLabel(
            settings_row1,
            text="Resolution:",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(side="left", padx=(30, 10))
        
        self.resolution_var = tk.StringVar(value="480p")
        ctk.CTkComboBox(
            settings_row1,
            variable=self.resolution_var,
            values=["480p", "720p", "1080p"],
            width=120,
            height=35,
            font=("Segoe UI", 11),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
        ).pack(side="left", padx=10)
        
        # Duration
        ctk.CTkLabel(
            settings_row1,
            text="Duration:",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(side="left", padx=(30, 10))
        
        self.duration_var = tk.StringVar(value="10s")
        ctk.CTkComboBox(
            settings_row1,
            variable=self.duration_var,
            values=["5s", "10s", "15s", "20s"],
            width=100,
            height=35,
            font=("Segoe UI", 11),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
        ).pack(side="left", padx=10)
        
        # Settings row 2
        settings_row2 = ctk.CTkFrame(settings_card, fg_color="transparent")
        settings_row2.grid(row=2, column=0, columnspan=4, sticky="ew", padx=20, pady=(5, 20))
        
        # Model
        ctk.CTkLabel(
            settings_row2,
            text="Model:",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 10))
        
        self.model_var = tk.StringVar(value="Sora (mặc định)")
        ctk.CTkComboBox(
            settings_row2,
            variable=self.model_var,
            values=["Sora (mặc định)", "Sora Turbo"],
            width=180,
            height=35,
            font=("Segoe UI", 11),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
        ).pack(side="left", padx=10)
        
        # Checkboxes
        self.headless_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            settings_row2,
            text="Headless (ẩn browser)",
            variable=self.headless_var,
            font=("Segoe UI", 11),
            fg_color=ModernColors.ACCENT_PRIMARY,
            hover_color=ModernColors.ACCENT_HOVER,
        ).pack(side="left", padx=30)
        
        self.multi_browser_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            settings_row2,
            text="Multi-browser mode",
            variable=self.multi_browser_var,
            font=("Segoe UI", 11),
            fg_color=ModernColors.ACCENT_PRIMARY,
            hover_color=ModernColors.ACCENT_HOVER,
        ).pack(side="left", padx=10)
        
        # Workers
        ctk.CTkLabel(
            settings_row2,
            text="Workers:",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(side="left", padx=(30, 10))
        
        self.workers_var = tk.IntVar(value=1)
        ctk.CTkEntry(
            settings_row2,
            textvariable=self.workers_var,
            width=80,
            height=35,
            font=("Segoe UI", 11),
            fg_color=ModernColors.BG_SECONDARY,
            border_color=ModernColors.BORDER,
        ).pack(side="left", padx=10)
        
        ctk.CTkLabel(
            settings_row2,
            text="(0 profiles)",
            font=("Segoe UI", 10),
            text_color=ModernColors.TEXT_MUTED
        ).pack(side="left", padx=5)
        
        # Control Buttons
        control_card = ModernCard(tab)
        control_card.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        control_card.grid_columnconfigure(0, weight=1)
        
        btn_container = ctk.CTkFrame(control_card, fg_color="transparent")
        btn_container.grid(row=0, column=0, pady=30)
        
        self.start_btn = ModernButton(
            btn_container,
            text="▶ START",
            width=200,
            height=60,
            font=("Segoe UI", 16, "bold"),
            fg_color=ModernColors.SUCCESS,
            hover_color="#229954",
            command=self._start_execution
        )
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ModernButton(
            btn_container,
            text="⏹ STOP",
            width=200,
            height=60,
            font=("Segoe UI", 16, "bold"),
            fg_color=ModernColors.ERROR,
            hover_color="#c0392b",
            command=self._stop_execution,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)
        
        # Status label
        self.exec_status_label = ctk.CTkLabel(
            control_card,
            text="✅ Sẵn sàng",
            font=("Segoe UI", 14),
            text_color=ModernColors.SUCCESS
        )
        self.exec_status_label.grid(row=1, column=0, pady=(0, 20))
        
    def _build_tasks_tab(self):
        """Build tasks progress tab"""
        tab = self.tab_tasks
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Header with stats
        stats_card = ModernCard(tab)
        stats_card.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        stats_card.grid_columnconfigure(0, weight=1)
        
        stats_container = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_container.grid(row=0, column=0, pady=20)
        
        # Stats boxes
        self.stats_widgets = {}
        stats_data = [
            ("Đang chạy", "0", ModernColors.INFO, "RUNNING"),
            ("Đang đợi", "0", ModernColors.WARNING, "QUEUE"),
            ("Hoàn thành", "0", ModernColors.SUCCESS, "pending"),
            ("Lỗi", "0", ModernColors.ERROR, "failed"),
        ]
        
        for i, (label, value, color, key) in enumerate(stats_data):
            stat_box = ctk.CTkFrame(
                stats_container,
                fg_color=color,
                corner_radius=10,
                width=150,
                height=100
            )
            stat_box.pack(side="left", padx=15)
            stat_box.pack_propagate(False)
            
            ctk.CTkLabel(
                stat_box,
                text=label,
                font=("Segoe UI", 12),
                text_color="white"
            ).pack(pady=(15, 5))
            
            value_label = ctk.CTkLabel(
                stat_box,
                text=value,
                font=("Segoe UI", 32, "bold"),
                text_color="white"
            )
            value_label.pack()
            self.stats_widgets[key] = value_label
        
        # Progress section
        progress_card = ModernCard(tab)
        progress_card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        progress_card.grid_columnconfigure(0, weight=1)
        progress_card.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            progress_card,
            text="📊 Chi tiết tiến trình",
            font=("Segoe UI", 16, "bold"),
            text_color=ModernColors.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        # Create text widget for logs (using tkinter for scrolled text)
        self.progress_text = scrolledtext.ScrolledText(
            progress_card,
            wrap="word",
            height=20,
            font=("Consolas", 10),
            bg=ModernColors.BG_SECONDARY,
            fg=ModernColors.TEXT_PRIMARY,
            insertbackground=ModernColors.TEXT_PRIMARY,
            relief="flat",
            borderwidth=0,
        )
        self.progress_text.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.progress_text.config(state="disabled")
        
    def _build_settings_tab(self):
        """Build settings tab"""
        tab = self.tab_settings
        tab.grid_columnconfigure(0, weight=1)
        
        settings_card = ModernCard(tab)
        settings_card.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(
            settings_card,
            text="⚙️ Cài đặt nâng cao",
            font=("Segoe UI", 18, "bold"),
            text_color=ModernColors.TEXT_PRIMARY
        ).pack(padx=20, pady=(20, 10), anchor="w")
        
        ctk.CTkLabel(
            settings_card,
            text="Các cài đặt sẽ được thêm vào phiên bản sau...",
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(padx=20, pady=20)
        
    def _build_help_tab(self):
        """Build help tab"""
        tab = self.tab_help
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        help_card = ModernCard(tab)
        help_card.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        help_card.grid_columnconfigure(0, weight=1)
        help_card.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            help_card,
            text="❓ Hướng dẫn sử dụng",
            font=("Segoe UI", 18, "bold"),
            text_color=ModernColors.TEXT_PRIMARY
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        help_text = """
🎬 HƯỚNG DẪN SỬ DỤNG SORA AUTOMATION TOOL

1. ĐĂNG NHẬP
   • Vào tab "Đăng nhập & Tài khoản"
   • Tạo profile mới hoặc chọn profile có sẵn
   • Click "Đăng nhập Sora" và đăng nhập thủ công

2. CHUẨN BỊ DỮ LIỆU
   • Tạo Google Sheet hoặc Excel với các cột: STT, PROMPT, IMAGE, SAVENAME, PATH
   • Hoặc tải template mẫu

3. THỰC THI
   • Vào tab "Execute Media Workflow"
   • Import dữ liệu từ Google Sheet hoặc Excel
   • Cấu hình các thông số (aspect ratio, duration, workers...)
   • Click START để bắt đầu

4. THEO DÕI
   • Vào tab "Tiến trình" để xem chi tiết
   • Theo dõi số lượng tasks đang chạy, hoàn thành, lỗi
        """
        
        help_display = scrolledtext.ScrolledText(
            help_card,
            wrap="word",
            font=("Segoe UI", 11),
            bg=ModernColors.BG_SECONDARY,
            fg=ModernColors.TEXT_PRIMARY,
            relief="flat",
            borderwidth=0,
        )
        help_display.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        help_display.insert("1.0", help_text)
        help_display.config(state="disabled")
        
    # ==================== Event Handlers ====================
    
    def _refresh_profiles(self):
        """Refresh profile combobox"""
        profiles = list(self.profiles.keys())
        if profiles:
            self.profile_combo.configure(values=profiles)
            self.profile_combo.set(profiles[0])
        else:
            self.profile_combo.configure(values=["Chưa có profile"])
            self.profile_combo.set("Chưa có profile")
            
    def _add_profile(self):
        """Add new profile"""
        dialog = ctk.CTkInputDialog(
            text="Nhập tên profile:",
            title="Thêm Profile Mới"
        )
        name = dialog.get_input()
        
        if name:
            self.profiles[name] = {
                "cache_dir": str(CHROME_CACHE_DIR / name.replace(" ", "_"))
            }
            save_profiles(self.profiles)
            self._refresh_profiles()
            self._log(f"👤 Đã thêm profile: {name}")
            messagebox.showinfo("Thành công", f"Đã thêm profile: {name}")
            
    def _remove_profile(self):
        """Remove selected profile"""
        name = self.profile_combo.get()
        if name and name != "Chưa có profile":
            if messagebox.askyesno("Xác nhận", f"Xóa profile '{name}'?"):
                del self.profiles[name]
                save_profiles(self.profiles)
                self._refresh_profiles()
                self._log(f"🗑️ Đã xóa profile: {name}")
                
    def _open_browser_login(self):
        """Open browser for manual login"""
        profile_name = self.profile_combo.get()
        if not profile_name or profile_name == "Chưa có profile":
            messagebox.showwarning("Cảnh báo", "Vui lòng tạo hoặc chọn profile")
            return
            
        profile = self.profiles.get(profile_name, {})
        cache_dir = profile.get("cache_dir", str(CHROME_CACHE_DIR / profile_name))
        
        def login_thread():
            try:
                browser = BrowserCore(cache_dir=cache_dir, log_callback=self._log)
                browser.build_driver()
                browser.navigate(SoraAutomationService.BASE_URL)
                self._log(f"🔐 Đã mở browser. Vui lòng đăng nhập thủ công.")
                
                sora = SoraAutomationService(browser, log_callback=self._log)
                if sora.wait_for_manual_login(timeout=300):
                    self._log("✅ Đăng nhập thành công!")
                    messagebox.showinfo("Thành công", "Đăng nhập thành công! Profile đã được lưu.")
                else:
                    self._log("⚠️ Timeout khi đợi đăng nhập")
                    
            except Exception as e:
                self._log(f"❌ Lỗi đăng nhập: {e}")
                
        threading.Thread(target=login_thread, daemon=True).start()
        
    def _browse_excel(self):
        """Browse for Excel file"""
        filepath = filedialog.askopenfilename(
            title="Chọn file Excel",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if filepath:
            self._load_excel(filepath)
            
    def _load_excel(self, filepath):
        """Load tasks from Excel"""
        try:
            # Get output_dir and image_dir from settings
            output_dir = self.settings.get("output_folder", str(DOWNLOADS_DIR))
            image_dir = self.settings.get("image_folder", str(BASE_DIR / "Image"))
            
            service = ExcelService(
                log_callback=self._log,
                image_dir=image_dir,
                output_dir=output_dir
            )
            if service.load(filepath):
                self.tasks = service.read_worksheet(skip_completed=True)
                self.task_count_label.configure(
                    text=f"✅ Đã load {len(self.tasks)} tasks",
                    text_color=ModernColors.SUCCESS
                )
                self._log(f"📂 Đã load {len(self.tasks)} tasks từ Excel")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể load file: {e}")
            self._log(f"❌ Lỗi load Excel: {e}")
            
    def _download_template(self):
        """Download Excel template"""
        # Lưu vào thư mục Downloads hoặc thư mục hiện tại
        import os
        from pathlib import Path
        
        # Lấy thư mục Downloads
        downloads_dir = Path.home() / "Downloads"
        if not downloads_dir.exists():
            downloads_dir = Path.cwd()  # Fallback về thư mục hiện tại
        
        filepath = filedialog.asksaveasfilename(
            title="Lưu Template",
            defaultextension=".xlsx",
            initialdir=str(downloads_dir),  # Mở ở thư mục Downloads
            initialname="sora_template.xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if filepath:
            create_template_excel(filepath)
            messagebox.showinfo("Thành công", f"Đã lưu template:\n{filepath}")
            self._log(f"📥 Đã tải template: {filepath}")
            
    def _load_tasks(self):
        """Load tasks from Google Sheets"""
        messagebox.showinfo("Thông báo", "Chức năng Google Sheets đang được phát triển")
        
    def _start_execution(self):
        """Start task execution"""
        if not self.tasks:
            messagebox.showwarning("Cảnh báo", "Chưa có tasks để thực thi")
            return
            
        profile_name = self.profile_combo.get()
        if not profile_name or profile_name == "Chưa có profile":
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn profile")
            return
            
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_indicator.configure(text="● Đang chạy", text_color=ModernColors.INFO)
        self.exec_status_label.configure(text="⚡ Đang thực thi...", text_color=ModernColors.INFO)
        
        self._log(f"🚀 Bắt đầu thực thi với {len(self.tasks)} tasks")
        
        # TODO: Implement actual execution logic
        
    def _stop_execution(self):
        """Stop execution"""
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_indicator.configure(text="● Đã dừng", text_color=ModernColors.WARNING)
        self.exec_status_label.configure(text="⏹ Đã dừng", text_color=ModernColors.WARNING)
        
        self._log("⏹️ Đã dừng thực thi")
        
    # ==================== Logging ====================
    
    def _log(self, message: str):
        """Thread-safe logging"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")
        
    def _process_log_queue(self):
        """Process log messages from queue"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.progress_text.config(state="normal")
                self.progress_text.insert("end", message + "\n")
                self.progress_text.see("end")
                self.progress_text.config(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_log_queue)
            
    def run(self):
        """Start the application"""
        self._log("🎬 Sora Automation Tool v2.0.0 đã khởi động")
        self.root.mainloop()


def main():
    """Entry point"""
    app = SoraToolModernApp()
    app.run()


if __name__ == "__main__":
    main()
