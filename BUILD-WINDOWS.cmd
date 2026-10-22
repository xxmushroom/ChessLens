@echo off
setlocal
cd /d "%~dp0"
echo ChessLens - Build a portable Windows app
echo This is a one-time developer build, not an end-user setup.
where py >nul 2>nul
if errorlevel 1 goto pythonfallback
py -3 build_windows.py
goto finished
:pythonfallback
where python >nul 2>nul
if errorlevel 1 goto missing
python build_windows.py
goto finished
:missing
echo Python was not found. Install 64-bit Python 3.11 or newer on this build computer.
:finished
pause
