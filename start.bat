@echo off
setlocal

echo =========================================
echo       QueryLocal - 1-Click Setup
echo =========================================
echo.

:: Check for Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not running.
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: Check for Ollama
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama is not installed.
    echo Please install Ollama: https://ollama.com/
    pause
    exit /b 1
)

echo Which AI model would you like to run?
echo (Recommended: qwen2.5-coder:7b)
set /p MODEL_NAME="Enter model name (or press Enter for default): "

if "%MODEL_NAME%"=="" (
    set MODEL_NAME=qwen2.5-coder:7b
)

echo.
echo Save choice to .env file...
echo OLLAMA_MODEL=%MODEL_NAME% > .env

echo.
echo Pulling %MODEL_NAME%... (This may take a moment if not already downloaded)
ollama pull %MODEL_NAME%

echo.
echo Starting Docker containers...
docker-compose up --build

echo.
echo Application stopped.
pause
