# Self-Healing Trial Executor

Automatic error detection and fixing for Playwright test execution with up to 5 retry attempts.

## Features

- **Automatic Error Detection**: Identifies common error types from execution logs
- **Smart Fixes**: Applies targeted fixes for import errors, export errors, syntax issues
- **Progressive Retry**: Up to 5 attempts with fixes applied between each run
- **MCP Integration**: Uses Copilot LLM for complex error resolution
- **Detailed Logging**: Tracks all attempts and fixes applied

## Supported Error Types

### 1. Export Errors
**Pattern**: `is not a constructor`, `has no exported member`

**Fix**: Automatically adds `export default ClassName;` at the end of page classes

**Example**:
```typescript
// Before (broken)
class LoginPage {
  constructor(page) { ... }
}

// After (fixed)
class LoginPage {
  constructor(page) { ... }
}

export default LoginPage;
```

### 2. Import Errors
**Pattern**: `Cannot find module`, `Module not found`

**Fix**: Adds `.ts` extensions to import paths

**Example**:
```typescript
// Before (broken)
import LoginPage from '../pages/LoginPage';

// After (fixed)
import LoginPage from '../pages/LoginPage.ts';
```

### 3. Locator Errors
**Pattern**: `locator not found`, `Timeout exceeded`

**Fix**: LLM generates resilient multi-attribute selectors

### 4. Type Errors
**Pattern**: `Type '...' is not assignable to type`

**Fix**: LLM corrects type annotations and interfaces

### 5. Syntax Errors
**Pattern**: `SyntaxError`, `Unexpected token`

**Fix**: LLM fixes syntax issues

## Usage

### Via API (Recommended)

#### Option 1: Trial Run with Self-Healing (Default)
```bash
POST /api/agentic/trial-run
{
  "testFileContent": "...",
  "frameworkRoot": "/path/to/repo",
  "headed": false,
  "selfHealing": true  // Default: true
}
```

**Response**:
```json
{
  "success": true,
  "logs": "[self-healing] Fixed after 2 attempts\n[self-healing] Fixes applied:\n  - Attempt 1: Added export default statements (Error: export_error)\n...",
  "updateInfo": null
}
```

#### Option 2: Dedicated Self-Healing Endpoint
```bash
POST /api/trial/run-with-healing
{
  "code": "...",
  "frameworkRoot": "/path/to/repo",
  "headed": false
}
```

**Response**:
```json
{
  "success": true,
  "logs": "...",
  "attempts": 2,
  "fixes_applied": [
    {
      "attempt": 1,
      "error_type": "export_error",
      "error_details": {...},
      "fix_description": "Added export default statements"
    }
  ],
  "final_content": "... fixed code ..."
}
```

### Via Python

```python
from pathlib import Path
from app.self_healing_trial_executor import execute_trial_with_self_healing

result = execute_trial_with_self_healing(
    script_content=typescript_code,
    framework_root=Path("/path/to/repo"),
    headed=False,
)

if result["success"]:
    print(f"✓ Success after {result['attempts']} attempts")
    print(f"Fixes: {result['fixes_applied']}")
else:
    print(f"✗ Failed after {result['attempts']} attempts")
    print(result["error"])
```

## Configuration

### Max Retries
Default: 5 attempts

Modify in `self_healing_trial_executor.py`:
```python
class SelfHealingTrialExecutor:
    MAX_RETRIES = 5  # Change this
```

### Error Patterns
Add custom error detection patterns in `ERROR_PATTERNS` dict:
```python
ERROR_PATTERNS = {
    "custom_error": r"(your|regex|pattern)",
    ...
}
```

### LLM Temperature
Lower temperature = more deterministic fixes

```python
executor = SelfHealingTrialExecutor(
    llm_client=CopilotClient(temperature=0.1)  # 0.0 - 1.0
)
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  1. Execute Test                                            │
│     └── Run Playwright test with current code              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                     ┌────────┐
                     │Success?│
                     └────────┘
                          │
                 ┌────────┴────────┐
                 │                 │
                YES               NO
                 │                 │
                 ▼                 ▼
          ┌──────────┐    ┌───────────────┐
          │  Return  │    │ Detect Error  │
          │  Result  │    │     Type      │
          └──────────┘    └───────────────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │  Apply Fix    │
                          │  (Quick or    │
                          │   LLM-based)  │
                          └───────────────┘
                                  │
                                  ▼
                          ┌───────────────┐
                          │  Retry < 5?   │
                          └───────────────┘
                                  │
                         ┌────────┴────────┐
                        YES               NO
                         │                 │
                         ▼                 ▼
                   (Loop back)     ┌──────────────┐
                                   │Return failure│
                                   │with all logs │
                                   └──────────────┘
```

## Example Output

```
[self-healing] Attempt 1/5
$ playwright test tests/tmpt6sfzyef.spec.ts --headed
(cwd=/repo)

TypeError: _WorkdaySignInPage.default is not a constructor
  at tests/tmpt6sfzyef.spec.ts:28:25

[self-healing] Detected error: export_error
[self-healing] Applied fix: Added export default statements

================================================================================
[self-healing] Attempt 2/5
$ playwright test tests/tmpt6sfzyef.spec.ts --headed
(cwd=/repo)

Running 1 test using 1 worker
  ✓ workday444 › workday444 (15.2s)

1 passed (16.3s)

[self-healing] ✓ Success on attempt 2
```

## Troubleshooting

### LLM Not Fixing Complex Errors
- Increase temperature: `CopilotClient(temperature=0.3)`
- Check Copilot bridge is running: `http://localhost:3030`
- Review fix prompt in `_build_fix_prompt()` method

### Quick Fixes Not Working
- Check regex patterns in `ERROR_PATTERNS`
- Add logging to `_apply_fix()` method
- Test patterns independently with `re.search()`

### Max Retries Exceeded
- Increase `MAX_RETRIES` constant
- Check if error is actually fixable (missing dependencies, etc.)
- Review `fix_history` property for applied fixes

## Architecture

### Files
- `app/self_healing_trial_executor.py` - Main executor class
- `app/api/routers/trial.py` - API endpoint `/trial/run-with-healing`
- `app/api/routers/agentic.py` - Integrated into `/agentic/trial-run`

### Dependencies
- `app/executor.py` - Base trial execution
- `app/core/llm_client_copilot.py` - LLM integration
- `langchain` - For structured LLM prompts

## Future Enhancements

- [ ] Locator self-healing from UI crawl data
- [ ] Test data correction (invalid formats, missing fields)
- [ ] Network request mocking for flaky tests
- [ ] Screenshot-based visual validation fixes
- [ ] Parallel retry with different fix strategies
- [ ] ML-based error pattern learning

## See Also

- [SELF_HEALING_COMPLETE.md](./SELF_HEALING_COMPLETE.md) - Locator self-healing
- [QUICK_REFERENCE_SELF_HEALING.md](../QUICK_REFERENCE_SELF_HEALING.md) - Quick guide
- [TRIAL_EXECUTION.md](./TRIAL_EXECUTION.md) - Manual trial execution
