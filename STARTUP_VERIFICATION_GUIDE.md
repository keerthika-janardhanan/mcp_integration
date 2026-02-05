# 🚀 Startup & Verification Guide

Complete guide to start all components and verify MCPs, agents, and recorder are working.

---

## 📋 Prerequisites Check

Run these commands first to verify dependencies:

```powershell
# 1. Python environment
python --version  # Should be 3.10+

# 2. Node.js (for MCP servers)
node --version    # Should be 18+
npx --version

# 3. Playwright browsers installed
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# 4. Required Python packages
python -c "import fastapi, playwright, chromadb; print('Core packages OK')"

# 5. VS Code Copilot bridge (optional but recommended)
# Should be running at http://localhost:3030
```

---

## 🔧 Step 1: Verify MCP Configuration

Check that all 4 MCP servers are configured:

```powershell
# Check MCP config file exists
cat .vscode/mcp.json

# Expected output should show:
# - playwright-test
# - microsoft-docs
# - github
# - filesystem
```

### Verify MCP Availability

```powershell
# Test MCP client
python -c "from app.core.mcp_client import MCPClient; print('MCP Client OK')"

# Test Playwright MCP recorder
python -c "from app.recorder.mcp_integration import get_playwright_mcp_recorder; r = get_playwright_mcp_recorder(); print(f'MCP Available: {r.mcp_available}')"
```

**Expected Output**:
```
MCP Client OK
MCP Available: True
```

---

## 🎯 Step 2: Start Backend API

Open a new PowerShell terminal:

```powershell
# Navigate to project root
cd C:\Users\2218532\PycharmProjects\mcp_integration

# Start FastAPI server
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8001

# Or use the batch file:
.\start.bat
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify Backend**:
```powershell
# In another terminal
curl http://localhost:8001/health

# Expected: {"status":"ok"}
```

---

## 🎨 Step 3: Start Frontend UI

Open a new PowerShell terminal:

```powershell
# Navigate to frontend
cd C:\Users\2218532\PycharmProjects\mcp_integration\frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

**Expected Output**:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

**Verify Frontend**:
Open browser to: http://localhost:5173

---

## 🔍 Step 4: Verify Components

### 4.1 Test MCP Servers

```powershell
# Test each MCP server independently

# 1. Playwright Test MCP
python -c "from app.core.mcp_client import MCPClient; client = MCPClient('playwright-test'); print('Playwright MCP: OK' if client else 'FAIL')"

# 2. Microsoft Docs MCP
python -c "from app.core.mcp_client import get_microsoft_docs_mcp; mcp = get_microsoft_docs_mcp(); result = mcp.search_docs('playwright locators'); print(f'MS Docs MCP: {len(result)} results')"

# 3. GitHub MCP
python -c "from app.core.mcp_client import get_github_mcp; mcp = get_github_mcp(); print('GitHub MCP: OK')"

# 4. Filesystem MCP
python -c "from app.core.mcp_client import get_filesystem_mcp; mcp = get_filesystem_mcp(); print('Filesystem MCP: OK')"
```

### 4.2 Test Copilot Bridge

```powershell
# Check if VS Code Copilot bridge is running
curl http://localhost:3030/health

# Test Copilot API
python -c "from app.core.llm_client_copilot import CopilotClient; client = CopilotClient(); response = client.invoke('Say hello'); print(f'Copilot: {response.content[:50]}')"
```

**Expected Output**:
```
Copilot: Hello! How can I help you today?
```

### 4.3 Test Agentic Script Agent

```powershell
# Test AgenticScriptAgent initialization
python -c "from app.generators.agentic_script_agent import AgenticScriptAgent; agent = AgenticScriptAgent(); print(f'Agent initialized: {agent is not None}')"

# Test context gathering (requires generated_flow files)
python -c "from app.generators.agentic_script_agent import AgenticScriptAgent; agent = AgenticScriptAgent(); flows = agent.list_available_flows(); print(f'Available flows: {len(flows)}')"
```

### 4.4 Test Test Case Generator

```powershell
# Test TestCaseGenerator initialization
python -c "from app.generators.test_case_generator import TestCaseGenerator; from app.core.vector_db import VectorDBClient; db = VectorDBClient(); gen = TestCaseGenerator(db=db, template={}); print('TestCaseGenerator: OK')"
```

---

## 🎬 Step 5: End-to-End Workflow Tests

### Test 1: Recording with MCP Integration

```powershell
# Start recorder with MCP enhancement
python -m app.recorder.run_playwright_recorder_v2 \
  --url "https://example.com" \
  --session-name mcp-test \
  --timeout 30 \
  --capture-dom \
  --capture-screenshots

# Expected output should include:
# [MCP] Playwright Test MCP integration enabled
# [recorder] Press 'P' to pause/resume recording...
# [recorder] Press Ctrl+C to finalize...
```

**Actions to Perform**:
1. Wait for page to load
2. Click a button
3. Type in an input field
4. Press Ctrl+C to stop

**Expected MCP Enhancements**:
```
[MCP] Captured 3 console messages
[MCP] Captured 15 network requests
[recorder] Metadata saved to recordings/mcp-test/metadata.json
```

**Verify Metadata**:
```powershell
# Check metadata.json has MCP data
cat recordings/mcp-test/metadata.json | Select-String "mcp_enhanced"

# Should show: "mcp_enhanced": true
```

---

### Test 2: Generate Test Script with Agentic Agent

```powershell
# Test preview generation
python -c "
from app.generators.agentic_script_agent import AgenticScriptAgent
agent = AgenticScriptAgent()

# Generate preview
scenario = 'Create a new supplier with name and email'
preview = agent.generate_preview(scenario)
print('Preview:', preview)
"

# Test full script generation (requires accepting preview)
# Use the React UI at http://localhost:5173 for interactive workflow
```

**In React UI**:
1. Go to "Generate Test Script" page
2. Enter scenario: "Create supplier"
3. Click "Generate Preview"
4. Review Markdown preview
5. Click "Confirm & Generate Script"
6. Verify TypeScript files generated

---

### Test 3: Self-Healing Execution

```powershell
# Test self-healing with demo script
python demo_self_healing.py

# Expected output:
# [SelfHealing] Running trial: demo_test.spec.ts
# [SelfHealing] Test failed - analyzing failures...
# [SelfHealing] Detected failed locator: button.submit
# [SelfHealing] Asking Copilot for healing...
# [SelfHealing] Healed locator: page.getByRole('button', { name: 'Submit' })
# [SelfHealing] Retrying with healed script...
# [SelfHealing] Test passed! ✅
```

---

## 🧪 Comprehensive Health Check Script

Create and run this comprehensive test:

```powershell
# Save as: check_health.py
python check_health.py
```

<details>
<summary>check_health.py (Click to expand)</summary>

```python
"""Comprehensive health check for all MCPs and agents."""
import sys
from pathlib import Path

def check(name, func):
    """Run a check and report status."""
    try:
        result = func()
        print(f"✅ {name}: {result}")
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

def main():
    print("=" * 60)
    print("🔍 MCP Integration Health Check")
    print("=" * 60)
    
    results = []
    
    # 1. MCP Servers
    print("\n📡 MCP Servers:")
    results.append(check("MCP Client", lambda: __import__('app.core.mcp_client', fromlist=['MCPClient']) and "OK"))
    results.append(check("Playwright MCP", lambda: __import__('app.recorder.mcp_integration', fromlist=['get_playwright_mcp_recorder']).get_playwright_mcp_recorder().mcp_available))
    
    try:
        from app.core.mcp_client import get_microsoft_docs_mcp
        results.append(check("Microsoft Docs MCP", lambda: get_microsoft_docs_mcp() and "OK"))
    except:
        results.append(check("Microsoft Docs MCP", lambda: None))
    
    # 2. Copilot Bridge
    print("\n🤖 Copilot Bridge:")
    try:
        from app.core.llm_client_copilot import CopilotClient
        client = CopilotClient()
        results.append(check("Copilot Client", lambda: "OK"))
    except Exception as e:
        results.append(check("Copilot Client", lambda: None))
    
    # 3. Agents
    print("\n🎯 Agentic Components:")
    try:
        from app.generators.agentic_script_agent import AgenticScriptAgent
        agent = AgenticScriptAgent()
        flows = agent.list_available_flows()
        results.append(check("AgenticScriptAgent", lambda: f"{len(flows)} flows available"))
    except Exception as e:
        results.append(check("AgenticScriptAgent", lambda: None))
    
    try:
        from app.generators.test_case_generator import TestCaseGenerator
        from app.core.vector_db import VectorDBClient
        db = VectorDBClient()
        gen = TestCaseGenerator(db=db, template={})
        results.append(check("TestCaseGenerator", lambda: "OK"))
    except Exception as e:
        results.append(check("TestCaseGenerator", lambda: None))
    
    try:
        from app.self_healing_with_mcp import SelfHealingExecutor
        executor = SelfHealingExecutor(".")
        results.append(check("SelfHealingExecutor", lambda: "OK"))
    except Exception as e:
        results.append(check("SelfHealingExecutor", lambda: None))
    
    # 4. Recorder
    print("\n📹 Recorder:")
    try:
        from app.recorder.run_playwright_recorder_v2 import RecorderSession
        results.append(check("Recorder", lambda: "OK"))
    except Exception as e:
        results.append(check("Recorder", lambda: None))
    
    # 5. Data Sources
    print("\n💾 Data Sources:")
    generated_flows = Path("app/generated_flow")
    if generated_flows.exists():
        flow_files = list(generated_flows.glob("*.json"))
        results.append(check("Generated Flows", lambda: f"{len(flow_files)} files"))
    else:
        results.append(check("Generated Flows", lambda: None))
    
    try:
        from app.core.vector_db import VectorDBClient
        db = VectorDBClient()
        count = db.count()
        results.append(check("Vector DB", lambda: f"{count} documents"))
    except Exception as e:
        results.append(check("Vector DB", lambda: None))
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"📊 Results: {passed}/{total} checks passed ({passed*100//total}%)")
    print("=" * 60)
    
    if passed == total:
        print("✅ All systems operational!")
        sys.exit(0)
    elif passed >= total * 0.7:
        print("⚠️  Most systems operational (some optional features unavailable)")
        sys.exit(0)
    else:
        print("❌ Critical issues detected")
        sys.exit(1)

if __name__ == "__main__":
    main()
```
</details>

---

## 🎮 Interactive Testing Workflow

### Complete End-to-End Test

```powershell
# 1. Start all services (3 terminals)

# Terminal 1: Backend
python -m uvicorn app.api.main:app --reload --port 8001

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Testing commands
```

### Workflow Test Sequence

```powershell
# Terminal 3:

# Step 1: Record a flow
python -m app.recorder.run_playwright_recorder_v2 \
  --url "https://demo.playwright.dev/todomvc" \
  --session-name todo-test \
  --capture-dom

# Actions: Add a todo item, mark it complete, press Ctrl+C

# Step 2: Verify recording has MCP data
python -c "
import json
with open('recordings/todo-test/metadata.json') as f:
    data = json.load(f)
    actions = data.get('actions', [])
    mcp_count = sum(1 for a in actions if a.get('mcp_enhanced'))
    print(f'Actions: {len(actions)}, MCP Enhanced: {mcp_count}')
    print(f'Console Messages: {data.get(\"artifacts\", {}).get(\"mcp_console_messages\", 0)}')
    print(f'Network Requests: {data.get(\"artifacts\", {}).get(\"mcp_network_requests\", 0)}')
"

# Step 3: Generate test script via UI
# Go to http://localhost:5173
# Enter scenario: "Add and complete a todo item"
# Generate preview → Confirm → View generated scripts

# Step 4: Run generated script
cd framework_repos/<your-repo>
npx playwright test tests/todo-test.spec.ts

# Step 5: Test self-healing (intentionally break a locator)
# Edit the test to use wrong selector
# Run with self-healing
python -c "
from app.self_healing_with_mcp import SelfHealingExecutor
executor = SelfHealingExecutor('framework_repos/<your-repo>')
result = executor.run_trial_with_real_time_healing('tests/todo-test.spec.ts')
print(f'Result: {result}')
"
```

---

## 📊 Expected Success Indicators

### ✅ All Working Correctly

You should see:

1. **MCP Integration**:
   - `[MCP] Playwright Test MCP integration enabled` in recorder
   - `mcp_enhanced: true` in metadata.json
   - Console messages and network requests captured

2. **Agentic Script Generation**:
   - Preview generates in < 5 seconds
   - Full script generates TypeScript files
   - Files aligned to framework structure (locators/, pages/, tests/)

3. **Self-Healing**:
   - Failed tests automatically detect issues
   - Copilot API suggests fixes
   - Retry succeeds with healed locators

4. **UI**:
   - All pages load without errors
   - "Generate Test Script" flow completes
   - "View Recordings" shows metadata

---

## 🔧 Troubleshooting

### MCP Not Available

```powershell
# Check MCP config
cat .vscode/mcp.json

# Verify Node.js and npx
node --version
npx --version

# Test manual MCP call
npx @modelcontextprotocol/server-playwright --help
```

### Copilot Bridge Not Running

```powershell
# Check if bridge is running
curl http://localhost:3030/health

# Start bridge (if you have vscode-copilot-bridge)
cd vscode-copilot-bridge
npm run dev
```

### Recording Not Enhanced

Check logs:
```powershell
# Run recorder with verbose logging
$env:PYTHONWARNINGS="default"
python -m app.recorder.run_playwright_recorder_v2 --url "https://example.com" --session-name debug-test

# Should show MCP debug messages
```

### Script Generation Fails

```powershell
# Check generated_flow directory
ls app/generated_flow/

# Verify flows exist
python -c "from app.generators.agentic_script_agent import AgenticScriptAgent; agent = AgenticScriptAgent(); print(agent.list_available_flows())"
```

---

## 🎯 Quick Verification Commands

Copy-paste these for rapid health check:

```powershell
# One-liner health check
python -c "from app.recorder.mcp_integration import get_playwright_mcp_recorder; from app.generators.agentic_script_agent import AgenticScriptAgent; from app.core.llm_client_copilot import CopilotClient; r = get_playwright_mcp_recorder(); a = AgenticScriptAgent(); c = CopilotClient(); print(f'MCP: {r.mcp_available}, Flows: {len(a.list_available_flows())}, Copilot: {c is not None}')"

# Backend health
curl http://localhost:8001/health

# Frontend health
curl http://localhost:5173

# Run comprehensive check
python check_health.py
```

---

## 📖 What Each Component Does

| Component | Purpose | Port/Location | Status Check |
|-----------|---------|---------------|--------------|
| **FastAPI Backend** | REST API for agents | 8001 | `curl http://localhost:8001/health` |
| **React Frontend** | UI for test generation | 5173 | `curl http://localhost:5173` |
| **Playwright MCP** | Browser automation | N/A (MCP) | `python -c "from app.recorder.mcp_integration import get_playwright_mcp_recorder; print(get_playwright_mcp_recorder().mcp_available)"` |
| **Microsoft Docs MCP** | Documentation | N/A (MCP) | `python -c "from app.core.mcp_client import get_microsoft_docs_mcp; print(get_microsoft_docs_mcp())"` |
| **GitHub MCP** | Code patterns | N/A (MCP) | `python -c "from app.core.mcp_client import get_github_mcp; print(get_github_mcp())"` |
| **Filesystem MCP** | File operations | N/A (MCP) | `python -c "from app.core.mcp_client import get_filesystem_mcp; print(get_filesystem_mcp())"` |
| **Copilot Bridge** | LLM API | 3030 | `curl http://localhost:3030/health` |
| **AgenticScriptAgent** | Test generation | N/A (Python) | `python -c "from app.generators.agentic_script_agent import AgenticScriptAgent; print(AgenticScriptAgent())"` |
| **Recorder** | User action capture | N/A (CLI) | `python -m app.recorder.run_playwright_recorder_v2 --help` |
| **Vector DB** | Context storage | N/A (Chroma) | `python -c "from app.core.vector_db import VectorDBClient; db = VectorDBClient(); print(db.count())"` |

---

## 🚀 Ready to Go?

If all checks pass, you're ready to:

1. **Record flows**: Use recorder with MCP enhancement
2. **Generate scripts**: Use agentic agent via UI
3. **Self-heal tests**: Run with automatic fixing
4. **Generate test cases**: Create Excel test cases

**Next Steps**: Try the complete end-to-end workflow in the "Interactive Testing Workflow" section above! 🎉
