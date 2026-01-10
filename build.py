"""
Build script for Sora Automation Tool
Tự động build exe với PyInstaller
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print("✅ PyInstaller đã được cài đặt")
        return True
    except ImportError:
        print("❌ PyInstaller chưa được cài đặt")
        print("Đang cài đặt PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return True

def install_dependencies():
    """Install all dependencies"""
    print("📦 Đang kiểm tra và cài đặt dependencies...")
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
        print("✅ Đã cài đặt dependencies")
    else:
        print("⚠️ Không tìm thấy requirements.txt")

def clean_build():
    """Clean previous build files"""
    print("🧹 Đang xóa build cũ...")
    dirs_to_remove = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  ✅ Đã xóa {dir_name}")

def build_exe():
    """Build exe using PyInstaller"""
    print("\n🔨 Đang build exe...")
    spec_file = Path("build_sora_tool.spec")
    
    if not spec_file.exists():
        print(f"❌ Không tìm thấy file {spec_file}")
        return False
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller",
            str(spec_file),
            "--clean",
            "--noconfirm"
        ])
        print("\n✅ BUILD THÀNH CÔNG!")
        print(f"📦 File exe: {Path('dist') / 'SoraTool.exe'}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ BUILD THẤT BẠI: {e}")
        return False

def main():
    """Main build process"""
    print("=" * 50)
    print("🎬 Sora Automation Tool - Build Script")
    print("=" * 50)
    print()
    
    # Check PyInstaller
    if not check_pyinstaller():
        return 1
    
    # Install dependencies
    install_dependencies()
    
    # Clean old builds
    clean_build()
    
    # Build exe
    if build_exe():
        print("\n" + "=" * 50)
        print("📝 Lưu ý:")
        print("  - File exe có thể chạy độc lập, không cần Python")
        print("  - Đừng xóa thư mục dist sau khi build")
        print("  - Có thể copy file exe đến máy khác để sử dụng")
        print("=" * 50)
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())

