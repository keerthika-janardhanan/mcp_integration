# Self-Healing Troubleshooting Guide

## Issue: Self-Healing Not Activating

The logs show NO `[Self-Healing]` output, which means the self-healing executor is not running.

## Diagnostic Steps

### 1. Check if FastAPI server picked up changes
The server needs to be restarted or running with `--reload` flag to pick up code changes.

**Verify**:
```powershell
# Check the terminal running uvicorn
# You should see: "Application startup complete."
```

### 2. Test self-healing logging directly
```powershell
python test_self_healing_logs.py
```

**Expected output**:
```
========== TESTING SELF-HEALING EXECUTOR ==========

[Self-Healing] ========== STARTING SELF-HEALING EXECUTION ==========
[Self-Healing] Framework root: framework_repos\f870a1343bdd
[Self-Healing] Recorder metadata available: True
[Self-Healing] Recorder has 0 actions
[Self-Healing] ========== ATTEMPT 1/5 ==========
...
```

If you see NO `[Self-Healing]` logs, there's a Python logging configuration issue.

### 3. Check backend API logs
When you run a trial, the FastAPI backend should log:

```
INFO:app.api.routers.agentic:[Self-Healing] Loaded recorder metadata from: workday444-workday444.refined.json
INFO:app.self_healing_trial_executor:[Self-Healing] ========== STARTING SELF-HEALING EXECUTION ==========
```

**How to check**:
- Look at the terminal running `python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8001 --reload`
- After clicking "Run Trial" in frontend, immediately check that terminal

### 4. Verify request is using self-healing
Check the frontend network request in browser DevTools:

**POST /agentic/trial-run-existing**:
```json
{
  "testFilePath": "tests/workday444.spec.ts",
  "selfHealing": true,
  "sessionName": "workday444"
}
```

## Common Issues

### Issue 1: Server not reloaded
**Solution**: Kill and restart uvicorn:
```powershell
# Ctrl+C in the uvicorn terminal, then:
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8001 --reload
```

### Issue 2: Logging not configured
**Solution**: Check `app/api/main.py` has logging setup:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Issue 3: Import error silently failing
**Solution**: Check for import errors:
```powershell
python -c "from app.self_healing_trial_executor import execute_trial_with_self_healing; print('Import OK')"
```

### Issue 4: Wrong endpoint being called
The frontend might be calling the wrong endpoint. Check:
- `/agentic/trial-run` (old, NO self-healing by default)
- `/agentic/trial-run-existing` (NEW, self-healing enabled)

## Expected Flow

1. **Frontend** sends POST with `selfHealing: true`, `sessionName: "workday444"`
2. **Backend** logs: `[Self-Healing] Loaded recorder metadata from: workday444-workday444.refined.json`
3. **Executor** logs: `[Self-Healing] ========== STARTING SELF-HEALING EXECUTION ==========`
4. **Attempt 1** runs and fails with timeout
5. **Error Detection** logs: `[Self-Healing] Detected error type: locator_error`
6. **Locator Extraction** logs: `[Self-Healing] Extracted failing locator: button[type='submit']...`
7. **Semantic Matching** logs: `[Self-Healing] Searching through 25 recorder actions`
8. **Match Found** logs: `[Self-Healing] Match found in action 3 (click): semantic match...`
9. **LLM Selection** logs: `[Self-Healing] LLM suggested locator: getByRole('button', {name: 'Sign In'})`
10. **File Update** logs: `[Self-Healing] ✓ Replaced locator in page files`
11. **Attempt 2** runs with new locator

## Next Steps

1. Run `test_self_healing_logs.py` to verify basic functionality
2. Check uvicorn terminal for backend logs during trial run
3. Verify server reloaded after code changes
4. Check browser DevTools network tab for request body

If still not working, provide:
- Output of `test_self_healing_logs.py`
- Backend logs from uvicorn terminal
- Network request body from browser DevTools
