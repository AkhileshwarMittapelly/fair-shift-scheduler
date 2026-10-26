# Fair Shift Scheduler - Automated PowerShell Launcher
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "Fair Shift Scheduler - Automated Verification & Server Launcher" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan

Write-Host "`n[1/4] Installing Python dependencies..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

Write-Host "`n[2/4] Running automated unit test suite (58/58 tests)..." -ForegroundColor Yellow
python -m pytest tests -v

Write-Host "`n[3/4] Running Step 10 Dual-Generation Reproducibility Verification..." -ForegroundColor Yellow
python cli.py verify-reproducibility --scale starter --seed 20261022

Write-Host "`n[4/4] Launching FastAPI Web Application on http://localhost:8000 ..." -ForegroundColor Green
Write-Host "Open your browser to: http://localhost:8000" -ForegroundColor Green
Write-Host "Press CTRL+C to stop the server.`n" -ForegroundColor Gray
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
