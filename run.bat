@echo off
REM ====================================================================
REM   Shreya Auto Enterprises - web app launcher
REM   Double-click this file to start the website.
REM   The first run sets up a private environment with the libraries
REM   it needs (Flask, Pillow). After that it just starts instantly.
REM ====================================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup: creating environment and installing libraries...
  py -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo  ============================================================
echo   Shreya Auto is starting...
echo   Website:  http://localhost:5000
echo   Admin:    http://localhost:5000/admin
echo   Leave this window open. Close it to stop the website.
echo  ============================================================
echo.

".venv\Scripts\python.exe" app.py

pause
