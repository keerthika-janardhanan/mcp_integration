# Recorder Missing Steps - Troubleshooting Guide

## Common Causes & Solutions

### 1. **Accidental Pause** ⏸️
**Symptom:** Recording stops capturing after pressing 'P'

**Check:**
```bash
python diagnose_recorder.py recordings/<your-session>
```
Look for "Pauses: X" in output

**Solution:**
- Press 'R' to resume recording
- Check terminal for "RECORDING PAUSED" message
- Avoid pressing 'P' unless intentional

---

### 2. **Fast Navigation Drops Events** 🚀
**Symptom:** Submit button clicks or navigation actions missing

**Root Cause:** Page navigates before JS flush completes (60-150ms delay)

**Solution A - Increase Delays:**
Edit `run_playwright_recorder_v2.py` line ~650:
```python
# Change from 150ms to 300ms
setTimeout(() => {
    // ... flush code ...
}, 300);  # Increased from 150
```

**Solution B - Use Slow-Mo:**
```bash
python -m app.recorder.run_playwright_recorder_v2 --url "https://example.com" --slow-mo 500
```

---

### 3. **CSP Blocking Bindings** 🔒
**Symptom:** High "degraded events" count in diagnostics

**Check:**
```bash
# Look for "degraded events (console fallback): X"
python diagnose_recorder.py recordings/<session>
```

**Solution:**
```bash
# Use bypass-csp flag
python -m app.recorder.run_playwright_recorder_v2 \
  --url "https://example.com" \
  --bypass-csp \
  --capture-dom
```

---

### 4. **Dynamic Elements Without Selectors** 🎯
**Symptom:** Actions captured but no stable selectors

**Check Diagnostics:**
```bash
python diagnose_recorder.py recordings/<session>
# Look for "Actions without selectors: X"
```

**Solution:**
- Ensure elements have `id`, `data-testid`, or `aria-label`
- Use `--capture-dom` to get full HTML snapshots
- Self-healing will fix selectors during test generation

---

### 5. **Rapid Interactions Overflow Queue** 💥
**Symptom:** Missing steps during fast typing/clicking

**Root Cause:** Event queue overflow (max 1000 events)

**Solution:**
Edit `enhanced_js_injection.py` line ~30:
```python
CONFIG = {
    'MAX_QUEUE_SIZE': 5000,  # Increased from 1000
    # ...
}
```

---

### 6. **Authentication Redirects** 🔐
**Symptom:** Steps during SSO/MFA missing

**Root Cause:** Recorder waits for target domain before starting

**Solution:**
```bash
# Record from login page directly
python -m app.recorder.run_playwright_recorder_v2 \
  --url "https://login.example.com" \
  --timeout 120
```

Or use saved auth state:
```bash
# First, save auth state
python -m app.recorder.run_playwright_recorder_v2 \
  --url "https://example.com" \
  --auth-state auth.json

# Then reuse it
python -m app.recorder.run_playwright_recorder_v2 \
  --url "https://app.example.com" \
  --auth-state auth.json
```

---

## Diagnostic Commands

### 1. Check Last Recording
```bash
# Find latest session
cd recordings
dir /O-D  # Windows
# or
ls -lt    # Linux/Mac

# Diagnose it
python diagnose_recorder.py recordings/<latest-session>
```

### 2. Enable Verbose Logging
```bash
# Run with stderr redirect to see all events
python -m app.recorder.run_playwright_recorder_v2 \
  --url "https://example.com" \
  --capture-dom 2> recorder_debug.log
```

### 3. Check Event Queue in Real-Time
Add this to your recording session (edit `run_playwright_recorder_v2.py` line ~1850):
```python
# In the wait loop, add periodic queue size logging
if len(pending_actions) > 10:
    sys.stderr.write(f"[recorder][WARNING] Queue backlog: {len(pending_actions)} actions\\n")
```

---

## Best Practices

### ✅ DO:
- Use `--slow-mo 300` for complex flows
- Use `--capture-dom` to get full element context
- Press 'P' to pause during authentication/loading
- Press 'R' to resume after auth completes
- Use `--timeout 120` for longer flows
- Run diagnostics after each recording

### ❌ DON'T:
- Click too fast (< 200ms between clicks)
- Navigate away before seeing action in terminal
- Record during page load/spinner animations
- Use on sites with aggressive CSP without `--bypass-csp`

---

## Quick Fixes Applied

The following fixes have been applied to `run_playwright_recorder_v2.py`:

1. **Reduced console fallback suppression** (1.0s → 0.3s)
   - Captures more events during rapid interactions
   
2. **Added queue size logging**
   - Shows when events are queued (helps debug drops)
   
3. **Added pause state logging**
   - Warns when actions are skipped due to pause

---

## Still Missing Steps?

### Advanced Debugging:

1. **Check Browser Console:**
```javascript
// Open DevTools Console during recording
// Look for:
[recorder] action click button https://...
[EnhancedRecorder] Flushed X events
```

2. **Check metadata.json:**
```bash
# Count actual captured actions
python -c "import json; print(len(json.load(open('recordings/<session>/metadata.json'))['actions']))"
```

3. **Compare with HAR file:**
```bash
# Check if network requests match expected flow
# Open recordings/<session>/network.har in Chrome DevTools
```

---

## Report Issues

If steps are still missing after trying above solutions:

1. Run diagnostics:
```bash
python diagnose_recorder.py recordings/<session> > issue_report.txt
```

2. Include:
   - Output of diagnostics
   - `metadata.json` file
   - Expected vs actual step count
   - Browser console logs (if available)
   - Command used to start recorder

3. Check if it's a known issue:
   - CSP blocking → Use `--bypass-csp`
   - Fast navigation → Use `--slow-mo 500`
   - Auth redirects → Record from login page
