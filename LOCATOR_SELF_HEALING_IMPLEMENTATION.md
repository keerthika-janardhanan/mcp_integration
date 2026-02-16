# Locator Self-Healing Implementation

## Overview
Enhanced the self-healing trial executor to automatically fix locator timeout errors by leveraging recorder metadata with alternative selectors and LLM-based selection.

## Changes Made

### 1. Self-Healing Trial Executor (`app/self_healing_trial_executor.py`)

#### Constructor Enhancement
- Added `recorder_metadata: Optional[Dict[str, Any]] = None` parameter
- Stores recorder JSON metadata for locator fixing

#### New Error Handling
- Updated `_apply_fix()` to route `locator_error` to specialized fix method
- Pattern already existed: `"locator_error": r"(locator.*not found|element.*not found|selector.*not found|Timeout.*exceeded)"`

#### New Methods Added

**`_fix_locator_error()`** (Lines 342-405)
- Extracts failing locator from error message using regex patterns
- Calls `_get_alternative_locators()` to query recorder metadata
- Uses LLM via `_ask_llm_for_best_locator()` to select best alternative
- Replaces locator in page/locator files via `_replace_locator_in_pages()`
- Returns original content (files are modified, not test content)

**`_get_alternative_locators()`** (Lines 407-446)
- Searches through recorder `actions` array for matching selectors
- Extracts all alternative selector formats:
  - CSS selector
  - XPath
  - Playwright methods (getByTestId, getByRole, etc.)
  - Visible text
- Returns list of alternatives with metadata (action_type, timestamp, page_url)

**`_ask_llm_for_best_locator()`** (Lines 448-503)
- Formats alternatives for LLM prompt
- Instructs LLM to prefer: Playwright methods > CSS > XPath
- Handles response formatting (removes markdown, extracts selector)
- Returns best selector string for Playwright `page.locator()`

**`_replace_locator_in_pages()`** (Lines 505-543)
- Scans both `pages/` and `locators/` directories
- Searches all `.ts` files for failing locator
- Replaces occurrences (handles single, double quotes, backticks)
- Logs successful replacements

#### Function Signature Update
**`execute_trial_with_self_healing()`** (Lines 664-692)
- Added `recorder_metadata: Optional[Dict[str, Any]] = None` parameter
- Passes metadata to `SelfHealingTrialExecutor` constructor
- Updated docstring with usage example

### 2. API Router (`app/api/routers/agentic.py`)

#### Import Addition
- Added `from ...recorder.metadata_utils import load_recorder_metadata`

#### Request Model Enhancement
**`TrialRunRequest`** (Lines 271-285)
- Added `sessionName: str | None` field for recorder session name
- Enables frontend to specify which recording session to use for locator fixing

#### Non-Streaming Endpoint Enhancement (Lines 394-420)
- Loads recorder metadata from `app/generated_flows/{sessionName}.refined.json`
- Tries multiple naming patterns: `{sessionName}.refined.json`, `{sessionName}-{sessionName}.refined.json`, `{sessionName}.json`
- Normalizes `steps` array to `actions` for compatibility with self-healing code
- Logs success/failure of metadata loading
- Passes `recorder_metadata` to `execute_trial_with_self_healing()`

#### Streaming Endpoint Enhancement (Lines 1048-1073)
- Same metadata loading logic from `app/generated_flows`
- Yields SSE event when metadata loaded successfully
- Passes `recorder_metadata` to executor via `run_in_executor()`

## Recorder Metadata Structure

### Example Action Format
```json
{
  "action": "input",
  "timestamp": 1770982444740,
  "pageUrl": "https://...",
  "pageTitle": "Sign in to Workday",
  "visibleText": "",
  "element": {
    "html": "<input type=\"text\" data-testid=\"username\" ...>",
    "selector": {
      "css": "#input-t7rh2",
      "xpath": "//*[@id='input-t7rh2']",
      "playwright": {
        "byTestId": "getByTestId('username')"
      }
    }
  },
  "pageId": "page-1",
  "step": 1
}
```

**Note**: The refined JSON uses `steps` array which is automatically normalized to `actions` when loaded.

### Supported Selector Types
1. **CSS**: `#input-t7rh2` or `button[type='submit']`
2. **XPath**: `//*[@id='input-t7rh2']`
3. **Playwright Methods**: `getByTestId('username')`, `getByRole('button')`
4. **Visible Text**: Text content for text-based matching

## Workflow

### When Locator Timeout Occurs

1. **ATTEMPT 1**: Test runs with original code
   - Locator times out: `TimeoutError: locator.waitFor: Timeout 30000ms exceeded`
   - Error detected with pattern: `locator_error`

2. **Self-Healing Activates**:
   - Extracts failing locator from error message
   - Searches recorder metadata for matching element
   - Finds all alternative selectors from that action

3. **LLM Selection**:
   - Presents alternatives to LLM
   - LLM analyzes stability and reliability
   - Prefers Playwright methods over CSS over XPath
   - Returns best selector string

4. **Fix Application**:
   - Replaces failing locator in page object files
   - Replaces failing locator in locator files
   - Both files updated to use new selector

5. **ATTEMPT 2**: Test runs again with fixed locator
   - New locator should work if it was a selector issue
   - Continues up to MAX_RETRIES (5 attempts total)

## Usage

### Frontend API Call
```typescript
const result = await trialRunAgentic({
  testFileContent: code,
  headed: false,
  selfHealing: true,
  sessionName: "workday444"  // NEW: specify recorder session
});
```

### Backend Execution
```python
result = execute_trial_with_self_healing(
    script_content=code,
    framework_root=Path("/repo"),
    headed=False,
    env_overrides={"USERNAME": "user"},
    recorder_metadata=recorder_data  # NEW: pass metadata
)
```

### Logs Output Example
```
[Self-Healing] ATTEMPT 1 failed: locator_error
[Self-Healing] Extracted failing locator: button[type='submit'][data-automation-id='signInButton']
[Self-Healing] Found 2 alternative selector(s)
[Self-Healing] LLM suggested locator: getByTestId('signInButton')
[Self-Healing] Updated locator in: WorkdayCollaborativePt10SignInToWorkday.pages.ts
[Self-Healing] Replaced locator: button[type='submit'][data-automation-id='signInButton'] -> getByTestId('signInButton')
[Self-Healing] ATTEMPT 2 starting...
```

## Benefits

1. **Automatic Locator Resilience**: Tests self-heal when elements not found
2. **Leverages Recorder Data**: Uses captured alternatives instead of guessing
3. **LLM Intelligence**: Smart selection based on Playwright best practices
4. **Minimal Manual Intervention**: Developers don't need to manually fix selectors
5. **Comprehensive Coverage**: Works for both timeout and not-found errors

## Configuration

- **MAX_RETRIES**: 5 attempts (defined in `SelfHealingTrialExecutor`)
- **Default Behavior**: Self-healing enabled by default (`selfHealing: true`)
- **Metadata Location**: `app/generated_flows/{sessionName}.refined.json` or `{sessionName}-{sessionName}.refined.json`
- **Supported File Types**: `.ts` files in `pages/` and `locators/` directories
- **Metadata Format**: Uses `steps` array (automatically normalized to `actions` for compatibility)

## Future Enhancements

1. Cache successful locator fixes to avoid re-fixing same issues
2. Track fix success rate per selector type (CSS vs XPath vs Playwright)
3. Automatically suggest locator improvements in preview phase
4. Support for dynamic selectors with parameterization
5. Integration with UI crawl data for additional selector options
