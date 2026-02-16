# Setting Up VS Code Copilot Bridge for PyCharm Users

## Overview

Even though your colleague uses **PyCharm**, they still need **VS Code** to run the Copilot bridge (it acts as a server). PyCharm will use Python to call the bridge via HTTP.

```
PyCharm (Python code)
    ↓ HTTP request
VS Code Extension Bridge (running in VS Code)
    ↓ VS Code API
GitHub Copilot
```

## Prerequisites

1. ✅ GitHub Copilot subscription (required)
2. ✅ VS Code installed (just for the bridge)
3. ✅ PyCharm (their IDE)
4. ✅ Node.js 18+ installed

## Step 1: Create VS Code Extension Bridge

### Option A: Copy from Your Machine

If you have access to the working bridge:

```powershell
# On your machine, zip the bridge folder
Compress-Archive -Path "C:\Users\2218532\PycharmProjects\mcp_integration\vscode-copilot-bridge" -DestinationPath "copilot-bridge.zip"

# Send copilot-bridge.zip to your colleague
# They extract it anywhere, e.g., C:\copilot-bridge
```

### Option B: Generate from Scratch

**Tell GitHub Copilot (in VS Code) this prompt:**

```
Create a VS Code extension that exposes GitHub Copilot Chat API via HTTP endpoint.

Requirements:
1. Extension should start an Express server on port 3030
2. Endpoint: POST /api/copilot/chat
3. Request body: { "messages": [{"role": "user", "content": "..."}], "temperature": 0.1 }
4. Use @vscode/prompt-tsx to call GitHub Copilot
5. Return Copilot's response as JSON: { "response": "..." }
6. Handle errors gracefully

File structure:
- package.json (Express + body-parser dependencies)
- tsconfig.json (TypeScript config)
- src/extension.ts (main extension code)
- README.md (setup instructions)

Activation: Extension should activate on startup (*) and start the HTTP server immediately.
```

## Step 2: Install Dependencies

In VS Code terminal (inside the bridge folder):

```powershell
npm install
npm run compile
```

This installs Express, body-parser, and compiles TypeScript.

## Step 3: Install GitHub Copilot in VS Code

1. Open VS Code
2. Extensions (Ctrl+Shift+X)
3. Search "GitHub Copilot"
4. Install both:
   - **GitHub Copilot** (main extension)
   - **GitHub Copilot Chat** (chat interface)
5. Sign in with GitHub account that has Copilot subscription
6. Verify: Click Copilot icon in sidebar, should show chat interface

## Step 4: Run the Bridge Extension

### In VS Code:

1. **Open the bridge folder:**
   - File → Open Folder
   - Select `copilot-bridge` folder
   - Click "Select Folder"

2. **Open Run & Debug:**
   - Click Run icon in sidebar (🐛 triangle)
   - Or press `Ctrl+Shift+D`

3. **Select configuration:**
   - Top dropdown: Select **"Run Extension"**
   - If not available, create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run Extension",
      "type": "extensionHost",
      "request": "launch",
      "args": [
        "--extensionDevelopmentPath=${workspaceFolder}"
      ],
      "outFiles": [
        "${workspaceFolder}/out/**/*.js"
      ],
      "preLaunchTask": "${defaultBuildTask}"
    }
  ]
}
```

4. **Start the bridge:**
   - Click green play button ▶
   - Or press `F5`

5. **Verify it's running:**
   - A NEW VS Code window opens (Extension Development Host)
   - In ORIGINAL window → View → Debug Console
   - Should see:
   ```
   [COPILOT BRIDGE] Extension activated
   [COPILOT BRIDGE] Server running on http://localhost:3030
   ```

6. **Test the endpoint:**
   ```powershell
   # In PowerShell
   $body = @{
       messages = @(
           @{
               role = "user"
               content = "Hello from PowerShell!"
           }
       )
   } | ConvertTo-Json -Depth 10

   Invoke-RestMethod -Uri "http://localhost:3030/api/copilot/chat" `
       -Method POST `
       -Body $body `
       -ContentType "application/json"
   ```

   Should return: `{ "response": "Hello! How can I help you?" }`

## Step 5: Configure PyCharm Project

### 1. Copy Python Integration Files

Your colleague needs these files from your project:

```
app/
  services/
    llm_client.py           # Main LLM client (with copilot support)
    llm_client_copilot.py   # Copilot HTTP client
```

### 2. Create/Update `.env` File

In their PyCharm project root:

```dotenv
# Copilot Bridge Configuration
COPILOT_BRIDGE_URL=http://localhost:3030

# Enable LLM Features
ENABLE_LLM_FEATURES=true
USE_LLM_CODE_ENHANCEMENT=true
USE_LLM_LOCATOR_GENERATION=false
ANALYZE_FRAMEWORK_WITH_LLM=true
LLM_TIMEOUT_MS=10000

# Use Copilot instead of Azure OpenAI
USE_COPILOT=true
```

### 3. Install Python Dependencies

In PyCharm terminal:

```powershell
pip install requests python-dotenv
```

### 4. Test from PyCharm

Create a test script in PyCharm:

```python
# test_copilot_bridge.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_copilot():
    url = os.getenv("COPILOT_BRIDGE_URL", "http://localhost:3030")
    
    response = requests.post(
        f"{url}/api/copilot/chat",
        json={
            "messages": [
                {"role": "user", "content": "Write a Python function to reverse a string"}
            ]
        },
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    test_copilot()
```

Run in PyCharm (right-click → Run 'test_copilot_bridge').

Expected output:
```
Status: 200
Response: {'response': 'def reverse_string(s):\n    return s[::-1]'}
```

## Step 6: Integrate with Your Application

### Update LLM Client Usage

In your colleague's PyCharm project:

```python
# Before (Azure OpenAI)
from app.services.llm_client import ask_llm_for_script

# After (works with both Azure and Copilot)
from app.services.llm_client import ask_llm_for_script

# No code changes needed! Client automatically uses Copilot
# if USE_COPILOT=true in .env
```

The client checks environment variable and routes accordingly.

## Troubleshooting

### Issue 1: "Connection refused" (Port 3030)

**Cause:** VS Code bridge not running

**Solution:**
1. Open VS Code with bridge folder
2. Press `F5` to start extension
3. Verify in Debug Console: "Server running on http://localhost:3030"

### Issue 2: "Copilot not available"

**Cause:** GitHub Copilot not installed/authenticated in VS Code

**Solution:**
1. Install GitHub Copilot extensions
2. Click Copilot icon in VS Code sidebar
3. Sign in with GitHub account
4. Verify subscription is active

### Issue 3: "Timeout waiting for Copilot"

**Cause:** Copilot slow to respond or not activated

**Solution:**
1. Increase timeout in Python client:
   ```python
   response = requests.post(url, json=data, timeout=120)  # 2 minutes
   ```
2. Warm up Copilot: Use chat in VS Code first
3. Check VS Code Debug Console for errors

### Issue 4: "Port 3030 already in use"

**Cause:** Another process using port 3030

**Solution:**
1. Find process:
   ```powershell
   netstat -ano | findstr :3030
   ```
2. Kill process:
   ```powershell
   taskkill /PID <PID> /F
   ```
3. Or change port in extension.ts:
   ```typescript
   const PORT = 3031; // Use different port
   ```
   And update `.env`:
   ```dotenv
   COPILOT_BRIDGE_URL=http://localhost:3031
   ```

### Issue 5: PyCharm can't find `.env` file

**Cause:** `.env` not in project root or not loaded

**Solution:**
1. Verify `.env` is in project root (same level as `app/` folder)
2. Install python-dotenv:
   ```powershell
   pip install python-dotenv
   ```
3. Load explicitly in code:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  PYCHARM (Your colleague's IDE)                │
│                                                 │
│  ┌───────────────────────────────────────┐     │
│  │  Python Code                          │     │
│  │  from app.services.llm_client import  │     │
│  │    ask_llm_for_script                 │     │
│  │                                       │     │
│  │  result = ask_llm_for_script(...)    │     │
│  └───────────────┬───────────────────────┘     │
│                  │                             │
└──────────────────┼─────────────────────────────┘
                   │ HTTP POST
                   │ http://localhost:3030/api/copilot/chat
                   ↓
┌─────────────────────────────────────────────────┐
│                                                 │
│  VS CODE (Running in background)               │
│                                                 │
│  ┌───────────────────────────────────────┐     │
│  │  Copilot Bridge Extension             │     │
│  │  Express Server (port 3030)           │     │
│  │                                       │     │
│  │  POST /api/copilot/chat               │     │
│  │    ↓                                  │     │
│  │  @vscode/prompt-tsx                   │     │
│  │    ↓                                  │     │
│  │  GitHub Copilot API                   │     │
│  │    ↓                                  │     │
│  │  Return response                      │     │
│  └───────────────────────────────────────┘     │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Quick Setup Summary (Copy-Paste for Your Colleague)

**What to tell your colleague:**

> "You need VS Code running the Copilot bridge in the background, but you can still use PyCharm for coding.
>
> **Setup (15 minutes):**
> 1. Install VS Code + GitHub Copilot extension (sign in)
> 2. Extract copilot-bridge.zip I sent you
> 3. Open bridge folder in VS Code → Press F5
> 4. In PyCharm: Update .env with `COPILOT_BRIDGE_URL=http://localhost:3030`
> 5. Test: Run test_copilot_bridge.py
>
> **Daily Usage:**
> 1. Open VS Code → Press F5 (starts bridge)
> 2. Open PyCharm → Work normally
> 3. Your Python code automatically uses Copilot via HTTP
>
> Keep both open while working!"

## Files to Share

Send your colleague:

1. **copilot-bridge.zip** (VS Code extension)
2. **llm_client.py** (Python client with Copilot support)
3. **llm_client_copilot.py** (Copilot HTTP wrapper)
4. **.env.example** (Configuration template)
5. **This guide** (Setup instructions)

## Alternative: Use VS Code for Everything

If your colleague is willing to switch to VS Code temporarily:

**Pros:**
- ✅ Simpler setup (no bridge needed)
- ✅ Native Copilot integration
- ✅ Better debugging for VS Code extensions

**Cons:**
- ❌ Learning curve if unfamiliar with VS Code
- ❌ Loses PyCharm features

They can always run the bridge in VS Code and code in PyCharm (best of both worlds).

## Support

If issues persist:
1. Check VS Code Debug Console for bridge errors
2. Check PyCharm terminal for Python errors
3. Test bridge directly with curl/Postman
4. Verify Copilot subscription is active
5. Restart VS Code extension (press F5 again)

## FAQ

**Q: Do I need VS Code open all the time?**
A: Yes, while using Copilot features. It's just running the bridge server.

**Q: Can multiple people share one bridge?**
A: No, each person needs their own (uses their Copilot subscription).

**Q: Does this work on Mac/Linux?**
A: Yes, same steps but use appropriate terminal commands.

**Q: Can I use PyCharm's Copilot plugin instead?**
A: PyCharm has its own Copilot plugin, but it won't integrate with your Python backend the same way. The bridge approach gives you programmatic access via API.

**Q: What if I don't have Copilot subscription?**
A: Use Azure OpenAI instead (set `USE_COPILOT=false` in .env).
