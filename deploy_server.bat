@echo off
chcp 65001 >nul
echo ===== REPITBOT SERVER DEPLOYMENT =====
echo.

REM Set variables
set "BOT_DIR=%~dp0"
set "PYTHON_CMD=python"

echo [INFO] Bot directory: %BOT_DIR%
echo [INFO] Checking Python installation...

REM Check Python
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python first.
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

REM Check if we're in git repo
if not exist ".git" (
    echo [ERROR] This is not a git repository!
    pause
    exit /b 1
)

echo [INFO] Pulling latest changes from git...
git fetch origin
git reset --hard origin/main
if %errorlevel% neq 0 (
    echo [WARNING] Failed to update from main branch. Trying current branch...
    git pull
)

echo [INFO] Installing/updating Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

echo [INFO] Running database migration...
%PYTHON_CMD% fix_db.py
if %errorlevel% neq 0 (
    echo [WARNING] Database migration had issues
)

echo [INFO] Testing bot startup...
timeout /t 2 >nul
%PYTHON_CMD% -c "import sys; sys.path.insert(0, 'src'); from database import engine; print('Database OK')"
if %errorlevel% neq 0 (
    echo [ERROR] Database connection failed!
    pause
    exit /b 1
)

echo.
echo [SUCCESS] Deployment completed!
echo [INFO] Bot is ready to run with: start_bot.bat
echo [INFO] Or setup Task Scheduler to run start_bot.bat automatically
echo.
pause