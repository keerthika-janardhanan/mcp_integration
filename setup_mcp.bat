@echo off
REM Setup script for MCP integrations in the test automation platform
REM Run this after cloning the repository to configure MCP servers

echo ========================================
echo MCP Integration Setup
echo ========================================
echo.

echo [1/5] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    exit /b 1
)
node --version
echo.

echo [2/5] Checking npm installation...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm is not installed or not in PATH
    exit /b 1
)
npm --version
echo.

echo [3/5] Installing MCP servers...
echo Installing Microsoft Docs MCP...
call npm install -g @microsoft/mcp-server-docs
if %errorlevel% neq 0 (
    echo WARNING: Failed to install Microsoft Docs MCP
)

echo Installing GitHub MCP...
call npm install -g @modelcontextprotocol/server-github
if %errorlevel% neq 0 (
    echo WARNING: Failed to install GitHub MCP
)

echo Installing Filesystem MCP...
call npm install -g @modelcontextprotocol/server-filesystem
if %errorlevel% neq 0 (
    echo WARNING: Failed to install Filesystem MCP
)
echo.

echo [4/5] Checking environment file...
if not exist .env (
    echo Creating .env from template...
    copy .env.template .env
    echo.
    echo IMPORTANT: Please edit .env and add your API keys:
    echo   - GITHUB_TOKEN (from https://github.com/settings/tokens)
    echo   - AZURE_OPENAI_KEY (your Azure OpenAI key)
    echo.
    echo Note: Self-healing uses playwright-test-healer agent (FREE, no API key needed)
    echo.
) else (
    echo .env file already exists
)
echo.

echo [5/5] Verifying MCP configuration...
if exist .vscode\mcp.json (
    echo MCP configuration found: .vscode\mcp.json
) else (
    echo WARNING: .vscode\mcp.json not found
)
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env and add your API keys
echo 2. Run: python -m pytest -q (to test installation)
echo 3. Start the backend: cd app/api ^&^& uvicorn main:app --reload --port 8001
echo 4. Start the frontend: cd frontend ^&^& npm run dev
echo.
echo For detailed MCP configuration, see: docs/MCP_INTEGRATION.md
echo.

pause
