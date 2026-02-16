# 🚀 Quick Start: Copilot Bridge for PyCharm Users (5 Minutes)

## TL;DR

Your colleague needs **VS Code** (running Copilot bridge) + **PyCharm** (for coding). They communicate via HTTP.

## Option 1: Share Your Working Bridge (FASTEST) ⚡

### Step 1: On Your Machine
```powershell
# Zip the bridge folder
cd C:\Users\2218532\PycharmProjects\mcp_integration
Compress-Archive -Path "vscode-copilot-bridge" -DestinationPath "copilot-bridge-ready.zip"
```

### Step 2: Send to Colleague
- Email/Slack: `copilot-bridge-ready.zip`
- Or share via OneDrive/Google Drive

### Step 3: Colleague Extracts & Runs
```powershell
# Extract to any location
Expand-Archive copilot-bridge-ready.zip -DestinationPath C:\copilot-bridge

# Install dependencies
cd C:\copilot-bridge
npm install

# Compile
npm run compile

# Open in VS Code
code .
```

### Step 4: Start Bridge
- In VS Code: Press `F5`
- Wait for: "Server running on http://localhost:3030"
- ✅ Done! Keep VS Code open

---

## Option 2: Generate from Scratch (10 Minutes) 🛠️

### Step 1: Tell Copilot
Open VS Code → Open Copilot Chat (Ctrl+Alt+I) → Paste:

```
Create a VS Code extension called "copilot-bridge" that:
1. Starts an Express server on port 3030
2. Exposes POST /api/copilot/chat endpoint
3. Uses vscode.lm API to call GitHub Copilot
4. Returns response as JSON: { "content": "..." }

Generate complete files:
- package.json (express, body-parser deps)
- tsconfig.json
- src/extension.ts (full implementation)
- .vscode/launch.json

No placeholders, production-ready code.
```

### Step 2: Install & Run
```powershell
npm install
npm run compile
# Press F5 in VS Code
```

---

## PyCharm Setup (3 Minutes)

### 1. Update `.env`
```dotenv
COPILOT_BRIDGE_URL=http://localhost:3030
USE_COPILOT=true
ENABLE_LLM_FEATURES=true
```

### 2. Install Dependencies
```powershell
pip install requests python-dotenv
```

### 3. Test Connection
Create `test_bridge.py`:
```python
import requests
import json

response = requests.post(
    "http://localhost:3030/api/copilot/chat",
    json={"messages": [{"role": "user", "content": "Hello!"}]},
    timeout=30
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

Run in PyCharm → Should see:
```
Status: 200
Response: {'content': 'Hello! How can I help you?'}
```

✅ **Done!** PyCharm can now use Copilot.

---

## Daily Workflow

### Morning Setup (30 seconds)
1. Open VS Code with bridge folder
2. Press `F5` (starts bridge server)
3. Minimize VS Code
4. Open PyCharm and code normally

### Your Code Just Works
```python
# In PyCharm - no changes needed!
from app.services.llm_client import ask_llm_for_script

result = ask_llm_for_script("Generate test for login page")
# Automatically uses Copilot via bridge
```

---

## Troubleshooting (1 Minute Fixes)

### ❌ "Connection refused"
**Fix:** Press `F5` in VS Code (bridge not running)

### ❌ "Copilot not available"
**Fix:** Install GitHub Copilot extension in VS Code + sign in

### ❌ Port 3030 in use
**Fix:** 
```powershell
netstat -ano | findstr :3030
taskkill /PID <PID> /F
```

---

## Complete File List to Share

Send your colleague:

1. ✅ `copilot-bridge-ready.zip` (working extension)
2. ✅ `PYCHARM_COPILOT_BRIDGE_SETUP.md` (full guide)
3. ✅ `PROMPT_FOR_COPILOT_BRIDGE.md` (Copilot prompt if regenerating)
4. ✅ `.env.example` (configuration template)

```dotenv
# .env.example
COPILOT_BRIDGE_URL=http://localhost:3030
USE_COPILOT=true
ENABLE_LLM_FEATURES=true
USE_LLM_CODE_ENHANCEMENT=true
LLM_TIMEOUT_MS=120000
```

---

## Architecture (Visual)

```
┌──────────────────────┐
│  PYCHARM             │
│  Python code         │──HTTP──┐
│  (colleague's IDE)   │        │
└──────────────────────┘        │
                                ▼
                        ┌──────────────────────┐
                        │  VS CODE             │
                        │  Copilot Bridge      │
                        │  Port 3030           │──┐
                        └──────────────────────┘  │
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │  GitHub      │
                                          │  Copilot     │
                                          └──────────────┘
```

---

## FAQ (30-Second Answers)

**Q: Need VS Code open all the time?**
A: Yes, but minimized in background (just runs server)

**Q: Can use PyCharm's Copilot plugin?**
A: Yes, but won't integrate with Python backend API

**Q: Works on Mac/Linux?**
A: Yes, same steps

**Q: Need Copilot subscription?**
A: Yes (individual ~$10/month or business plan)

**Q: Colleague doesn't have Copilot?**
A: Use Azure OpenAI instead (set `USE_COPILOT=false`)

---

## What to Tell Your Colleague (Copy-Paste)

> **Hey! To use Copilot with PyCharm:**
>
> 1. Extract the `copilot-bridge-ready.zip` I sent
> 2. `cd copilot-bridge` → `npm install` → `npm run compile`
> 3. Open folder in VS Code → Press F5
> 4. In PyCharm: Add to `.env`: `COPILOT_BRIDGE_URL=http://localhost:3030`
> 5. Test with the `test_bridge.py` script I included
>
> **Daily:** Just press F5 in VS Code before coding. Keep it minimized.
>
> **Need help?** Check `PYCHARM_COPILOT_BRIDGE_SETUP.md` (full guide included)

---

## Support Links

- 📖 Full setup guide: `docs/PYCHARM_COPILOT_BRIDGE_SETUP.md`
- 🤖 Copilot prompt: `docs/PROMPT_FOR_COPILOT_BRIDGE.md`
- ✅ Already working in your project: Use that!

---

**Time investment:** 5-10 minutes setup, then seamless integration forever ✨
