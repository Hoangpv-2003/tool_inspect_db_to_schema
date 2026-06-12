@echo off
title DB Schema Crawler Tool - Giao diện cho người nghiệp vụ
color 0B
cd /d %~dp0

:: Kiem tra xem python co duoc cai dat khong
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python tren may tinh cua ban.
    echo Vui long cai dat Python va thu lai.
    pause
    exit /b
)

:: Cai dat cac thu vien can thiet neu chua co
echo Dang kiem tra va cap nhat thu vien (co the mat vai giay)...
pip install -r requirements.txt --quiet --disable-pip-version-check

:: Chay ung dung
cls
set PYTHONPATH=%PYTHONPATH%;%cd%\src
python -m db_schema_crawler.cli

pause
