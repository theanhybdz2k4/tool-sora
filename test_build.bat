@echo off
echo ========================================
echo Testing SoraTool.exe
echo ========================================
echo.

if not exist "dist\SoraTool.exe" (
    echo ❌ File dist\SoraTool.exe không tồn tại!
    echo Vui lòng chạy build.bat trước
    pause
    exit /b 1
)

echo ✅ Tìm thấy file exe
echo.
echo Kích thước file:
dir "dist\SoraTool.exe" | findstr "SoraTool.exe"
echo.

echo Đang test chạy file exe...
echo (Nhấn Ctrl+C để dừng nếu cần)
echo.

cd dist
start SoraTool.exe

echo.
echo ✅ Đã khởi động SoraTool.exe
echo Nếu ứng dụng không mở hoặc báo lỗi, có thể build chưa đầy đủ
echo.
pause

