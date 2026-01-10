@echo off
echo ========================================
echo Building Sora Automation Tool
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller chua duoc cai dat!
    echo Dang cai dat PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo Loi cai dat PyInstaller!
        pause
        exit /b 1
    )
)

REM Check if all dependencies are installed
echo Kiem tra dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Loi cai dat dependencies!
    pause
    exit /b 1
)

REM Clean previous builds
echo Xoa build cu...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

REM Build with PyInstaller
echo.
echo Dang build exe...
echo (Qua trinh nay co the mat 5-10 phut...)
echo.
pyinstaller build_sora_tool.spec --clean --noconfirm --log-level=INFO

if errorlevel 1 (
    echo.
    echo ========================================
    echo BUILD FAILED!
    echo ========================================
    echo Vui long kiem tra log o tren de tim loi
    pause
    exit /b 1
)

REM Check build result
echo.
echo Kiem tra ket qua build...
if exist "dist\SoraTool\SoraTool.exe" (
    echo ✅ Tim thay file exe: dist\SoraTool\SoraTool.exe
    if exist "dist\SoraTool\_internal" (
        echo ✅ Tim thay thu muc _internal chua dependencies
        echo.
        echo Cau truc build:
        echo   dist\SoraTool\
        echo     - SoraTool.exe (file chinh)
        echo     - _internal\ (thu muc chua dependencies)
        echo     - README.md (neu co)
        echo.
        echo ✅ Build thanh cong theo kieu onedir!
        echo    Co the copy ca thu muc SoraTool den may khac de su dung
    ) else (
        echo ⚠️ Khong tim thay thu muc _internal!
    )
) else if exist "dist\SoraTool.exe" (
    echo ✅ Tim thay file exe: dist\SoraTool.exe (onefile mode)
    echo    Day la onefile mode - tat ca trong 1 file
) else (
    echo ❌ Khong tim thay file exe!
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESS!
echo ========================================
echo.
echo File exe duoc tao tai: dist\SoraTool.exe
echo.
echo Luu y:
echo - File exe co the chay doc lap, khong can Python
echo - Dung xoa thu muc dist sau khi build
echo - Co the copy file exe den may khac de su dung
echo - Neu file exe khong chay, thu doi console=True trong spec de xem loi
echo.
pause

