# 🏗️ Project Architecture Analysis

## Overview

This is an **enterprise-grade test automation platform** with AI-powered test generation, self-healing capabilities, and comprehensive recording features for Oracle Fusion and other web applications.

---

## 1️⃣ MCPs (Model Context Protocols) Used

### Configured MCP Servers (`.vscode/mcp.json`)

| MCP Server | Purpose | Tools Available | Status |
|------------|---------|-----------------|--------|
| **Playwright Test MCP** | Browser automation & test planning | `browser_open`, `browser_click`, `browser_snapshot`, `browser_console_messages`, `browser_network_requests`, `planner_setup_page`, `planner_save_plan`, etc. | ✅ Active |
| **Microsoft Docs MCP** | Official documentation & code samples | `search_docs`, `search_code_samples`, `fetch_doc_page` | ✅ Active |
| **GitHub MCP** | Repository search & code patterns | `search_repositories`, `search_code`, `clone_repository` | ✅ Active |
| **Filesystem MCP** | Safe file operations with backups | `list_directory`, `create_directory`, `safe_write_file`, `read_file` | ✅ Active |

### MCP Client Implementation

**File**: `app/core/mcp_client.py`

```python
class MCPClient:
    """Base class for interacting with MCP servers"""
    
class MicrosoftDocsMCP(MCPClient):
    - search_docs(query, max_results)
    - search_code_samples(query, language)
    - fetch_doc_page(url)

class GitHubMCP(MCPClient):
    - search_repositories(query, max_results)
    - search_code(repo, query, max_results)
    - clone_repository(repo, target_dir)

class FilesystemMCP(MCPClient):
    - list_directory(path, recursive)
    - create_directory(path)
    - safe_write_file(path, content, backup)
    - read_file(path, start_line, end_line)
```

### MCP Integration Points

1. **Test Script Generation** (`app/generators/agentic_script_agent.py`):
   - Uses Microsoft Docs MCP for official Playwright patterns
   - Uses GitHub MCP for code pattern discovery
   - Uses Filesystem MCP for framework repository management

2. **Self-Healing** (`app/self_healing_with_mcp.py`):
   - Uses Playwright MCP for real-time page capture
   - Uses Microsoft Docs MCP for best practices
   - Captures page snapshots, console messages, network requests

3. **Framework Management** (`app/api/framework_resolver.py`):
   - Uses GitHub MCP for repository cloning
   - Uses Filesystem MCP for directory verification

---

## 2️⃣ Agents (Agentic AI Systems)

### Primary Agent: **AgenticScriptAgent**

**Location**: `app/generators/agentic_script_agent.py`

**Purpose**: AI-powered test script generation with framework alignment

**Capabilities**:
```python
class AgenticScriptAgent:
    def __init__(self):
        self.llm = None  # VS Code Copilot API (not Azure OpenAI)
        self.microsoft_docs_mcp = get_microsoft_docs_mcp()
        self.github_mcp = get_github_mcp()
        self.filesystem_mcp = get_filesystem_mcp()
    
    # Core Methods:
    - gather_context(scenario) → context from generated_flow/*.json
    - generate_preview(scenario) → Markdown preview of test steps
    - generate_script_payload(scenario, framework, accepted_preview) → TypeScript files
    - _generate_payload_with_llm() → LLM-based generation
    - _generate_payload_with_templates() → Template-based generation
    - _build_page_based_payload() → Multi-page test structure
    - _build_deterministic_payload() → Fallback deterministic generation
```

**Key Features**:
- **Context Gathering**: Loads flows from `app/generated_flow/*.json` (not vector DB)
- **Preview Generation**: Creates Markdown summaries before generating scripts
- **Multi-Page Support**: Generates separate locator/page files per page title
- **LLM Enhancement**: Uses Copilot API for intelligent code generation
- **Framework Awareness**: Aligns with existing repo structure (locators, pages, tests dirs)
- **Self-Healing Integration**: Generates resilient locators (role, testid, label > xpath)

**Workflow**:
```
User Request (scenario)
    ↓
gather_context(scenario) → Load from app/generated_flow/*.json
    ↓
generate_preview(scenario) → Markdown steps
    ↓
User accepts preview ("confirm")
    ↓
generate_script_payload(scenario, framework, accepted_preview)
    ↓
Generate TypeScript files:
    - locators/<PageTitle>.ts
    - pages/<PageTitle>.pages.ts
    - tests/<flow_name>.spec.ts
```

### Secondary Agent: **TestCaseGenerator**

**Location**: `app/generators/test_case_generator.py`

**Purpose**: Generate manual test cases with Excel integration

**Capabilities**:
```python
class TestCaseGenerator:
    def __init__(self, db, llm, template):
        self.db = VectorDBClient()  # For historical context
        self.llm = CopilotClient() or AzureChatOpenAI()  # Copilot bridge preferred
    
    # Core Methods:
    - generate_test_cases(flow_name) → Excel-ready test cases
    - map_llm_to_template() → Map AI output to Excel columns
    - enrich_with_llm() → Enhance test steps with AI
```

**Key Features**:
- **Excel Integration**: Generates test cases mapped to Excel columns
- **LLM Enrichment**: Uses Copilot API for enhancing test steps
- **Vector DB Query**: Searches historical flows for context
- **Template Mapping**: Maps to standardized Excel template

### Tertiary Agent: **SelfHealingExecutor**

**Location**: `app/self_healing_with_mcp.py`

**Purpose**: Automatic test self-healing during runtime failures

**Capabilities**:
```python
class SelfHealingExecutor:
    def __init__(self, framework_root):
        self.mcp_recorder = PlaywrightMCPRecorder()
    
    # Core Methods:
    - run_trial_with_real_time_healing() → Execute test with auto-healing
    - capture_page_state_on_failure() → Real-time page capture via Playwright MCP
    - _generate_locator_strategies() → Multiple locator options per element
    - _save_healed_script() → Persist healed version
```

**Key Features**:
- **Runtime Healing**: Detects failed locators during test execution
- **Page State Capture**: Uses Playwright MCP to capture real page at failure point
- **Copilot Analysis**: Uses Copilot API + Microsoft Docs to generate better locators
- **Automatic Retry**: Retries test with healed script (max 2-3 attempts)
- **Script Persistence**: Saves healed scripts for future use

**Workflow**:
```
Test execution → ❌ XPath fails
    ↓
extract_failed_locators_from_logs()
    ↓
capture_page_state_on_failure() → Playwright MCP snapshot
    ↓
ask_copilot_to_self_heal() → Copilot API + MS Docs + generated_flow context
    ↓
Retry with healed script → ✅ Test passes
    ↓
save_healed_script()
```

---

## 3️⃣ Agentic AI Components

### 1. **Copilot Bridge Client**

**Location**: `app/core/llm_client_copilot.py`, `app/core/llm_client.py`

**Purpose**: VS Code Copilot API integration

```python
class CopilotClient:
    def __init__(self, temperature=0.2):
        self.bridge_url = f"{COPILOT_BRIDGE_URL}/api/copilot/chat"
    
    def invoke(self, prompt: str) -> CopilotResponse:
        # POST to http://localhost:3030/api/copilot/chat
        # Returns LLM-generated code/fixes
```

**Used By**:
- `AgenticScriptAgent` → Test script generation
- `TestCaseGenerator` → Test case enrichment
- `SelfHealingExecutor` → Locator healing
- `ask_llm_to_self_heal()` → Self-healing function

**Key Functions**:
- `ask_llm_for_script()` → Generate test scripts from prompts
- `ask_llm_to_self_heal()` → Fix failed test locators
- `_ensure_llm()` → Singleton LLM client factory

### 2. **LLM-Enhanced Generator**

**Location**: `app/generators/framework_templates.py`

```python
class LLMEnhancedGenerator:
    def generate_with_llm() → Enhanced test generation with AI
```

### 3. **Recorder Enricher**

**Location**: `app/recorder/recorder_enricher.py`

**Purpose**: Enrich recorded flows with AI-powered insights

**Features**:
- Infers test steps from raw recordings
- Maps actions to test case columns
- Generates expected results
- Enriches with context from generated flows

---

## 4️⃣ Data Sources & Context

### NOT Vector DB (As You Clarified)

❌ **Removed**: Vector DB for self-healing context  
✅ **Using**: Direct file loading from `app/generated_flow/*.json`

### Primary Data Source: `app/generated_flow/`

**Structure**:
```json
{
  "flow_name": "supplier_creation",
  "source": "recorded",
  "steps": [
    {
      "step": 1,
      "action": "click",
      "element": "Create button",
      "navigation": "Navigate to Create Supplier",
      "data": "",
      "expected": "Supplier form opens"
    }
  ]
}
```

**Usage**:
1. **AgenticScriptAgent.gather_context()** → Loads flow data
2. **ask_copilot_to_self_heal()** → Provides context for healing
3. **TestCaseGenerator** → Historical test patterns

### Secondary Data: Vector DB (Still Used for Test Case Generation)

**Location**: `app/core/vector_db.py`

**Used By**:
- `TestCaseGenerator` → Query historical test cases
- `AgenticScriptAgent.gather_context()` → Fallback context if flow file not found

**NOT Used For**:
- Self-healing (uses generated_flow instead)
- Real-time context (uses Playwright MCP)

---

## 5️⃣ Recorder System

### Primary Recorder: `run_playwright_recorder_v2.py`

**Location**: `app/recorder/run_playwright_recorder_v2.py`

**Type**: Playwright-based event recorder with JavaScript injection

**Capabilities**:
```bash
python -m app.recorder.run_playwright_recorder_v2 \
  --url "https://app.com" \
  --capture-dom \
  --capture-screenshots \
  --timeout 60
```

**Captures**:
- **User Actions**: Click, input, change, keydown, scroll, etc.
- **Page Events**: Navigation, DOMContentLoaded, load
- **DOM Snapshots**: Full HTML at each action (optional)
- **Screenshots**: Element-level screenshots (optional)
- **Network HAR**: HTTP archive of all requests
- **Trace**: Playwright trace for debugging
- **Metadata**: `metadata.json` with structured event data

**Key Features**:
- **Multi-window Support**: Handles popups and new tabs
- **Authentication Recording**: Captures OAuth/SSO flows
- **Element Enrichment**: Generates Playwright locators (role, label, text, testid)
- **Sensitive Data Masking**: Redacts passwords/secrets
- **Hybrid Mode**: Lightweight capture (page details + element HTML only)

**Output Structure**:
```
recordings/<session>/
├── metadata.json          # All actions & page events
├── dom/                   # HTML snapshots (if --capture-dom)
│   ├── A-001.html
│   ├── A-002.html
│   └── P-001.html
├── screenshots/           # Screenshots (if --capture-screenshots)
│   ├── A-001.png
│   ├── A-002.png
│   └── P-001.png
├── network.har            # Network capture
└── trace.zip              # Playwright trace
```

### Secondary Recorder: `run_minimal_recorder.py`

**Location**: `app/run_minimal_recorder.py`

**Type**: Minimal CDP-based recorder (fallback)

**Purpose**: Lightweight recording without heavy artifacts

---

## 6️⃣ Complete Architecture Flow

### End-to-End Test Generation Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                            │
│              (Frontend or CLI Command)                         │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────────┐
│ 1. RECORDING PHASE                                             │
│    run_playwright_recorder_v2.py                               │
│                                                                │
│    Captures: Actions → metadata.json                           │
│              DOM → dom/*.html                                  │
│              Screenshots → screenshots/*.png                   │
│              Network → network.har                             │
│              Trace → trace.zip                                 │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────────┐
│ 2. REFINEMENT PHASE                                            │
│    recorder_enricher.py                                        │
│                                                                │
│    - Filter authentication steps                               │
│    - Enrich with locators                                      │
│    - Infer expected results                                    │
│    - Save to app/generated_flow/<name>.json                    │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────────┐
│ 3. CONTEXT GATHERING                                           │
│    AgenticScriptAgent.gather_context()                         │
│                                                                │
│    - Load from app/generated_flow/*.json                       │
│    - Query Microsoft Docs MCP (official patterns)              │
│    - Query GitHub MCP (code examples)                          │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────────┐
│ 4. PREVIEW GENERATION                                          │
│    AgenticScriptAgent.generate_preview()                       │
│                                                                │
│    - Uses Copilot API                                          │
│    - Generates Markdown preview                                │
│    - Returns to user for confirmation                          │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────────┐
│ 5. SCRIPT GENERATION                                           │
│    AgenticScriptAgent.generate_script_payload()                │
│                                                                │
│    - Uses Copilot API + Microsoft Docs MCP                     │
│    - Detects unique page titles from steps                     │
│    - Generates:                                                │
│      • locators/<PageTitle>.ts                                 │
│      • pages/<PageTitle>.pages.ts                              │
│      • tests/<flow_name>.spec.ts                               │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────────┐
│ 6. FRAMEWORK INTEGRATION                                       │
│    framework_resolver.py                                       │
│                                                                │
│    - Detect framework structure using Filesystem MCP           │
│    - Clone repos using GitHub MCP (if needed)                  │
│    - Write files to correct directories                        │
│    - Verify structure alignment                                │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────────┐
│ 7. TRIAL EXECUTION (with Self-Healing)                         │
│    SelfHealingExecutor.run_trial_with_real_time_healing()      │
│                                                                │
│    Run test → Fails? → Capture page (Playwright MCP)           │
│               ↓                                                │
│           ask_copilot_to_self_heal()                           │
│               ↓                                                │
│           Retry with healed script → Passes? → Save            │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────────────────┐
│ 8. FINAL OUTPUT                                                │
│                                                                │
│    ✅ Working test scripts in framework repo                   │
│    ✅ Healed scripts saved for future                          │
│    ✅ Test execution logs                                      │
│    ✅ Excel test cases (optional)                              │
└────────────────────────────────────────────────────────────────┘
```

---

## 7️⃣ Technology Stack

### Backend
- **Python 3.10+**
- **FastAPI** (REST API)
- **Playwright for Python** (browser automation)
- **LangChain** (LLM orchestration - minimal usage)
- **Chroma** (vector DB - for test case context only)
- **Pandas** (Excel generation)

### Frontend
- **React 18** with TypeScript
- **Vite** (build tool)
- **TanStack Query** (React Query)
- **shadcn/ui** (UI components)
- **Tailwind CSS** (styling)

### AI/LLM
- **VS Code Copilot API** (via HTTP bridge at localhost:3030)
- **NOT Azure OpenAI** (as you clarified)
- **Microsoft Docs MCP** (official documentation)

### MCP Ecosystem
- **Playwright Test MCP** (`@modelcontextprotocol/server-playwright`)
- **Microsoft Docs MCP** (`@microsoft/mcp-server-docs`)
- **GitHub MCP** (`@modelcontextprotocol/server-github`)
- **Filesystem MCP** (`@modelcontextprotocol/server-filesystem`)

---

## 8️⃣ Key Differentiators

### What Makes This Platform Unique

1. **100% Free Runtime Self-Healing**
   - Uses VS Code Copilot API (no per-request charges)
   - Playwright MCP for real-time page capture
   - Microsoft Docs MCP for official patterns
   - No paid web search APIs needed

2. **Framework-Aware Generation**
   - Detects existing repo structure
   - Aligns generated code with existing patterns
   - Multi-page test support (one file per page)
   - Automatic directory detection

3. **Multi-Phase Recording**
   - Raw recording → Refinement → Enrichment → Generation
   - Authentication flow filtering
   - Sensitive data masking
   - Multi-window support

4. **Agentic Architecture**
   - AgenticScriptAgent for intelligent code generation
   - SelfHealingExecutor for runtime error recovery
   - TestCaseGenerator for manual test cases
   - All powered by Copilot API (not Azure OpenAI)

5. **MCP-First Design**
   - Official documentation via Microsoft Docs MCP
   - Code patterns via GitHub MCP
   - Safe operations via Filesystem MCP
   - Browser automation via Playwright MCP

---

## 9️⃣ Summary

### MCPs: 4 Active Servers
1. Playwright Test MCP → Browser automation
2. Microsoft Docs MCP → Official documentation
3. GitHub MCP → Code pattern discovery
4. Filesystem MCP → Safe file operations

### Agents: 3 Primary Agents
1. **AgenticScriptAgent** → Test script generation (main)
2. **TestCaseGenerator** → Manual test case generation
3. **SelfHealingExecutor** → Runtime test healing

### Agentic AI: Copilot-Powered
- **VS Code Copilot API** (HTTP bridge at localhost:3030)
- **NOT Azure OpenAI** (as per your correction)
- **Data Source**: `app/generated_flow/*.json` (not vector DB for self-healing)
- **Context**: Microsoft Docs MCP + GitHub MCP + generated flows

### Architecture Pattern
```
Recording → Refinement → Context → Preview → Generation → Integration → Execution → Self-Healing
```

**Cost**: 100% FREE (only requires VS Code Copilot subscription)

---

## 📊 Component Matrix

| Component | Type | Purpose | Data Source | LLM Used |
|-----------|------|---------|-------------|----------|
| `run_playwright_recorder_v2.py` | Recorder | Capture user actions | Browser events | ❌ No |
| `recorder_enricher.py` | Enricher | Refine recordings | metadata.json | ✅ Copilot |
| `AgenticScriptAgent` | Agent | Generate test scripts | generated_flow/*.json | ✅ Copilot |
| `TestCaseGenerator` | Agent | Generate Excel test cases | Vector DB | ✅ Copilot |
| `SelfHealingExecutor` | Agent | Auto-heal failing tests | Playwright MCP | ✅ Copilot |
| `llm_client_copilot.py` | Client | Copilot API bridge | N/A | ✅ Copilot |
| `mcp_client.py` | Client | MCP server integration | MCP servers | ❌ No |

---

This architecture enables **enterprise-grade test automation with AI-powered generation and self-healing**, all using free/low-cost tools (VS Code Copilot + MCP servers).
