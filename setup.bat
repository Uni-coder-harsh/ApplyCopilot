@echo off
REM ApplyCopilot — Windows setup script
REM Usage: setup.bat

echo.
echo   ApplyCopilot - Local-first AI job ^& internship tracker
echo   =========================================================
echo.

REM ── Check Python ────────────────────────────────────────────────────────────
echo [1/5] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.12+ from https://python.org
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo [OK] Python %PY_VER%

REM ── Virtual environment ──────────────────────────────────────────────────────
echo [2/5] Creating virtual environment...
if not exist ".venv" (
    python -m venv .venv
    echo [OK] .venv created
) else (
    echo [OK] .venv already exists
)
call .venv\Scripts\activate.bat

REM ── Install dependencies ─────────────────────────────────────────────────────
echo [3/5] Installing dependencies...
pip install --upgrade pip -q
pip install -e ".[dev]" -q
echo [OK] Dependencies installed

REM ── Check Ollama ─────────────────────────────────────────────────────────────
echo [4/5] Checking Ollama...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Ollama not found. Download from https://ollama.com
    echo        Then run: ollama pull phi3:mini
    echo                  ollama pull mistral:7b-instruct-q4_0
    echo                  ollama pull nomic-embed-text
) else (
    echo [OK] Ollama found
    echo Pulling required models...
    ollama pull phi3:mini
    ollama pull mistral:7b-instruct-q4_0
    ollama pull nomic-embed-text
)

REM ── Copy env example ─────────────────────────────────────────────────────────
echo [5/5] Setting up config...
if not exist ".env" (
    copy config\.env.example .env >nul
    echo [OK] .env created from .env.example
) else (
    echo [OK] .env already exists
)

REM ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo =============================================
echo   Setup complete!
echo =============================================
echo.
echo   Next steps:
echo   1. Activate venv:  .venv\Scripts\activate
echo   2. Run init:       applycopilot init
echo.
pause
