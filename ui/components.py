"""
Reusable UI components for modern interface
"""
import customtkinter as ctk
import tkinter as tk
from typing import Callable, Optional


class ModernColors:
    """Modern color palette"""
    BG_PRIMARY = "#1a1d2e"
    BG_SECONDARY = "#16213e"
    BG_CARD = "#0f3460"
    ACCENT_PRIMARY = "#3282b8"
    ACCENT_SECONDARY = "#00d9ff"
    ACCENT_HOVER = "#4a9fd8"
    SUCCESS = "#27ae60"
    WARNING = "#f39c12"
    ERROR = "#e74c3c"
    INFO = "#3498db"
    TEXT_PRIMARY = "#ecf0f1"
    TEXT_SECONDARY = "#95a5a6"
    TEXT_MUTED = "#7f8c8d"
    BORDER = "#2c3e50"
    HOVER = "#34495e"


class ModernButton(ctk.CTkButton):
    """Custom button with hover effects and consistent styling"""
    
    def __init__(self, master, **kwargs):
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


class StatBox(ctk.CTkFrame):
    """Colored stat box with label and value"""
    
    def __init__(
        self,
        master,
        label: str,
        initial_value: str = "0",
        color: str = ModernColors.INFO,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=color,
            corner_radius=10,
            width=150,
            height=100,
            **kwargs
        )
        self.pack_propagate(False)
        
        # Label
        self.label = ctk.CTkLabel(
            self,
            text=label,
            font=("Segoe UI", 12),
            text_color="white"
        )
        self.label.pack(pady=(15, 5))
        
        # Value
        self.value_label = ctk.CTkLabel(
            self,
            text=initial_value,
            font=("Segoe UI", 32, "bold"),
            text_color="white"
        )
        self.value_label.pack()
    
    def set_value(self, value: str):
        """Update the displayed value"""
        self.value_label.configure(text=str(value))


class ModernEntry(ctk.CTkEntry):
    """Styled entry with consistent theme"""
    
    def __init__(self, master, **kwargs):
        defaults = {
            "height": 40,
            "font": ("Segoe UI", 12),
            "fg_color": ModernColors.BG_SECONDARY,
            "border_color": ModernColors.BORDER,
            "text_color": ModernColors.TEXT_PRIMARY,
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class ModernComboBox(ctk.CTkComboBox):
    """Styled combobox with consistent theme"""
    
    def __init__(self, master, **kwargs):
        defaults = {
            "height": 40,
            "font": ("Segoe UI", 12),
            "dropdown_font": ("Segoe UI", 12),
            "fg_color": ModernColors.BG_SECONDARY,
            "border_color": ModernColors.BORDER,
            "button_color": ModernColors.ACCENT_PRIMARY,
            "button_hover_color": ModernColors.ACCENT_HOVER,
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class ModernCheckBox(ctk.CTkCheckBox):
    """Styled checkbox with consistent theme"""
    
    def __init__(self, master, **kwargs):
        defaults = {
            "font": ("Segoe UI", 11),
            "fg_color": ModernColors.ACCENT_PRIMARY,
            "hover_color": ModernColors.ACCENT_HOVER,
            "text_color": ModernColors.TEXT_PRIMARY,
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)


class LabeledInput(ctk.CTkFrame):
    """Input field with label"""
    
    def __init__(
        self,
        master,
        label: str,
        input_type: str = "entry",  # "entry" or "combobox"
        values: list = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent")
        
        # Label
        ctk.CTkLabel(
            self,
            text=label,
            font=("Segoe UI", 12),
            text_color=ModernColors.TEXT_SECONDARY
        ).pack(side="left", padx=(0, 10))
        
        # Input
        if input_type == "combobox":
            self.input = ModernComboBox(self, values=values or [], **kwargs)
        else:
            self.input = ModernEntry(self, **kwargs)
        self.input.pack(side="left", padx=5)
    
    def get(self):
        """Get input value"""
        return self.input.get()
    
    def set(self, value):
        """Set input value"""
        if isinstance(self.input, ModernComboBox):
            self.input.set(value)
        else:
            self.input.delete(0, "end")
            self.input.insert(0, value)


class ActionButton(ModernButton):
    """Button with icon and action"""
    
    def __init__(
        self,
        master,
        text: str,
        command: Optional[Callable] = None,
        icon: str = "",
        button_type: str = "primary",  # primary, success, warning, error
        **kwargs
    ):
        # Set color based on type
        colors = {
            "primary": (ModernColors.ACCENT_PRIMARY, ModernColors.ACCENT_HOVER),
            "success": (ModernColors.SUCCESS, "#229954"),
            "warning": (ModernColors.WARNING, "#e67e22"),
            "error": (ModernColors.ERROR, "#c0392b"),
            "info": (ModernColors.INFO, "#2980b9"),
        }
        fg_color, hover_color = colors.get(button_type, colors["primary"])
        
        # Add icon to text if provided
        display_text = f"{icon} {text}" if icon else text
        
        super().__init__(
            master,
            text=display_text,
            command=command,
            fg_color=fg_color,
            hover_color=hover_color,
            **kwargs
        )


class SectionHeader(ctk.CTkLabel):
    """Section header with consistent styling"""
    
    def __init__(self, master, text: str, **kwargs):
        defaults = {
            "text": text,
            "font": ("Segoe UI", 18, "bold"),
            "text_color": ModernColors.TEXT_PRIMARY,
        }
        defaults.update(kwargs)
        super().__init__(master, **defaults)
