# VS Code Copilot Bridge Setup for PyCharm Users

## What This Is
A VS Code extension that runs a local HTTP server (port 3030) to expose GitHub Copilot API. This lets PyCharm Python code call Copilot for AI-powered code generation.

## Why Not a PyCharm Plugin?
**PyCharm does NOT have GitHub Copilot.** PyCharm has JetBrains AI Assistant (different service, different API). Only VS Code has official GitHub Copilot integration. So we create a VS Code extension as a "bridge" that PyCharm calls via HTTP.

**Architecture:** PyCharm (your IDE) → HTTP (localhost:3030) → VS Code Extension (bridge) → GitHub Copilot API

**You use:** PyCharm for coding, VS Code just runs in background as a server.

---

## Quick Setup (2 Steps)

### Step 1: Generate the VS Code Extension

1. **Open VS Code** (you need VS Code for the bridge, PyCharm for your work)
2. **Open GitHub Copilot Chat** (Ctrl+Shift+I or Cmd+Shift+I)
3. **Copy and paste this ENTIRE prompt:**

```
Create a VS Code extension that exposes GitHub Copilot API via HTTP server on port 3030.

REQUIREMENTS:
- Extension name: "copilot-bridge"
- Package.json with activation event: "*"
- HTTP server using Express.js on port 3030
- Endpoints:
  * POST /api/chat - Send messages to Copilot
  * POST /api/complete - Get code completions
  * GET /health - Health check
- Use VS Code's authentication.getSession('github') for auth
- Use fetch() to call Copilot API at https://api.githubcopilot.com/chat/completions
- CORS enabled for localhost
- Request body format: { messages: [{role: "user", content: "..."}], model: "gpt-4", temperature: 0.7 }
- Response: Stream or JSON with Copilot's reply

FILE STRUCTURE:
```
vscode-copilot-bridge/
├── package.json
├── tsconfig.json
├── src/
│   └── extension.ts
└── README.md
```

IMPLEMENTATION in extension.ts:
```typescript
import * as vscode from 'vscode';
import express from 'express';
import cors from 'cors';

let server: any;

export function activate(context: vscode.ExtensionContext) {
    const app = express();
    app.use(cors());
    app.use(express.json());

    // Health check
    app.get('/health', (req, res) => {
        res.json({ status: 'ok', timestamp: new Date().toISOString() });
    });

    // Chat endpoint
    app.post('/api/chat', async (req, res) => {
        try {
            const { messages, model = 'gpt-4', temperature = 0.7 } = req.body;
            
            // Get GitHub session
            const session = await vscode.authentication.getSession('github', ['user:email'], { createIfNone: true });
            
            // Call Copilot API
            const response = await fetch('https://api.githubcopilot.com/chat/completions', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${session.accessToken}`,
                    'Content-Type': 'application/json',
                    'Editor-Version': 'vscode/1.85.0',
                    'Editor-Plugin-Version': 'copilot/1.140.0'
                },
                body: JSON.stringify({ messages, model, temperature, stream: false })
            });

            const data = await response.json();
            res.json(data);
        } catch (error: any) {
            res.status(500).json({ error: error.message });
        }
    });

    // Start server
    server = app.listen(3030, () => {
        vscode.window.showInformationMessage('Copilot Bridge running on http://localhost:3030');
    });
}

export function deactivate() {
    if (server) server.close();
}
```

PACKAGE.JSON:
```json
{
  "name": "copilot-bridge",
  "version": "1.0.0",
  "engines": { "vscode": "^1.85.0" },
  "activationEvents": ["*"],
  "main": "./out/extension.js",
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5"
  },
  "devDependencies": {
    "@types/vscode": "^1.85.0",
    "@types/express": "^4.17.21",
    "@types/node": "^20.10.0",
    "typescript": "^5.3.3"
  }
}
```

Generate all files now.
```

4. **Wait for Copilot to generate** the files
5. **Run these commands in VS Code terminal:**

```powershell
cd vscode-copilot-bridge
npm install
npm run compile
# Press F5 to launch Extension Development Host
```

---

### Step 2: Configure PyCharm to Use the Bridge

**In your PyCharm project root, create/update `.env`:**

```bash
COPILOT_BRIDGE_URL=http://localhost:3030
```

**In your Python code:**

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def ask_copilot(prompt: str) -> str:
    """Call Copilot via VS Code bridge"""
    bridge_url = os.getenv('COPILOT_BRIDGE_URL', 'http://localhost:3030')
    
    response = requests.post(
        f"{bridge_url}/api/chat",
        json={
            "messages": [{"role": "user", "content": prompt}],
            "model": "gpt-4",
            "temperature": 0.7
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        return data['choices'][0]['message']['content']
    else:
        raise Exception(f"Copilot API error: {response.text}")

# Example usage
result = ask_copilot("Generate a Python function to parse JSON")
print(result)
```

---

## Testing

**1. Verify bridge is running:**
```powershell
curl http://localhost:3030/health
# Should return: {"status":"ok","timestamp":"..."}
```

**2. Test from Python:**
```python
import requests
response = requests.get("http://localhost:3030/health")
print(response.json())
```

**3. Make a real Copilot call:**
```python
response = requests.post(
    "http://localhost:3030/api/chat",
    json={"messages": [{"role": "user", "content": "Hello Copilot"}]}
)
print(response.json())
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Port 3030 already in use | Change port in extension.ts (line with `app.listen(3030, ...)`) and .env |
| "GitHub authentication failed" | In VS Code: Sign out and sign in to GitHub (Accounts icon, bottom-left) |
| Connection refused | Ensure VS Code Extension Development Host is running (F5 in VS Code) |
| CORS errors | Verify `app.use(cors())` is in extension.ts before routes |

---

## Daily Usage

**Every time you work:**
1. Open VS Code → Press F5 (starts extension with bridge)
2. Open PyCharm → Write your Python code → Call Copilot via HTTP
3. Leave VS Code running in background

**You don't need to switch between IDEs** - PyCharm does all the work, VS Code just runs the bridge server.

---

## What to Send Your Colleague

**Send this file only.** They need:
- VS Code installed
- GitHub Copilot subscription
- Node.js installed
- Python `requests` and `python-dotenv` packages

That's it. Copy the prompt in Step 1 into their Copilot chat, run the commands, and they're ready.
