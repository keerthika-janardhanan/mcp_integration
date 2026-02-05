# Quick Start - Copilot Integration

## Step 1: Install VS Code Extension

```bash
cd vscode-copilot-bridge
npm install
npm run compile
```

## Step 2: Launch Extension

**Option A - Debug Mode:**
1. Open `vscode-copilot-bridge` folder in VS Code
2. Press `F5` (starts extension in new VS Code window)
3. Check Debug Console - should see: "Copilot Bridge running on http://localhost:3030"

**Option B - Install Locally:**
```bash
code --install-extension vscode-copilot-bridge
```

## Step 3: Configure Environment

Add to `.env` file:
```
COPILOT_BRIDGE_URL=http://localhost:3030
```

## Step 4: Install Python Dependency

```bash
pip install requests
```

## Step 5: Start Backend

```bash
python app/api/main.py
```

Backend runs on: http://localhost:8001

## Step 6: Start Frontend

```bash
cd frontend
npm run dev
```

Frontend runs on: http://localhost:5178

## Verify It Works

Test the bridge:
```bash
curl -X POST http://localhost:3030/api/copilot/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}],\"temperature\":0.2}"
```

Should return: `{"content":"..."}`

## Troubleshooting

**"Copilot not available"**
- Ensure GitHub Copilot extension is installed in VS Code
- Check you're logged into GitHub in VS Code
- Verify Copilot subscription is active

**"Connection refused"**
- Extension not running - press F5 in VS Code
- Check port 3030 is not in use: `netstat -ano | findstr :3030`

**"Module not found: requests"**
```bash
pip install requests
```
