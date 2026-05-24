@echo off
title LiveStream Pro
echo ========================================
echo  LiveStream Pro - Stream 24/7
echo ========================================
echo.

REM Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Python chua duoc cai dat!
    echo Tai Python tai: https://python.org
    pause
    exit /b 1
)

REM Kiểm tra FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [CANH BAO] FFmpeg chua duoc cai hoac chua them vao PATH!
    echo Tai FFmpeg tai: https://ffmpeg.org/download.html
    echo.
)

REM Cài requirements nếu chưa có
echo Kiem tra thu vien...
pip install -r requirements.txt --quiet

echo.
echo Khoi dong LiveStream Pro...
python main.py

if errorlevel 1 (
    echo.
    echo [LOI] Ung dung bi loi. Xem thong bao tren.
    pause
)
