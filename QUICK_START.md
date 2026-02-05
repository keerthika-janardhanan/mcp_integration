# 🎯 Quick Reference: Start & Test Everything

## ⚡ One-Command Startup

```powershell
# Windows: Run everything at once
.\quick_start.bat

# This will:
# 1. Check health
# 2. Start FastAPI backend (port 8001)
# 3. Start React frontend (port 5173)
# 4. Open testing console
# 5. Open browser to UI
```

## 🔍 Manual Health Check

```powershell
python check_health.py
```

**Expected**: `✅ All systems operational! (15/15 checks passed)`

## 🎬 Quick Test Workflows

### 1️⃣ Record with MCP Enhancement (30 seconds)

```powershell
python -m app.recorder.run_playwright_recorder_v2 ^
  --url "https://demo.playwright.dev/todomvc" ^
  --session-name quick-test ^
  --timeout 30

# Actions:
# - Type a todo item
# - Mark it complete
# - Press Ctrl+C

# Expected output:
# [MCP] Playwright Test MCP integration enabled
# [MCP] Captured X console messages
# [MCP] Captured Y network requests
```

### 2️⃣ Generate Test Script via UI (2 minutes)

```powershell
# 1. Open http://localhost:5173
# 2. Click "Generate Test Script"
# 3. Enter: "Add and complete todo item"
# 4. Click "Generate Preview"
# 5. Review preview → Click "Confirm"
# 6. View generated TypeScript files
```

### 3️⃣ Self-Healing Demo (1 minute)

```powershell
python demo_self_healing.py

# Expected:
# ✅ Test passed after self-healing
```

## 🌐 Service URLs

| Service | URL | Status Check |
|---------|-----|--------------|
| **Frontend UI** | http://localhost:5173 | Open in browser |
| **Backend API** | http://localhost:8001 | `curl http://localhost:8001/health` |
| **API Docs** | http://localhost:8001/docs | Interactive Swagger UI |
| **Copilot Bridge** | http://localhost:3030 | `curl http://localhost:3030/health` |

## 📊 Verify Components

```powershell
# Quick one-liner check
python -c "from app.recorder.mcp_integration import get_playwright_mcp_recorder; from app.generators.agentic_script_agent import AgenticScriptAgent; r = get_playwright_mcp_recorder(); a = AgenticScriptAgent(); print(f'MCP: {r.mcp_available}, Flows: {len(a.list_available_flows())}')"

# Expected: MCP: True, Flows: 0 (or more if you've recorded)
```

## 🛠️ Troubleshooting

### MCPs Not Working
```powershell
# Check MCP config
cat .vscode/mcp.json

# Should show 4 servers: playwright-test, microsoft-docs, github, filesystem
```

### Backend Not Starting
```powershell
# Check if port 8001 is in use
netstat -ano | findstr :8001

# Kill process if needed
taskkill /F /PID <PID>

# Restart backend
python -m uvicorn app.api.main:app --reload --port 8001
```

### Frontend Not Starting
```powershell
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

## 📁 Key Files & Locations

| Component | Location | Purpose |
|-----------|----------|---------|
| **Recorded Flows** | `recordings/<session>/metadata.json` | Recorder output with MCP data |
| **Generated Flows** | `app/generated_flow/*.json` | Processed flows for script generation |
| **MCP Config** | `.vscode/mcp.json` | MCP server configuration |
| **Generated Scripts** | `framework_repos/<repo>/tests/` | Output TypeScript test files |
| **Vector DB** | `./vector_store/` | Chroma database for context |

## 🎯 What Works Now

✅ **Recording**: JS injection + MCP enhancement  
✅ **Script Generation**: Agentic agent with Copilot API  
✅ **Self-Healing**: Runtime locator fixing with MCP  
✅ **Test Case Generation**: Excel test case creation  
✅ **4 MCP Servers**: Playwright, MS Docs, GitHub, Filesystem  
✅ **Copilot Integration**: VS Code Copilot API bridge  

## 📚 Full Documentation

- [STARTUP_VERIFICATION_GUIDE.md](STARTUP_VERIFICATION_GUIDE.md) - Complete startup guide
- [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md) - Full system architecture
- [RECORDER_HYBRID_INTEGRATION.md](RECORDER_HYBRID_INTEGRATION.md) - Recorder details
- [RUNTIME_SELF_HEALING.md](RUNTIME_SELF_HEALING.md) - Self-healing system

---

**Ready?** Run `.\quick_start.bat` to launch everything! 🚀
