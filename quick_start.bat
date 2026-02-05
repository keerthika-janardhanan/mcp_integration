@echo off
echo ============================================
echo    MCP Integration Platform - Quick Start
echo ============================================
echo.

echo [1/3] Checking health...
python check_health.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Health check failed. Please fix issues above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Health check passed! Starting services...
echo ============================================
echo.
echo Opening 3 terminals:
echo   Terminal 1: FastAPI Backend (port 8001)
echo   Terminal 2: React Frontend (port 5173)
echo   Terminal 3: Command console for testing
echo.

REM Start Backend in new window
start "FastAPI Backend" cmd /k "echo Starting FastAPI Backend... && python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8001"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start Frontend in new window
start "React Frontend" cmd /k "echo Starting React Frontend... && cd frontend && npm run dev"

REM Wait a bit for frontend to start
timeout /t 3 /nobreak >nul

REM Open testing console
start "Testing Console" cmd /k "echo ============================================ && echo    Testing Console && echo ============================================ && echo. && echo Available commands: && echo   python -m app.recorder.run_playwright_recorder_v2 --url https://example.com && echo   python demo_self_healing.py && echo   python check_health.py && echo. && echo Web UIs: && echo   Backend API:  http://localhost:8001 && echo   Frontend UI:  http://localhost:5173 && echo   API Docs:     http://localhost:8001/docs && echo."

echo.
echo ============================================
echo Services started!
echo ============================================
echo.
echo Backend API:  http://localhost:8001
echo Frontend UI:  http://localhost:5173
echo API Docs:     http://localhost:8001/docs
echo.
echo Press any key to open browser...
pause >nul

REM Open browser to frontend
start http://localhost:5173

echo.
echo All services running. Check the opened terminals.
echo Close this window when done (services will keep running).
echo.
