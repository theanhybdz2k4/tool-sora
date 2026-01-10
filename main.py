"""
Sora Automation Tool - Entry Point
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ui.main_window import main

if __name__ == "__main__":
    main()
