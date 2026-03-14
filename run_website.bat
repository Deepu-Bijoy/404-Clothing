@echo off
echo ==========================================
echo      Cloth Store Website Setup & Run
echo ==========================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b
)

REM Create virtual environment if it doesn't exist
if not exist .venv (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
) else (
    echo [INFO] Virtual environment already exists.
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate

REM Install dependencies
echo [INFO] Installing/Updating dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b
)

REM Initialize Database
echo [INFO] Initializing database...
python init_db.py
if %errorlevel% neq 0 (
    echo [ERROR] Failed to initialize database.
    pause
    exit /b
)

REM Start the Application
echo [INFO] Starting Flask Server...
echo [INFO] Open your browser and go to: http://127.0.0.1:5000
python app.py

pause
