# Runtime Self-Healing: How It Works When XPath Is Incorrect

## The Problem You Asked About

**Question**: "If the XPath is incorrect while trial run, how will it work?"

**Answer**: The system now has **automatic self-healing during trial runs** using a 3-step process:

1. **Detect Failure** → Parse Playwright logs to identify failed locators
2. **Capture Page State** → Use Playwright MCP to snapshot the actual page at failure point
3. **Heal & Retry** → Use VS Code Copilot API + Microsoft Docs MCP + generated flows from `app/generated_flow` to generate better locators and retry

---

## Complete Self-Healing Flow

### Step 1: Initial Trial Run (Locators Fail)

```typescript
// ❌ Test with incorrect XPath
test('supplier creation', async ({ page }) => {
  await page.goto('https://fusion.oracle.com/supplier');
  
  // Wrong: Button ID changed from "old-create-btn" to "create-supplier-btn"
  await page.locator('xpath=//button[@id="old-create-btn"]').click();
});
```

**Result**: `TimeoutError: locator xpath=//button[@id="old-create-btn"] not found`

---

### Step 2: Failure Detection & Log Analysis

The `SelfHealingExecutor` automatically:

1. **Parses error logs** using `extract_failed_locators_from_logs()`:
   ```python
   failed_locators = [
       {
           "locator": "xpath=//button[@id='old-create-btn']",
           "type": "xpath",
           "error": "TimeoutError: not found",
           "context": "locator('xpath=//button[@id=\"old-create-btn\"]').click()"
       }
   ]
   ```

2. **Identifies failure type**:
   - ✅ Locator error → Trigger self-healing
   - ❌ Other error (network, assertion) → Return failure

---

### Step 3: Real-Time Page State Capture (Playwright MCP)

The executor opens the **actual page** and captures its current state:

```python
# Use Playwright MCP to capture page snapshot
ui_crawl_data = executor.capture_page_state_on_failure(test_url)
```

**What gets captured**:

#### A. Accessibility Snapshot (Better than Screenshot)
```json
{
  "role": "button",
  "name": "Create Supplier",
  "attributes": {
    "id": "create-supplier-btn",
    "class": "btn btn-primary create-action",
    "aria-label": "Create new supplier",
    "data-testid": "create-supplier"
  },
  "locators": {
    "role": "page.getByRole('button', { name: 'Create Supplier' })",
    "testid": "page.getByTestId('create-supplier')",
    "label": "page.getByLabel('Create new supplier')",
    "xpath": "//button[@id='create-supplier-btn']",
    "css": "button#create-supplier-btn.btn.btn-primary"
  }
}
```

#### B. Console Messages
```json
[
  {
    "type": "error",
    "text": "Button #old-create-btn not found",
    "location": "supplier.js:145"
  }
]
```

#### C. Network Requests
```json
[
  {
    "url": "https://fusion.oracle.com/api/supplier/metadata",
    "status": 200,
    "response": { "create_button_id": "create-supplier-btn" }
  }
]
```

---

### Step 4: Copilot-Powered Self-Healing

The system calls `ask_copilot_to_self_heal()` with:

1. **Failed script** with incorrect locators
2. **Error logs** showing what failed
3. **Real UI crawl data** showing what's actually on the page
4. **Generated flows** from `app/generated_flow` (JSON format) for additional context

#### Copilot Prompt (Simplified)

```
You are fixing a Playwright test with failed locators using VS Code Copilot API.

FAILED LOCATORS:
- xpath=//button[@id="old-create-btn"] → TimeoutError: not found

ACTUAL PAGE STATE:
{
  "role": "button",
  "name": "Create Supplier",
  "attributes": { "id": "create-supplier-btn", ... },
  "locators": {
    "role": "page.getByRole('button', { name: 'Create Supplier' })",
    "testid": "page.getByTestId('create-supplier')"
  }
}

GENERATED FLOWS (from app/generated_flow):
{
  "flow_name": "supplier_creation",
  "steps": [{ "action": "click", "element": "Create button" }]
}

OFFICIAL PATTERNS (Microsoft Docs MCP):
- Prefer: getByRole(), getByLabel(), getByTestId()
- Avoid: XPath unless necessary

Fix the script using the most resilient locator from the page snapshot.
```

#### Copilot Response (Healed Script)

```typescript
// ✅ Healed script with resilient locators
test('supplier creation', async ({ page }) => {
  await page.goto('https://fusion.oracle.com/supplier');
  
  // Fixed: Using resilient role-based locator
  await page.getByRole('button', { name: 'Create Supplier' }).click();
  
  // Fallback: TestId-based locator
  // await page.getByTestId('create-supplier').click();
});
```

---

### Step 5: Automatic Retry with Healed Script

```python
# Run trial with healed script
success, logs = run_trial_in_framework(healed_script, framework_root)

if success:
    # ✅ Test passes! Save the healed script
    executor._save_healed_script(healed_script, "supplier_creation")
```

**Result**: `Test PASSED ✅ on retry attempt 1`

---

## Code Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Initial Trial Run                                        │
│    run_trial_with_real_time_healing(script, url)            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ ❌ Test fails
┌─────────────────────────────────────────────────────────────┐
│ 2. Detect Failure Type                                      │
│    failed_locators = extract_failed_locators_from_logs()    │
│    → ["xpath=//button[@id='old-create-btn']"]               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ ✅ Locator error detected
┌─────────────────────────────────────────────────────────────┐
│ 3. Capture Real Page State (Playwright MCP)                │
│    ui_crawl = capture_page_state_on_failure(url)            │
│    → Opens actual page, captures snapshot + console + net   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ ✅ Page state captured
┌─────────────────────────────────────────────────────────────┐
│ 4. AI Self-Healing (Azure OpenAI + MS Docs)                │
│    healed_script = ask_llm_to_self_heal(                    │
│        failed_script=script,                                │
│        logs=logs,                                           │
│        ui_crawl=ui_crawl                                    │
│    )                                                        │
│    → LLM analyzes failure + real page + official docs       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ ✅ Healed script generated
┌─────────────────────────────────────────────────────────────┐
│ 5. Retry with Healed Script                                │
│    success, logs = run_trial_in_framework(healed_script)    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ↓ ✅ Test passes
┌─────────────────────────────────────────────────────────────┐
│ 6. Save Healed Script                                       │
│    save_healed_script(healed_script, "test_name")           │
│    → Saved to framework_repos/*/tests/                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### Example 1: Basic Self-Healing Trial

```python
from app.self_healing_with_mcp import SelfHealingExecutor
from pathlib import Path

# Initialize executor
executor = SelfHealingExecutor(
    framework_root=Path("./framework_repos/my-framework")
)

# Run with self-healing (max 2 retries)
success, logs, healing_attempts = executor.run_trial_with_real_time_healing(
    script_content=my_test_script,
    test_url="https://fusion.oracle.com/supplier",
    max_retries=2,
    headed=False  # Run headless for CI/CD
)

# Check results
if success:
    print(f"✅ Test passed after {len(healing_attempts)} healing attempts")
else:
    print(f"❌ Test failed even after self-healing")
```

### Example 2: Manual Self-Healing (No Auto-Retry)

```python
from app.self_healing_executor import run_trial_with_self_healing

# Manual control over healing process
success, logs, healing_attempts = run_trial_with_self_healing(
    script_content=test_script,
    framework_root=Path("./framework_repos/my-framework"),
    max_retries=3,  # Try up to 3 times
    headed=True,    # Show browser for debugging
    env_overrides={"DEBUG": "pw:api"}
)

# Detailed healing report
for attempt in healing_attempts:
    print(f"Attempt {attempt['attempt']}:")
    print(f"  Failed locators: {attempt['failed_locators']}")
    print(f"  Healed: {attempt['healed']}")
    print(f"  Changes: {attempt.get('changes', 'N/A')}")
```

### Example 3: Integration with FastAPI

```python
from fastapi import APIRouter, HTTPException
from app.self_healing_with_mcp import SelfHealingExecutor

router = APIRouter()

@router.post("/trial/run-with-healing")
async def run_trial_with_healing(request: TrialRequest):
    """Run trial with automatic self-healing."""
    
    executor = SelfHealingExecutor(
        framework_root=Path(request.framework_root)
    )
    
    success, logs, healing_attempts = executor.run_trial_with_real_time_healing(
        script_content=request.script,
        test_url=request.url,
        max_retries=2
    )
    
    return {
        "success": success,
        "logs": logs,
        "healing_attempts": len(healing_attempts),
        "healed": len(healing_attempts) > 0 and success,
        "details": healing_attempts
    }
```

---

## Key Features

### 1. **Automatic Failure Detection**
- Parses Playwright error logs
- Identifies locator-specific failures
- Distinguishes from network/assertion errors

### 2. **Real-Time Page Capture (Playwright MCP)**
- Opens actual page at failure point
- Captures accessibility snapshot (better than DOM/screenshot)
- Records console messages & network requests
- Extracts all available locator strategies per element

### 3. **Copilot-Powered Healing (Free with Copilot)**
- VS Code Copilot API (integrated with your editor)
- Microsoft Docs MCP for official Playwright patterns
- Generated flows from `app/generated_flow` for context
- Playwright-test-healer methodology
- Generates multiple locator strategies (role, testid, label, xpath)

### 4. **Automatic Retry & Save**
- Retries up to N times with healed scripts
- Saves successful healed scripts to framework
- Creates backup of original scripts
- Returns detailed healing report

---

## Configuration

### Environment Variables

```bash
# VS Code Copilot (no environment variables needed - uses VS Code integration)
# Copilot API is automatically available when signed into VS Code with Copilot subscription

# Optional (for GitHub repo cloning)
GITHUB_TOKEN=ghp_your_github_token

# Generated Flows Directory (default: app/generated_flow)
# This is where recorded flows are stored in JSON format
```

### MCP Servers (Must be running)

```json
// .vscode/mcp.json
{
  "mcpServers": {
    "playwright-test": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-playwright"]
    },
    "microsoft-docs": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-microsoft-docs"]
    }
  }
}
```

---

## Limitations & Trade-offs

### What Works Well ✅
- **Locator failures** (XPath, CSS, role-based)
- **Dynamic content** (IDs/classes that change)
- **Simple page structures** (< 100 elements)
- **Known patterns** (buttons, inputs, dropdowns)

### What Needs Improvement 🔄
- **Complex SPAs** (React/Angular with shadow DOM) → May need multiple retries
- **Iframe/multi-window** → Requires context switching (being added)
- **Dynamic waits** → LLM needs to infer wait conditions
- **Performance** → Each healing cycle takes 10-30 seconds

### Known Edge Cases ⚠️
1. **Non-locator errors** (network, assertion) → No healing attempted
2. **Ambiguous elements** (multiple buttons with same text) → May need manual intervention
3. **Page changes during healing** → Rare, but can cause inconsistencies
4. **Max retries reached** → Test still fails, but provides detailed report

---

## Comparison: Before vs After

### Before (No Self-Healing)
```
Trial Run → ❌ XPath not found → ❌ Test fails → ❌ Manual fix required
```

### After (With Self-Healing)
```
Trial Run → ❌ XPath not found → 🔧 Capture page state → 🤖 Copilot heals locator 
→ ✅ Retry with better locator → ✅ Test passes → 💾 Save healed script
```

---

## Next Steps

1. **Try it**: Run `python -m app.self_healing_with_mcp` to see example
2. **Integrate**: Use `SelfHealingExecutor` in your trial runs
3. **Monitor**: Check healing reports to see common failure patterns
4. **Optimize**: Adjust `max_retries` based on your test complexity

---

## Questions?

- **Q: Does this replace manual test writing?**
  - A: No, but it reduces maintenance when locators break

- **Q: How much does it cost?**
  - A: FREE - included with your VS Code Copilot subscription (no per-request charges)

- **Q: Can I use without MCP?**
  - A: Yes, use `run_trial_with_self_healing()` with fallback UI crawl

- **Q: What if healing fails?**
  - A: You get detailed logs showing what was tried and why it failed

---

## Related Docs

- [MCP_INTEGRATION.md](./MCP_INTEGRATION.md) - Complete MCP setup
- [FREE_SELF_HEALING.md](./FREE_SELF_HEALING.md) - Free healing methodology
- [RECORDER_TO_SCRIPT_FLOW.md](./RECORDER_TO_SCRIPT_FLOW.md) - End-to-end flow
