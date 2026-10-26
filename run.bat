@echo off
echo ===============================================================================
echo Fair Shift Scheduler - Automated One-Click Verification and Launcher
echo ===============================================================================
echo.

echo [1/4] Installing Python dependencies...
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Error installing dependencies.
    exit /b %ERRORLEVEL%
)

echo.
echo [2/4] Running automated unit test suite (7/7 tests)...
python -m pytest tests -v
if %ERRORLEVEL% NEQ 0 (
    echo Unit tests failed.
    exit /b %ERRORLEVEL%
)

echo.
echo [3/4] Running Step 10 Dual-Generation Reproducibility Verification...
python cli.py verify-reproducibility --scale starter --seed 20261022
if %ERRORLEVEL% NEQ 0 (
    echo Reproducibility check failed.
    exit /b %ERRORLEVEL%
)

echo.
echo [4/4] Launching FastAPI Web Application on http://localhost:8000 ...
echo Open your browser to: http://localhost:8000
echo Press CTRL+C to stop the server.
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
