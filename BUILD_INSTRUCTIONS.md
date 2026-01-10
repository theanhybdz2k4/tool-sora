# Hướng dẫn Build Sora Automation Tool

## Yêu cầu

- Python 3.8 trở lên
- Windows 10/11
- Kết nối internet (để download dependencies)

## Cách Build

### Cách 1: Sử dụng build.bat (Khuyến nghị)

1. Mở Command Prompt hoặc PowerShell
2. Chạy lệnh:
   ```batch
   build.bat
   ```

Script sẽ tự động:
- Kiểm tra và cài đặt PyInstaller
- Cài đặt tất cả dependencies
- Xóa build cũ
- Build file exe mới

### Cách 2: Sử dụng build.py

1. Mở Command Prompt hoặc PowerShell
2. Chạy lệnh:
   ```batch
   python build.py
   ```

### Cách 3: Build thủ công

1. Cài đặt PyInstaller:
   ```batch
   pip install pyinstaller
   ```

2. Cài đặt dependencies:
   ```batch
   pip install -r requirements.txt
   ```

3. Build exe:
   ```batch
   pyinstaller build_sora_tool.spec --clean --noconfirm
   ```

## Kết quả

Sau khi build thành công, bạn sẽ có cấu trúc sau:
```
dist\SoraTool\
  - SoraTool.exe        (file chính, ~8-10MB)
  - _internal\          (thư mục chứa tất cả dependencies)
  - README.md           (nếu có)
```

**Lưu ý**: Build theo kiểu **onedir** (one directory) - file exe nhỏ + thư mục `_internal` chứa dependencies. Để sử dụng trên máy khác, copy cả thư mục `SoraTool` (bao gồm cả `_internal`).

## Các file được đóng gói

- ✅ Tất cả Python modules cần thiết (trong `_internal`)
- ✅ Selenium và ChromeDriver (tự động download khi chạy)
- ✅ CustomTkinter UI libraries
- ✅ OpenPyXL cho Excel
- ✅ Config files
- ✅ Logo và icon

## Cấu trúc build (onedir mode)

Build theo kiểu **onedir** (one directory):
- File `SoraTool.exe` nhỏ (~8-10MB) - chỉ chứa bootloader
- Thư mục `_internal` chứa tất cả Python runtime và dependencies (~100-200MB)
- Dễ dàng copy cả thư mục để sử dụng trên máy khác
- Khởi động nhanh hơn onefile mode

## Lưu ý

1. **File exe độc lập**: File exe có thể chạy độc lập, không cần cài Python trên máy đích
2. **ChromeDriver**: ChromeDriver sẽ được tự động download khi chạy lần đầu
3. **Kích thước file**: File exe có thể lớn (~100-200MB) do chứa toàn bộ Python runtime
4. **Antivirus**: Một số antivirus có thể cảnh báo về file exe được build từ PyInstaller, đây là false positive

## Troubleshooting

### Lỗi "Module not found"
- Kiểm tra xem tất cả dependencies đã được cài đặt chưa
- Thêm module vào `hiddenimports` trong `build_sora_tool.spec`

### Lỗi "File not found"
- Đảm bảo đang chạy script từ thư mục gốc của project
- Kiểm tra file `main.py` có tồn tại không

### File exe không chạy
- Kiểm tra log file (nếu có)
- Thử build với `console=True` trong spec để xem lỗi
- Đảm bảo Windows Defender không block file

## Tối ưu kích thước file

Nếu muốn giảm kích thước file exe:
1. Sử dụng UPX compression (đã bật trong spec)
2. Loại bỏ các module không cần thiết trong `excludes`
3. Sử dụng `--onefile` mode (đã được cấu hình)

