@echo off
echo ========================================
echo Starting Copilot Integration
echo ========================================
echo.

REM Load environment variables from .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="API_PORT" set BACKEND_PORT=%%b
    if "%%a"=="FRONTEND_PORT" set FRONTEND_PORT=%%b
)

REM Set defaults if not found in .env
if not defined BACKEND_PORT set BACKEND_PORT=8001
if not defined FRONTEND_PORT set FRONTEND_PORT=5178

echo [1/3] Checking VS Code Extension...
tasklist /FI "IMAGENAME eq Code.exe" 2>NUL | find /I /N "Code.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo VS Code is running
) else (
    echo WARNING: VS Code not detected. Launch extension manually with F5
)
echo.

echo [2/3] Starting Backend...
start "Backend Server" cmd /k "python app\api\main.py"
timeout /t 3 /nobreak >nul
echo Backend started on http://localhost:%BACKEND_PORT%
echo.

echo [3/3] Starting Frontend...
start "Frontend Server" cmd /k "cd frontend && npm run dev"
timeout /t 3 /nobreak >nul
echo Frontend starting on http://localhost:%FRONTEND_PORT%
echo.

echo ========================================
echo All services started!
echo ========================================
echo.
echo Backend:  http://localhost:%BACKEND_PORT%
echo Frontend: http://localhost:%FRONTEND_PORT%
echo Bridge:   http://localhost:3030
echo.
echo Press any key to stop all services...
pause >nul

taskkill /FI "WindowTitle eq Backend Server*" /T /F >nul 2>&1
taskkill /FI "WindowTitle eq Frontend Server*" /T /F >nul 2>&1
echo Services stopped.
