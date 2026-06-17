@echo off
title He thong Lap Danh muc Dac ta Ky thuat CSDL
color 0B
cd /d "%~dp0"

:: Kiem tra xem venv co ton tai khong
if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay moi truong ao .venv
    pause
    exit /b
)

:: Chay ung dung
cls
set "PYTHONPATH=%cd%\src"
".venv\Scripts\python.exe" -m technical_schema_cataloger.cli

pause
