# Parallel Codegen Recording

## Overview

Run Playwright's native `codegen` in parallel with our recorder to capture **ALL** actions, then automatically merge missing actions at the end.

## Why?

- **Playwright codegen** captures every action at the protocol level (100% coverage)
- **Our recorder** may miss some actions due to timing, CSP, or programmatic changes
- **Parallel execution** gives us the best of both worlds

## Usage

### Option 1: With Parallel Codegen (Recommended)

```powershell
python -m app.recorder.run_with_codegen --url "https://example.com" --timeout 60
```

### Option 2: Standard Recorder (Existing)

```powershell
python -m app.recorder.run_playwright_recorder_v2 --url "https://example.com" --timeout 60
```

## How It Works

```
Start Recording
├─ Launch Playwright codegen (background, headless)
├─ Launch our recorder (foreground, visible)
└─ User performs actions

Both capture actions simultaneously
├─ Codegen → codegen_actions.json
└─ Recorder → metadata.json

Stop Recording
├─ Stop codegen
├─ Parse codegen output
├─ Compare actions
├─ Add missing actions to metadata.json
└─ Save merged result
```

## Output

### Before Merge
```json
{
  "actions": [
    {"action": "click", "selector": "#button1"},
    {"action": "fill", "selector": "#input1"}
  ]
}
```

### After Merge
```json
{
  "actions": [
    {"action": "click", "selector": "#button1"},
    {"action": "fill", "selector": "#input1"},
    {"action": "check", "selector": "#checkbox1", "addedFromCodegen": true}
  ],
  "codegenMerged": true,
  "codegenActionsCount": 3,
  "missingActionsAdded": 1
}
```

## Benefits

| Feature | Standard Recorder | With Codegen |
|---------|-------------------|--------------|
| **Coverage** | 80-95% | ~100% |
| **Missing actions** | Possible | Auto-added |
| **Metadata richness** | High | High + codegen |
| **Performance** | Fast | Slightly slower |

## Trace File Location

The trace file is saved at:
```
recordings/<session_name>/trace.zip
```

**To view:**
```powershell
playwright show-trace recordings/<session_name>/trace.zip
```

**To analyze:**
```powershell
python -m app.recorder.trace_analyzer recordings/<session_name>
```

## Troubleshooting

### No trace.zip file

**Cause:** Recording was done with `--no-trace` flag

**Solution:** Re-record without `--no-trace`:
```powershell
python -m app.recorder.run_with_codegen --url "https://example.com" --timeout 60
```

### Codegen not starting

**Cause:** Playwright not installed

**Solution:**
```powershell
pip install playwright
playwright install chromium
```

### Actions not merging

**Cause:** Selector mismatch between codegen and recorder

**Solution:** Check `codegen_actions.json` in session directory for raw codegen output

## Comparison: 3 Approaches

### 1. Standard Recorder
```powershell
python -m app.recorder.run_playwright_recorder_v2 --url "https://example.com"
```
- ✅ Fast
- ✅ Rich metadata
- ⚠️ May miss some actions

### 2. Recorder + Trace Analysis
```powershell
python -m app.recorder.run_playwright_recorder_v2 --url "https://example.com"
python -m app.recorder.trace_analyzer recordings/<session>
```
- ✅ Identifies missing actions
- ✅ Coverage report
- ❌ Manual review needed

### 3. Recorder + Parallel Codegen (NEW!)
```powershell
python -m app.recorder.run_with_codegen --url "https://example.com"
```
- ✅ Auto-adds missing actions
- ✅ ~100% coverage
- ✅ No manual review
- ⚠️ Slightly slower

## Example Output

```
[parallel] Starting recorder with parallel codegen
[parallel] Session: recordings/20250115_143022
[codegen] Started parallel codegen recorder (PID: 12345)

>> RECORDER ACTIVE <<
   Recording ALL interactions
   Press Ctrl+C to STOP

[recorder] Recorded 42 actions.

[parallel] Stopping codegen...
[codegen] Stopped codegen recorder
[codegen] Parsed 45 actions from codegen

[parallel] Merging actions...
[parallel] Recorded: 42 actions
[parallel] Codegen: 45 actions
[merge] Found 3 missing actions from codegen

✅ Merge complete!
   Added: 3 missing actions
   Total: 45 actions
```

## Best Practices

1. **Use parallel codegen for critical flows** where 100% coverage is needed
2. **Use standard recorder for quick recordings** where speed matters
3. **Always check trace.zip** to verify what was captured
4. **Review addedFromCodegen actions** to ensure they're valid

## Related Documentation

- [TRACE_ANALYSIS.md](TRACE_ANALYSIS.md) - Trace analysis guide
- [RUNTIME_SELF_HEALING.md](RUNTIME_SELF_HEALING.md) - Self-healing guide
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md) - MCP integration
