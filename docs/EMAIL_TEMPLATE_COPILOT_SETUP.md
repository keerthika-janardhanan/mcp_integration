# Email Template for Colleague

---

**Subject:** Copilot Bridge Setup for PyCharm - Quick Start Guide

---

Hi [Colleague Name],

I've set up everything you need to use GitHub Copilot with PyCharm. Here's the package:

## 📦 What I'm Sending You

1. **copilot-bridge-ready.zip** - VS Code extension (already compiled)
2. **setup-docs.zip** - Complete setup guides
3. This email - Quick start steps

## ⚡ Quick Setup (10 Minutes)

### Prerequisites
- ✅ GitHub Copilot subscription (check: https://github.com/settings/copilot)
- ✅ Node.js 18+ installed
- ✅ VS Code installed
- ✅ PyCharm (your IDE)

### Step 1: Extract & Install Bridge (5 min)
```powershell
# Extract the bridge
Expand-Archive copilot-bridge-ready.zip -DestinationPath C:\copilot-bridge

# Install dependencies
cd C:\copilot-bridge
npm install

# Compile TypeScript
npm run compile
```

### Step 2: Install GitHub Copilot in VS Code (2 min)
1. Open VS Code
2. Extensions (Ctrl+Shift+X)
3. Search "GitHub Copilot"
4. Install **both**:
   - GitHub Copilot
   - GitHub Copilot Chat
5. Sign in with your GitHub account

### Step 3: Start the Bridge (1 min)
1. In VS Code: File → Open Folder → Select `C:\copilot-bridge`
2. Press **F5** (or Run → Start Debugging)
3. A new VS Code window opens (ignore it, it's the extension host)
4. In the **original** VS Code window → View → Debug Console
5. You should see:
   ```
   [COPILOT BRIDGE] Extension activated
   [COPILOT BRIDGE] Server running on http://localhost:3030
   ```

### Step 4: Configure PyCharm (2 min)
1. In your PyCharm project, create/update `.env`:
   ```dotenv
   COPILOT_BRIDGE_URL=http://localhost:3030
   USE_COPILOT=true
   ENABLE_LLM_FEATURES=true
   ```

2. Install Python dependencies:
   ```powershell
   pip install requests python-dotenv
   ```

### Step 5: Test It! (1 min)
Create `test_bridge.py` in PyCharm:
```python
import requests

response = requests.post(
    "http://localhost:3030/api/copilot/chat",
    json={
        "messages": [
            {"role": "user", "content": "Write a Python function to calculate factorial"}
        ]
    },
    timeout=30
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

Right-click → Run. Should see:
```
Status: 200
Response: {'content': 'def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)'}
```

✅ **Success!** You're all set!

## 🎯 Daily Workflow

**Every morning:**
1. Open VS Code with the bridge folder
2. Press F5 (starts the bridge)
3. Minimize VS Code (leave it running)
4. Open PyCharm and code normally

**Your Python code automatically uses Copilot:**
```python
from app.services.llm_client import ask_llm_for_script

# This now uses Copilot!
result = ask_llm_for_script("Generate test for login page")
```

## 🔧 Troubleshooting

### "Connection refused to localhost:3030"
→ Press F5 in VS Code to start the bridge

### "Copilot not available"
→ Install GitHub Copilot extension in VS Code + sign in

### Port 3030 already in use
```powershell
netstat -ano | findstr :3030
taskkill /PID <PID> /F
```

### Still stuck?
Check the full guide: `docs/PYCHARM_COPILOT_BRIDGE_SETUP.md`

## 📚 Documentation Included

- `COPILOT_BRIDGE_QUICKSTART.md` - This quick start
- `PYCHARM_COPILOT_BRIDGE_SETUP.md` - Complete setup guide
- `PROMPT_FOR_COPILOT_BRIDGE.md` - How to regenerate bridge with Copilot

## ❓ FAQ

**Q: Do I need VS Code open all the time?**
A: Yes, but just minimized in the background (runs the bridge server)

**Q: Can I use PyCharm's Copilot plugin instead?**
A: PyCharm has Copilot, but it won't integrate with our Python backend API. The bridge approach gives you programmatic access.

**Q: What if I don't have a Copilot subscription?**
A: You can use Azure OpenAI instead (set `USE_COPILOT=false` in `.env`)

**Q: Does this work on Mac/Linux?**
A: Yes, same steps (adjust PowerShell commands for bash/zsh)

## 💡 Tips

- Keep the VS Code Debug Console open to see what's happening
- The bridge uses your Copilot subscription (no extra cost)
- You can still use Copilot directly in VS Code while the bridge runs
- If you restart VS Code, just press F5 again

## 🎬 Quick Demo Video

If you prefer a video walkthrough, I can do a quick screenshare showing:
1. Starting the bridge (F5)
2. Configuring PyCharm
3. Testing from Python
4. Seeing it work in your actual code

Let me know!

## 🚀 Ready to Start?

Once you've completed the setup:
1. Reply to confirm it's working
2. If any issues, send me:
   - Screenshot of VS Code Debug Console
   - Error message from PyCharm
   - Output of `netstat -ano | findstr :3030`

Happy coding with Copilot! 🤖

---

**Attachments:**
- copilot-bridge-ready.zip
- setup-docs.zip

---

Feel free to reach out if you hit any snags. The setup is straightforward, but I'm here to help!

Best,
[Your Name]

---

**P.S.** If you prefer, you can also use GitHub Copilot CLI for command-line access, but the bridge gives you programmatic API access from Python, which is what we need for our test automation framework.
