@echo off
title Web Video Downloader Companion
cd /d "%~dp0"
python service.py
if errorlevel 1 pause
