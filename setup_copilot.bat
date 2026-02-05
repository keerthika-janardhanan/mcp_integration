@echo off
echo Installing VS Code Extension...
cd vscode-copilot-bridge
call npm install
call npm run compile
echo.
echo Extension ready. Press F5 in VS Code to launch.
echo.
echo Installing Python dependencies...
cd ..
pip install requests
echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Press F5 in VS Code (with vscode-copilot-bridge folder open)
echo 2. Add COPILOT_BRIDGE_URL=http://localhost:3030 to .env
echo 3. Start backend: python app/api/main.py
