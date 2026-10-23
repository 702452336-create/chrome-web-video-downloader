@echo off
setlocal
title Web Video Downloader Setup
cd /d "%~dp0"
python --version
if errorlevel 1 (
  echo Python 3 is required. Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)
python -m pip install --user --upgrade -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 echo WARNING: ffmpeg is not on PATH.
where ffprobe >nul 2>nul
if errorlevel 1 echo WARNING: ffprobe is not on PATH.
echo Setup complete.
pause
