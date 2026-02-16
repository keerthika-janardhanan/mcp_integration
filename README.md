# Test Automation Platform with MCP Integration

Enterprise-grade test automation platform with AI-powered test generation, self-healing capabilities, and comprehensive recording features.

## 🚀 Key Features

### Core Capabilities
- **AI-Powered Test Generation**: Generate Playwright test scripts from recorded flows
- **Self-Healing Tests**: Automatically fix failing locators using AI and web search
- **Smart Recorder**: Record user interactions with enriched metadata
- **Trace Analysis**: Compare captured actions vs actual browser events to diagnose missing steps
- **Enhanced MutationObserver**: Capture programmatic DOM changes (checkboxes, buttons, custom components)
- **Vector Database**: Intelligent context retrieval for test generation
- **Multi-Framework Support**: Playwright, Cypress, Selenium
- **Excel Integration**: Generate manual test cases with data mapping

### MCP Integrations (New!)
- **Microsoft Docs MCP**: Official Playwright documentation and code samples
- **GitHub MCP**: Search repositories for test patterns
- **Filesystem MCP**: Safe file operations with automatic backups
- **Playwright Test MCP**: Browser automation and test generation

**Self-Healing**: Uses playwright-test-healer agent methodology (100% FREE)

## 📋 Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for MCP servers and frontend)
- **Git**
- **Playwright browsers** (installed via script)

## 🛠️ Quick Setup

### 1. Clone Repository

```powershell
git clone <repository-url>
cd mcp_integration
```

### 2. Setup Python Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate (Windows)
.\\venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Setup MCP Servers

```powershell
# Run the automated setup script
.\\setup_mcp.bat
```

This script will:
- Verify Node.js installation
- Install all MCP servers
- Create `.env` from template
- Verify MCP configuration

### 4. Configure Environment Variables

Edit `.env` and add your API keys:

```env
# Required for GitHub operations
GITHUB_TOKEN=your_github_personal_access_token

# Required for AI test generation
AZURE_OPENAI_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

**Get API Keys:**
- GitHub Token: https://github.com/settings/tokens (scopes: `repo`, `read:org`)
- Azure OpenAI: https://portal.azure.com/

**Note:** Self-healing uses playwright-test-healer agent methodology - no web search API needed!

### 5. Install Playwright Browsers

```powershell
playwright install chromium firefox webkit
```

### 6. Setup Frontend

```powershell
cd frontend
npm install
cd ..
```

## 🎯 Running the Application

### Start Backend

```powershell
cd app/api
uvicorn main:app --reload --port 8001
```

Backend runs at: http://localhost:8001

### Start Frontend

```powershell
cd frontend
npm run dev
```

Frontend runs at: http://localhost:5173

## 📖 Usage Examples

### 1. Record User Flow

```powershell
python -m app.recorder.run_playwright_recorder_v2 --url "https://example.com" --capture-dom --timeout 60
```

Press `Ctrl+C` to stop recording. Output saved to `recordings/<session-name>/`

### 2. Generate Test Scripts

Via UI:
1. Navigate to http://localhost:5173
2. Click "Start Recording"
3. Perform actions on target website
4. Stop recording
5. Generate automation scripts or manual test cases

### 3. Self-Healing Tests (Runtime)

**Automatic self-healing during trial runs** - when XPath/locators fail:

```python
from app.self_healing_with_mcp import SelfHealingExecutor
from pathlib import Path

# Initialize executor
executor = SelfHealingExecutor(framework_root=Path("./framework_repos/my-framework"))

# Run with automatic self-healing (up to 2 retries)
success, logs, healing_attempts = executor.run_trial_with_real_time_healing(
    script_content=my_test_script,
    test_url="https://app.com/page",
    max_retries=2,
    headed=False
)

if success:
    print(f"✅ Test passed after {len(healing_attempts)} healing attempts")
```

**How it works**:
1. **Test fails** with incorrect XPath/locator → Detected automatically
2. **Playwright MCP captures** real page state at failure point
3. **Copilot analyzes** failed vs actual elements using Microsoft Docs MCP + generated flows from `app/generated_flow`
4. **Generates better locators** (role-based, testid, label - resilient patterns)
5. **Retries automatically** with healed script → Test passes ✅
6. **Saves healed script** for future use

**Cost**: 100% FREE (included with VS Code Copilot subscription)

**See**: [docs/RUNTIME_SELF_HEALING.md](docs/RUNTIME_SELF_HEALING.md) for complete guide

### 4. Trace Analysis (Diagnose Missing Actions)

**Compare recorded actions with Playwright trace** to identify missing steps:

```powershell
# 1. Record with trace enabled (default)
python -m app.recorder.run_playwright_recorder_v2 --url "https://example.com" --timeout 60

# 2. Analyze the recording
python -m app.recorder.trace_analyzer recordings/<session_name>

# 3. View trace in Playwright Inspector
playwright show-trace recordings/<session_name>/trace.zip
```

**Sample Output:**
```
📊 Summary:
  - Trace events: 45
  - Recorded actions: 42
  - Missing events: 3
  - Coverage: 93.3%

❌ Missing Events:
  1. Type: click → Selector: button[data-testid="submit"]
  2. Type: fill → Selector: input#email
  3. Type: check → Selector: input[type="checkbox"]#terms
```

**See**: [docs/TRACE_ANALYSIS.md](docs/TRACE_ANALYSIS.md) for complete guide

### 5. Vector Database Operations

```powershell
# Query the vector DB
python -m app.core.vector_db query "Create Supplier" --top-k 5

# List stored documents
python -m app.core.vector_db list --limit 50
```

## 🔧 MCP Integration Details

### Microsoft Docs MCP

**Purpose:** Official Playwright documentation and code samples

```python
from app.core.mcp_client import get_microsoft_docs_mcp

docs_mcp = get_microsoft_docs_mcp()

# Search documentation
results = docs_mcp.search_docs("Playwright locators")

# Get code samples
samples = docs_mcp.search_code_samples("getByRole", language="typescript")
```

### Self-Healing with Playwright Test Healer

**Purpose:** Systematic debugging using playwright-test-healer methodology (FREE)

The system uses the playwright-test-healer agent approach:
1. Analyze error logs systematically
2. Use Microsoft Docs for official best practices
3. Generate resilient locators from UI crawl data
4. Apply proven debugging patterns

No web search API needed - all free tools!

### GitHub MCP

**Purpose:** Repository management and code search

```python
from app.core.mcp_client import get_github_mcp

github = get_github_mcp()

# Search code
code_results = github.search_code("playwright locators")

# Clone repository
github.clone_repository(repo_url, target_path)
```

See [MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) for complete documentation.

## 🏗️ Project Structure

```
mcp_integration/
├── app/
│   ├── api/                    # FastAPI backend
│   ├── core/                   # Core utilities
│   │   ├── llm_client.py      # LLM integration (self-healing)
│   │   ├── mcp_client.py      # MCP server clients
│   │   ├── vector_db.py       # Vector database
│   │   └── browser_utils.py   # Browser utilities
│   ├── generators/             # Test generation
│   │   └── agentic_script_agent.py  # AI script generation
│   ├── recorder/               # Recording module
│   │   ├── run_playwright_recorder_v2.py
│   │   └── mcp_integration.py # Recorder MCP integration
│   ├── ingestion/              # Data ingestion
│   └── services/               # Business logic
├── frontend/                   # React UI
├── docs/                       # Documentation
│   └── MCP_INTEGRATION.md     # MCP integration guide
├── recordings/                 # Recording output
├── framework_repos/           # Cloned test frameworks
├── .vscode/
│   └── mcp.json               # MCP server configuration
├── .env.template              # Environment variables template
├── setup_mcp.bat              # MCP setup script
└── requirements.txt           # Python dependencies
```

## 🧪 Running Tests

```powershell
# Run all tests
python -m pytest -q

# Run specific test file
python -m pytest app/tests/test_vector_db.py -v

# Run with coverage
python -m pytest --cov=app --cov-report=html
```

## 📊 Key Workflows

### Workflow 1: Recording → Manual Test Cases

1. Start recorder with UI or CLI
2. Perform actions on target application
3. Stop recording (metadata saved)
4. Click "Generate Manual Test Cases"
5. Download Excel with test cases

### Workflow 2: Recording → Automation Scripts

1. Start recorder
2. Perform actions
3. Stop recording
4. Provide Git repository URL
5. System generates:
   - Page objects
   - Locator files
   - Test scripts
6. Review preview
7. Push to repository

### Workflow 3: Self-Healing Failed Tests (100% FREE)

1. Test execution fails
2. System captures error logs
3. Consults Microsoft Docs for best practices
4. Analyzes UI crawl data
5. Uses playwright-test-healer methodology
6. Generates fixed locators
7. Updates locator cache

**No paid APIs required!**

## 🔍 Troubleshooting

### MCP Server Not Found

```
Error: npx: command not found
```

**Solution:** Install Node.js from https://nodejs.org/

### GitHub Rate Limit

```
Error: GitHub API rate limit exceeded
```

**Solution:** Add `GITHUB_TOKEN` to `.env` file

### Import Errors

```
ModuleNotFoundError: No module named 'app.core.mcp_client'
```

**Solution:** Ensure you're running from the project root and virtual environment is activated

## 📚 Documentation

### Core Docs
- [MCP Integration Guide](docs/MCP_INTEGRATION.md) - Complete MCP setup and usage
- [Runtime Self-Healing](docs/RUNTIME_SELF_HEALING.md) - How incorrect XPath gets fixed automatically ⭐
- [Trace Analysis](docs/TRACE_ANALYSIS.md) - Diagnose missing recorder actions with Playwright trace ⭐
- [Trace Analysis Quick Ref](docs/TRACE_ANALYSIS_QUICK_REF.md) - Quick reference for trace analysis
- [Self-Healing Flow Diagram](docs/self_healing_flow.md) - Visual guide to self-healing process
- [Free Self-Healing Methodology](docs/FREE_SELF_HEALING.md) - Free approach without paid APIs

### API & Development
- [API Contract](docs/api_contract.md) - Backend API endpoints
- [FastAPI Server](docs/fastapi_server.md) - Server architecture
- [Deployment Runbook](docs/deployment_runbook.md) - Production deployment

### Recording & Testing
- [Recorder to Script Flow](docs/RECORDER_TO_SCRIPT_FLOW.md) - End-to-end recording workflow
- [Test Data Mapping UI](docs/TEST_DATA_MAPPING_UI.md) - Excel test case generation
- [Agentic Test Script Engineer](docs/AGENTIC_TEST_SCRIPT_ENGINEER.md) - AI agent architecture

## 🎯 Quick Reference

### Runtime Self-Healing Commands

```python
# Basic self-healing trial
from app.self_healing_with_mcp import SelfHealingExecutor

executor = SelfHealingExecutor(framework_root=Path("./my-framework"))
success, logs, attempts = executor.run_trial_with_real_time_healing(
    script_content=test_script,
    test_url="https://app.com",
    max_retries=2
)

# Check if healing was successful
if success and attempts:
    print(f"✅ Healed after {len(attempts)} attempts")
```

### Manual Self-Healing (No Auto-Retry)

```python
from app.self_healing_executor import run_trial_with_self_healing

success, logs, attempts = run_trial_with_self_healing(
    script_content=script,
    framework_root=Path("./framework"),
    max_retries=3,
    headed=True  # Show browser for debugging
)
```

### MCP Client Usage

```python
from app.core.mcp_client import (
    get_microsoft_docs_mcp,
    get_github_mcp,
    get_filesystem_mcp
)

# Search official Playwright docs
docs_mcp = get_microsoft_docs_mcp()
results = docs_mcp.search_docs("getByRole selector")

# Find test patterns in GitHub
github_mcp = get_github_mcp()
patterns = github_mcp.search_code("microsoft/playwright", "page.getByRole")

# Safe file operations
fs_mcp = get_filesystem_mcp()
fs_mcp.safe_write_file(Path("test.spec.ts"), content, backup=True)
```

- [MCP Integration Guide](docs/MCP_INTEGRATION.md)
- [Agentic Test Script Engineer](docs/AGENTIC_TEST_SCRIPT_ENGINEER.md)
- [Recorder to Script Flow](docs/RECORDER_TO_SCRIPT_FLOW.md)
- [API Contract](docs/api_contract.md)
- [Test Data Mapping](docs/TEST_DATA_MAPPING_UI.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is proprietary software for enterprise use.

## 🙏 Acknowledgments

- **Playwright** - Browser automation framework
- **Claude AI** - AI-powered test generation
- **Model Context Protocol** - MCP integrations
- **FastAPI** - Backend framework
- **React** - Frontend framework
