"""
Main Application Window for Sora Automation Tool
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import threading
import queue
import os
import sys
from pathlib import Path
from typing import List, Dict, Callable

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try modern theming
try:
    from ttkbootstrap import Style as TtkbStyle
    from ttkbootstrap import Window as TtkbWindow
    HAS_TTKBOOTSTRAP = True
except ImportError:
    TtkbStyle = None
    TtkbWindow = None
    HAS_TTKBOOTSTRAP = False

from config.settings import (
    load_settings, save_settings, load_profiles, save_profiles,
    DOWNLOADS_DIR, LOGS_DIR, CHROME_CACHE_DIR, BASE_DIR
)
from core.browser import BrowserCore
from core.thread_pool import ThreadPoolManager, Task, TaskStatus
from services.sheets_service import ExcelService, SheetRow, create_template_excel
from services.sora_service import SoraAutomationService


class SoraToolApp:
    """Main application window"""
    
    def __init__(self):
        # Create window
        if HAS_TTKBOOTSTRAP:
            self.root = TtkbWindow(themename="darkly")
        else:
            self.root = tk.Tk()
            
        self.root.title("🎬 Sora Automation Tool")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # State
        self.settings = load_settings()
        self.profiles = load_profiles()
        self.tasks: List[SheetRow] = []
        self.is_running = False
        self.thread_pool: ThreadPoolManager = None
        self.browser_instances: Dict[int, BrowserCore] = {}
        self.sora_instances: Dict[int, SoraAutomationService] = {}
        self.profile_assignments: Dict[int, str] = {}  # thread_id -> profile_name
        
        # Message queue for thread-safe logging
        self.log_queue = queue.Queue()
        
        # Build UI
        self._apply_theme()
        self._build_ui()
        
        # Update thread limit after UI is built
        self._update_thread_limit()
        
        # Start log consumer
        self._process_log_queue()
        
    def _apply_theme(self):
        """Apply visual theme"""
        if not HAS_TTKBOOTSTRAP:
            style = ttk.Style()
            try:
                style.theme_use("clam")
            except:
                pass
                
    def _build_ui(self):
        """Build the main UI"""
        # Main container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: Main Control
        self._build_control_tab()
        
        # Tab 2: Tasks/Queue
        self._build_tasks_tab()
        
        # Tab 3: Settings
        self._build_settings_tab()
        
        # Tab 4: Logs
        self._build_log_tab()
        
        # Tab 5: Help
        self._build_help_tab()
        
    def _build_control_tab(self):
        """Build main control tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="🎮 Control Panel")
        
        # === Data Source Frame ===
        source_frame = ttk.LabelFrame(tab, text="📊 Data Source", padding=10)
        source_frame.pack(fill="x", pady=(0, 10))
        
        # Source type selection
        source_row = ttk.Frame(source_frame)
        source_row.pack(fill="x", pady=5)
        
        self.source_type = tk.StringVar(value="excel")
        ttk.Radiobutton(source_row, text="Excel File", variable=self.source_type, 
                        value="excel", command=self._on_source_change).pack(side="left", padx=5)
        ttk.Radiobutton(source_row, text="Google Sheets", variable=self.source_type,
                        value="gsheet", command=self._on_source_change).pack(side="left", padx=5)
        
        # Excel file selection
        self.excel_frame = ttk.Frame(source_frame)
        self.excel_frame.pack(fill="x", pady=5)
        
        ttk.Label(self.excel_frame, text="File:").pack(side="left")
        self.excel_path = tk.StringVar()
        ttk.Entry(self.excel_frame, textvariable=self.excel_path, width=50).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(self.excel_frame, text="Browse...", command=self._browse_excel).pack(side="left", padx=5)
        ttk.Button(self.excel_frame, text="📥 Template", command=self._download_template).pack(side="left")
        
        # Google Sheets (hidden by default)
        self.gsheet_frame = ttk.Frame(source_frame)
        
        ttk.Label(self.gsheet_frame, text="Sheet URL:").pack(side="left")
        self.gsheet_url = tk.StringVar()
        ttk.Entry(self.gsheet_frame, textvariable=self.gsheet_url, width=60).pack(side="left", padx=5, fill="x", expand=True)
        
        # Load button
        load_row = ttk.Frame(source_frame)
        load_row.pack(fill="x", pady=10)
        ttk.Button(load_row, text="📂 Load Tasks", command=self._load_tasks).pack(side="left", padx=5)
        self.task_count_label = ttk.Label(load_row, text="No tasks loaded")
        self.task_count_label.pack(side="left", padx=10)
        
        # === Account Frame ===
        account_frame = ttk.LabelFrame(tab, text="👤 Account", padding=10)
        account_frame.pack(fill="x", pady=(0, 10))
        
        account_row = ttk.Frame(account_frame)
        account_row.pack(fill="x", pady=5)
        
        ttk.Label(account_row, text="Profile:").pack(side="left")
        self.profile_combo = ttk.Combobox(account_row, width=30, state="readonly")
        self.profile_combo.pack(side="left", padx=5)
        # Don't call _refresh_profiles here, will be called after thread_info_label is created
        
        ttk.Button(account_row, text="➕ Add", command=self._add_profile).pack(side="left", padx=5)
        ttk.Button(account_row, text="🗑️ Remove", command=self._remove_profile).pack(side="left")
        ttk.Button(account_row, text="🔐 Login", command=self._open_browser_login).pack(side="left", padx=20)
        
        # === Execution Frame ===
        exec_frame = ttk.LabelFrame(tab, text="⚡ Execution", padding=10)
        exec_frame.pack(fill="x", pady=(0, 10))
        
        # Thread settings
        thread_row = ttk.Frame(exec_frame)
        thread_row.pack(fill="x", pady=5)
        
        ttk.Label(thread_row, text="Threads:").pack(side="left")
        self.thread_count = tk.IntVar(value=self.settings.get("max_threads", 1))
        self.thread_spinbox = ttk.Spinbox(thread_row, from_=1, to=10, width=5, 
                                          textvariable=self.thread_count,
                                          command=self._update_thread_limit)
        self.thread_spinbox.pack(side="left", padx=5)
        
        # Label hiển thị số profile và giới hạn
        self.thread_info_label = ttk.Label(thread_row, text="(Max: 1 profile)", foreground="gray")
        self.thread_info_label.pack(side="left", padx=5)
        
        # Now refresh profiles and update thread limit
        self._refresh_profiles()
        
        ttk.Label(thread_row, text="Delay (s):").pack(side="left", padx=(20, 0))
        self.delay_seconds = tk.DoubleVar(value=self.settings.get("thread_delay_seconds", 2))
        ttk.Spinbox(thread_row, from_=0, to=30, width=5, 
                   textvariable=self.delay_seconds).pack(side="left", padx=5)
        
        self.headless_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(thread_row, text="Headless Mode", 
                       variable=self.headless_var).pack(side="left", padx=20)
        
        # Control buttons
        btn_row = ttk.Frame(exec_frame)
        btn_row.pack(fill="x", pady=10)
        
        self.start_btn = ttk.Button(btn_row, text="▶️ START", command=self._start_execution)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(btn_row, text="⏹️ STOP", command=self._stop_execution, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        self.pause_btn = ttk.Button(btn_row, text="⏸️ PAUSE", command=self._pause_execution, state="disabled")
        self.pause_btn.pack(side="left", padx=5)
        
        # Progress
        progress_frame = ttk.Frame(exec_frame)
        progress_frame.pack(fill="x", pady=10)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack()
        
        # Stats
        stats_row = ttk.Frame(exec_frame)
        stats_row.pack(fill="x", pady=5)
        
        self.stats_labels = {}
        for stat in ["Pending", "Running", "Completed", "Failed"]:
            frame = ttk.Frame(stats_row)
            frame.pack(side="left", padx=10)
            ttk.Label(frame, text=f"{stat}:").pack(side="left")
            label = ttk.Label(frame, text="0", font=("Arial", 12, "bold"))
            label.pack(side="left", padx=3)
            self.stats_labels[stat.lower()] = label
            
    def _build_tasks_tab(self):
        """Build tasks/queue tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="📋 Tasks Queue")
        
        # Toolbar
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self._refresh_tasks_view).pack(side="left", padx=5)
        ttk.Button(toolbar, text="✅ Select All", command=self._select_all_tasks).pack(side="left", padx=5)
        ttk.Button(toolbar, text="❌ Clear Selection", command=self._clear_selection).pack(side="left", padx=5)
        
        # Tasks treeview
        columns = ("stt", "prompt", "status", "aspect", "duration", "output")
        self.tasks_tree = ttk.Treeview(tab, columns=columns, show="headings", height=20)
        
        self.tasks_tree.heading("stt", text="#")
        self.tasks_tree.heading("prompt", text="Prompt")
        self.tasks_tree.heading("status", text="Status")
        self.tasks_tree.heading("aspect", text="Aspect")
        self.tasks_tree.heading("duration", text="Duration")
        self.tasks_tree.heading("output", text="Output Path")
        
        self.tasks_tree.column("stt", width=50)
        self.tasks_tree.column("prompt", width=400)
        self.tasks_tree.column("status", width=100)
        self.tasks_tree.column("aspect", width=80)
        self.tasks_tree.column("duration", width=80)
        self.tasks_tree.column("output", width=200)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=scrollbar.set)
        
        self.tasks_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def _build_settings_tab(self):
        """Build settings tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="⚙️ Settings")
        
        # Default settings
        defaults_frame = ttk.LabelFrame(tab, text="Default Values", padding=10)
        defaults_frame.pack(fill="x", pady=10)
        
        row1 = ttk.Frame(defaults_frame)
        row1.pack(fill="x", pady=5)
        
        ttk.Label(row1, text="Default Aspect Ratio:").pack(side="left")
        self.default_aspect = tk.StringVar(value=self.settings.get("default_aspect_ratio", "16:9"))
        aspect_combo = ttk.Combobox(row1, textvariable=self.default_aspect, width=10,
                                   values=["16:9", "3:2", "1:1", "2:3", "9:16"])
        aspect_combo.pack(side="left", padx=10)
        
        ttk.Label(row1, text="Default Duration:").pack(side="left", padx=(30, 0))
        self.default_duration = tk.StringVar(value=self.settings.get("default_duration", "10s"))
        duration_combo = ttk.Combobox(row1, textvariable=self.default_duration, width=10,
                                     values=["5s", "10s", "15s", "20s"])
        duration_combo.pack(side="left", padx=10)
        
        # Row 2: Resolution and Variations
        row1b = ttk.Frame(defaults_frame)
        row1b.pack(fill="x", pady=5)
        
        ttk.Label(row1b, text="Default Resolution:").pack(side="left")
        self.default_resolution = tk.StringVar(value=self.settings.get("default_resolution", "480p"))
        resolution_combo = ttk.Combobox(row1b, textvariable=self.default_resolution, width=10,
                                        values=["1080p", "720p", "480p"])
        resolution_combo.pack(side="left", padx=10)
        
        ttk.Label(row1b, text="Default Variations:").pack(side="left", padx=(30, 0))
        self.default_variations = tk.StringVar(value=self.settings.get("default_variations", "1"))
        variations_combo = ttk.Combobox(row1b, textvariable=self.default_variations, width=10,
                                        values=["1", "2", "4"])
        variations_combo.pack(side="left", padx=10)
        
        # Folder settings (Image and Output folders)
        folder_frame = ttk.LabelFrame(tab, text="📁 Thư mục", padding=10)
        folder_frame.pack(fill="x", pady=10)
        
        # Image folder
        img_row = ttk.Frame(folder_frame)
        img_row.pack(fill="x", pady=5)
        
        ttk.Label(img_row, text="Image Folder:").pack(side="left")
        default_image_dir = str(BASE_DIR / "Image")
        self.image_folder = tk.StringVar(value=self.settings.get("image_folder", default_image_dir))
        ttk.Entry(img_row, textvariable=self.image_folder, width=50).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(img_row, text="Browse...", command=self._browse_image_folder).pack(side="left", padx=5)
        
        # Output folder
        out_row = ttk.Frame(folder_frame)
        out_row.pack(fill="x", pady=5)
        
        ttk.Label(out_row, text="Output Folder:").pack(side="left")
        default_output_dir = str(DOWNLOADS_DIR)
        self.output_folder = tk.StringVar(value=self.settings.get("output_folder", default_output_dir))
        ttk.Entry(out_row, textvariable=self.output_folder, width=50).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(out_row, text="Browse...", command=self._browse_output_folder).pack(side="left", padx=5)
        
        # Timeout settings
        timeout_frame = ttk.LabelFrame(tab, text="Timeouts", padding=10)
        timeout_frame.pack(fill="x", pady=10)
        
        row2 = ttk.Frame(timeout_frame)
        row2.pack(fill="x", pady=5)
        
        ttk.Label(row2, text="Wait Timeout (s):").pack(side="left")
        self.wait_timeout = tk.IntVar(value=self.settings.get("wait_timeout_seconds", 300))
        ttk.Spinbox(row2, from_=60, to=600, width=8, textvariable=self.wait_timeout).pack(side="left", padx=10)
        
        ttk.Label(row2, text="Check Interval (s):").pack(side="left", padx=(30, 0))
        self.check_interval = tk.IntVar(value=self.settings.get("check_interval_seconds", 10))
        ttk.Spinbox(row2, from_=5, to=60, width=8, textvariable=self.check_interval).pack(side="left", padx=10)
        
        # Download settings
        dl_frame = ttk.LabelFrame(tab, text="Downloads", padding=10)
        dl_frame.pack(fill="x", pady=10)
        
        row3 = ttk.Frame(dl_frame)
        row3.pack(fill="x", pady=5)
        
        self.auto_download = tk.BooleanVar(value=self.settings.get("auto_download", True))
        ttk.Checkbutton(row3, text="Auto Download Results", variable=self.auto_download).pack(side="left")
        
        ttk.Label(row3, text="Default Format:").pack(side="left", padx=(30, 0))
        self.download_format = tk.StringVar(value=self.settings.get("download_format", "mp4"))
        ttk.Combobox(row3, textvariable=self.download_format, width=8,
                    values=["mp4", "webm", "gif"]).pack(side="left", padx=10)
        
        # Save button
        ttk.Button(tab, text="💾 Save Settings", command=self._save_settings).pack(pady=20)
        
    def _build_log_tab(self):
        """Build log tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="📜 Logs")
        
        # Toolbar
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(toolbar, text="🗑️ Clear Logs", command=self._clear_logs).pack(side="left", padx=5)
        ttk.Button(toolbar, text="💾 Save Logs", command=self._save_logs).pack(side="left", padx=5)
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Auto Scroll", variable=self.auto_scroll_var).pack(side="right")
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(tab, wrap="word", height=30, font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state="disabled")
        
    def _build_help_tab(self):
        """Build help tab"""
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="❓ Help")
        
        help_text = """
🎬 SORA AUTOMATION TOOL - HƯỚNG DẪN SỬ DỤNG

═══════════════════════════════════════════════════════════════

📋 BƯỚC 1: CHUẨN BỊ DỮ LIỆU
   • Tạo file Excel hoặc Google Sheet với các cột sau:
     - STT: Số thứ tự
     - PROMPT: Nội dung prompt cho AI
     - IMAGE: Đường dẫn ảnh tham chiếu (tùy chọn)
     - SAVENAME: Tên file lưu
     - PATH: Thư mục lưu output
     - ASPECT_RATIO: Tỷ lệ khung hình (16:9, 9:16, 1:1...)
     - DURATION: Thời lượng video (5s, 10s, 20s...)
     - STATUS: Trạng thái (tool sẽ tự cập nhật)

   • Nhấn "📥 Template" để tải file Excel mẫu

═══════════════════════════════════════════════════════════════

👤 BƯỚC 2: ĐĂNG NHẬP TÀI KHOẢN
   • Thêm profile mới bằng nút "➕ Add"
   • Chọn profile và nhấn "🔐 Login"
   • Đăng nhập thủ công vào tài khoản Sora
   • Profile sẽ được lưu lại cho lần sau

═══════════════════════════════════════════════════════════════

⚡ BƯỚC 3: CHẠY TỰ ĐỘNG
   • Load file Excel/Google Sheet
   • Chọn số lượng threads (1-10)
   • Nhấn "▶️ START" để bắt đầu
   • Theo dõi tiến độ và logs

═══════════════════════════════════════════════════════════════

⚙️ CÀI ĐẶT
   • Threads: Số lượng browser chạy song song
   • Delay: Thời gian chờ giữa các task
   • Headless: Chạy ẩn browser (không hiển thị)
   • Auto Download: Tự động tải kết quả

═══════════════════════════════════════════════════════════════

📞 HỖ TRỢ
   • Email: support@example.com
   • Website: https://example.com
        """
        
        text = scrolledtext.ScrolledText(tab, wrap="word", font=("Arial", 11))
        text.pack(fill="both", expand=True)
        text.insert("1.0", help_text)
        text.config(state="disabled")
        
    # ==================== Event Handlers ====================
    
    def _on_source_change(self):
        """Handle source type change"""
        if self.source_type.get() == "excel":
            self.gsheet_frame.pack_forget()
            self.excel_frame.pack(fill="x", pady=5)
        else:
            self.excel_frame.pack_forget()
            self.gsheet_frame.pack(fill="x", pady=5)
            
    def _browse_excel(self):
        """Browse for Excel file"""
        filepath = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if filepath:
            self.excel_path.set(filepath)
    
    def _browse_image_folder(self):
        """Browse for Image folder"""
        folder = filedialog.askdirectory(
            title="Select Image Folder",
            initialdir=self.image_folder.get() if self.image_folder.get() else str(BASE_DIR)
        )
        if folder:
            self.image_folder.set(folder)
            self._log(f"📁 Image folder: {folder}")
    
    def _browse_output_folder(self):
        """Browse for Output folder"""
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.output_folder.get() if self.output_folder.get() else str(DOWNLOADS_DIR)
        )
        if folder:
            self.output_folder.set(folder)
            self._log(f"📁 Output folder: {folder}")
            
    def _download_template(self):
        """Download Excel template"""
        filepath = filedialog.asksaveasfilename(
            title="Save Template",
            defaultextension=".xlsx",
            initialname="sora_prompts_template.xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if filepath:
            create_template_excel(filepath)
            messagebox.showinfo("Success", f"Template saved: {filepath}")
            
    def _load_tasks(self):
        """Load tasks from data source"""
        self.tasks = []
        
        try:
            if self.source_type.get() == "excel":
                filepath = self.excel_path.get()
                if not filepath:
                    messagebox.showwarning("Warning", "Please select an Excel file")
                    return
                    
                # Use Image and Output folders from settings
                image_dir = self.image_folder.get() if hasattr(self, 'image_folder') else str(BASE_DIR / "Image")
                output_dir = self.output_folder.get() if hasattr(self, 'output_folder') else str(DOWNLOADS_DIR)
                
                service = ExcelService(
                    log_callback=self._log,
                    image_dir=image_dir,
                    output_dir=output_dir
                )
                if service.load(filepath):
                    self.tasks = service.read_worksheet(skip_completed=True)
                    
            else:
                # Google Sheets - not implemented for demo
                messagebox.showinfo("Info", "Google Sheets integration requires setup")
                return
                
            # Update UI
            self.task_count_label.config(text=f"✅ {len(self.tasks)} tasks loaded")
            self._refresh_tasks_view()
            self._log(f"📂 Loaded {len(self.tasks)} tasks")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")
            self._log(f"❌ Load error: {e}")
            
    def _refresh_tasks_view(self):
        """Refresh tasks treeview"""
        # Clear existing
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)
            
        # Add tasks
        for task in self.tasks:
            self.tasks_tree.insert("", "end", values=(
                task.stt,
                task.prompt[:60] + "..." if len(task.prompt) > 60 else task.prompt,
                task.status or "Pending",
                task.aspect_ratio,
                task.duration,
                task.output_path[:30] + "..." if len(task.output_path) > 30 else task.output_path
            ))
            
    def _select_all_tasks(self):
        """Select all tasks in treeview"""
        for item in self.tasks_tree.get_children():
            self.tasks_tree.selection_add(item)
            
    def _clear_selection(self):
        """Clear task selection"""
        self.tasks_tree.selection_remove(*self.tasks_tree.selection())
        
    def _refresh_profiles(self):
        """Refresh profile combobox"""
        self.profiles = load_profiles()  # Reload from file
        profile_list = list(self.profiles.keys())
        self.profile_combo["values"] = profile_list
        if profile_list:
            self.profile_combo.current(0)
        # Update thread limit based on number of profiles
        self._update_thread_limit()
            
    def _add_profile(self):
        """Add new profile"""
        name = tk.simpledialog.askstring("New Profile", "Enter profile name:")
        if name:
            self.profiles[name] = {
                "cache_dir": str(CHROME_CACHE_DIR / name.replace(" ", "_"))
            }
            save_profiles(self.profiles)
            self._refresh_profiles()
            self._log(f"👤 Profile added: {name}")
    
    def _update_thread_limit(self):
        """Update thread count limit based on available profiles"""
        # Check if thread_info_label exists (may not exist during initialization)
        if not hasattr(self, 'thread_info_label') or self.thread_info_label is None:
            return
        
        num_profiles = len(self.profiles)
        if num_profiles == 0:
            max_threads = 1
            self.thread_info_label.config(text="(Cần ít nhất 1 profile)", foreground="orange")
        else:
            max_threads = num_profiles
            self.thread_info_label.config(text=f"(Max: {max_threads} profiles)", foreground="gray")
        
        # Update spinbox max value
        current_value = self.thread_count.get()
        if current_value > max_threads:
            self.thread_count.set(max_threads)
        
        # Update spinbox to value (check if exists)
        if hasattr(self, 'thread_spinbox') and self.thread_spinbox is not None:
            self.thread_spinbox.config(to=max_threads)
            
    def _remove_profile(self):
        """Remove selected profile"""
        name = self.profile_combo.get()
        if name and messagebox.askyesno("Confirm", f"Remove profile '{name}'?"):
            del self.profiles[name]
            save_profiles(self.profiles)
            self._refresh_profiles()
            self._log(f"🗑️ Profile removed: {name}")
            # Update thread count if it exceeds available profiles
            if self.thread_count.get() > len(self.profiles):
                self.thread_count.set(len(self.profiles) if self.profiles else 1)
            
    def _open_browser_login(self):
        """Open browser for manual login"""
        profile_name = self.profile_combo.get()
        if not profile_name:
            messagebox.showwarning("Warning", "Please select or create a profile")
            return
            
        profile = self.profiles.get(profile_name, {})
        cache_dir = profile.get("cache_dir", str(CHROME_CACHE_DIR / profile_name))
        
        def login_thread():
            try:
                browser = BrowserCore(cache_dir=cache_dir, log_callback=self._log)
                browser.build_driver()
                browser.navigate(SoraAutomationService.BASE_URL)
                self._log(f"🔐 Browser opened for login. Please login manually.")
                
                # Wait for user to login
                sora = SoraAutomationService(browser, log_callback=self._log)
                if sora.wait_for_manual_login(timeout=300):
                    self._log("✅ Login successful! You can close the browser.")
                    messagebox.showinfo("Success", "Login successful! Profile saved.")
                else:
                    self._log("⚠️ Login timeout")
                    
            except Exception as e:
                self._log(f"❌ Login error: {e}")
                
        threading.Thread(target=login_thread, daemon=True).start()
        
    def _save_settings(self):
        """Save current settings"""
        self.settings.update({
            "max_threads": self.thread_count.get(),
            "thread_delay_seconds": self.delay_seconds.get(),
            "default_aspect_ratio": self.default_aspect.get(),
            "default_duration": self.default_duration.get(),
            "default_resolution": self.default_resolution.get(),
            "default_variations": self.default_variations.get(),
            "wait_timeout_seconds": self.wait_timeout.get(),
            "check_interval_seconds": self.check_interval.get(),
            "auto_download": self.auto_download.get(),
            "download_format": self.download_format.get(),
            "image_folder": self.image_folder.get(),
            "output_folder": self.output_folder.get(),
        })
        save_settings(self.settings)
        messagebox.showinfo("Success", "Settings saved!")
        self._log("💾 Settings saved")
        
    def _clear_logs(self):
        """Clear log text"""
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        
    def _save_logs(self):
        """Save logs to file"""
        filepath = filedialog.asksaveasfilename(
            title="Save Logs",
            defaultextension=".txt",
            initialname=f"sora_logs_{int(__import__('time').time())}.txt"
        )
        if filepath:
            self.log_text.config(state="normal")
            content = self.log_text.get("1.0", "end")
            self.log_text.config(state="disabled")
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Success", f"Logs saved: {filepath}")
            
    # ==================== Execution Methods ====================
    
    def _start_execution(self):
        """Start task execution"""
        if not self.tasks:
            messagebox.showwarning("Warning", "No tasks loaded")
            return
        
        # Validate profiles
        if not self.profiles:
            messagebox.showwarning("Warning", "Please add at least one profile")
            return
        
        # Get available profiles
        available_profiles = list(self.profiles.keys())
        num_profiles = len(available_profiles)
        
        # Limit threads to number of profiles
        requested_threads = self.thread_count.get()
        actual_threads = min(requested_threads, num_profiles)
        
        if requested_threads > num_profiles:
            messagebox.showwarning(
                "Thread Limit", 
                f"Chỉ có {num_profiles} profile, giới hạn threads = {num_profiles}\n"
                f"(Bạn đã chọn {requested_threads} threads)"
            )
            self.thread_count.set(actual_threads)
        
        if actual_threads == 0:
            messagebox.showwarning("Warning", "Không có profile để chạy")
            return
            
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.pause_btn.config(state="normal")
        
        # Store profile assignment for threads
        self.profile_assignments = {}
        for i in range(actual_threads):
            # Round-robin assignment: thread 1 -> profile 0, thread 2 -> profile 1, etc.
            profile_idx = i % num_profiles
            self.profile_assignments[i + 1] = available_profiles[profile_idx]
        
        # Initialize thread pool
        self.thread_pool = ThreadPoolManager(
            max_workers=actual_threads,
            task_handler=self._process_task,
            on_task_complete=self._on_task_complete,
            on_task_error=self._on_task_error,
            on_log=self._log,
            delay_between_tasks=self.delay_seconds.get()
        )
        
        # Add tasks to queue
        for row in self.tasks:
            self.thread_pool.add_task(row.to_dict())
            
        # Start execution
        self.thread_pool.start()
        self._log(f"🚀 Started execution with {actual_threads} threads")
        self._log(f"📋 Profile assignment: {self.profile_assignments}")
        
        # Update UI periodically
        self._update_progress()
        
    def _process_task(self, task: Task, thread_id: int):
        """Process a single task (called in worker thread)"""
        data = task.data
        
        # Get or create browser for this thread
        if thread_id not in self.browser_instances:
            # Get assigned profile for this thread
            profile_name = self.profile_assignments.get(thread_id)
            if not profile_name:
                raise ValueError(f"No profile assigned for thread {thread_id}")
            
            profile = self.profiles.get(profile_name, {})
            if not profile:
                raise ValueError(f"Profile '{profile_name}' not found")
            
            # CRITICAL: Mỗi thread dùng 1 profile riêng, không chia sẻ cache_dir
            # Mỗi profile chỉ được sử dụng bởi 1 thread tại một thời điểm
            cache_dir = profile.get("cache_dir", str(CHROME_CACHE_DIR / profile_name))
            
            self._log(f"[T{thread_id}] Sử dụng profile: {profile_name}")
            
            browser = BrowserCore(
                cache_dir=cache_dir,
                headless=self.headless_var.get(),
                log_callback=lambda msg: self._log(f"[T{thread_id}|{profile_name}] {msg}")
            )
            browser.build_driver()
            self.browser_instances[thread_id] = browser
            
            sora = SoraAutomationService(
                browser=browser,
                download_dir=str(DOWNLOADS_DIR),
                log_callback=lambda msg: self._log(f"[T{thread_id}|{profile_name}] {msg}")
            )
            self.sora_instances[thread_id] = sora
        
        sora = self.sora_instances[thread_id]
        
        # Convert dict back to SheetRow
        row = SheetRow(
            row_index=data.get("row_index", 0),
            stt=data.get("stt", ""),
            prompt=data.get("prompt", ""),
            image_path=data.get("image_path", ""),
            save_name=data.get("save_name", ""),
            output_path=data.get("output_path", str(DOWNLOADS_DIR)),
            presets=data.get("presets", ""),
            status=data.get("status", ""),
            aspect_ratio=data.get("aspect_ratio", self.default_aspect.get()),
            duration=data.get("duration", self.default_duration.get()),
        )
        
        # Process
        result = sora.process_row(row)
        return result
        
    def _on_task_complete(self, task: Task):
        """Called when a task completes"""
        self._update_stats()
        
    def _on_task_error(self, task: Task, error: Exception):
        """Called when a task fails"""
        self._log(f"❌ Task {task.id} error: {error}")
        self._update_stats()
        
    def _stop_execution(self):
        """Stop execution"""
        if self.thread_pool:
            self.thread_pool.stop(wait=False)
            
        # Close browsers
        for browser in self.browser_instances.values():
            try:
                browser.close()
            except:
                pass
                
        self.browser_instances.clear()
        self.sora_instances.clear()
        
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.pause_btn.config(state="disabled")
        
        self._log("⏹️ Execution stopped")
        
    def _pause_execution(self):
        """Pause/resume execution"""
        # TODO: Implement pause functionality
        pass
        
    def _update_progress(self):
        """Update progress bar and stats"""
        if not self.is_running or not self.thread_pool:
            return
            
        self._update_stats()
        
        # Calculate progress
        total = len(self.tasks)
        if total > 0:
            completed = self.thread_pool.get_completed_count() + self.thread_pool.get_failed_count()
            progress = (completed / total) * 100
            self.progress_var.set(progress)
            self.status_label.config(text=f"Progress: {completed}/{total} ({progress:.1f}%)")
            
        # Check if all done
        if self.thread_pool.get_pending_count() == 0 and self.thread_pool.get_running_count() == 0:
            self._log("✅ All tasks completed!")
            self._stop_execution()
            return
            
        # Schedule next update
        self.root.after(1000, self._update_progress)
        
    def _update_stats(self):
        """Update statistics labels"""
        if self.thread_pool:
            self.stats_labels["pending"].config(text=str(self.thread_pool.get_pending_count()))
            self.stats_labels["running"].config(text=str(self.thread_pool.get_running_count()))
            self.stats_labels["completed"].config(text=str(self.thread_pool.get_completed_count()))
            self.stats_labels["failed"].config(text=str(self.thread_pool.get_failed_count()))
            
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
                self.log_text.config(state="normal")
                self.log_text.insert("end", message + "\n")
                if self.auto_scroll_var.get():
                    self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_log_queue)
            
    def run(self):
        """Start the application"""
        self._log("🎬 Sora Automation Tool started")
        self.root.mainloop()


def main():
    """Entry point"""
    app = SoraToolApp()
    app.run()


if __name__ == "__main__":
    main()
