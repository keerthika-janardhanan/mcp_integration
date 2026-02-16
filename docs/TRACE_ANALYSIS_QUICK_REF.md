# Quick Reference: Trace Analysis & Enhanced Recording

## 🚀 Quick Start

### 1. Record with Trace (Default)

```powershell
python -m app.recorder.run_playwright_recorder_v2 --url "https://example.com" --timeout 60
```

### 2. Analyze Recording

```powershell
python -m app.recorder.trace_analyzer recordings/<session_name>
```

### 3. View Trace in Playwright Inspector

```powershell
playwright show-trace recordings/<session_name>/trace.zip
```

## 📊 Understanding the Report

```
📊 Summary:
  - Trace events: 45        ← Total browser events
  - Recorded actions: 42    ← Actions we captured
  - Missing events: 3       ← Events we missed
  - Coverage: 93.3%         ← Capture success rate
```

**Good coverage:** > 90%
**Needs investigation:** < 80%

## 🔍 Common Missing Event Patterns

### Pattern 1: Programmatic Checkbox

**Trace shows:** `check` event on checkbox
**Recorder shows:** Nothing

**Cause:** JavaScript set `element.checked = true` without user click

**Solution:** ✅ Enhanced MutationObserver now captures this

### Pattern 2: Fast Navigation

**Trace shows:** Click → Navigate
**Recorder shows:** Navigate only

**Cause:** Page navigated before JS flush

**Solution:** ✅ 20ms flush + 20x beforeunload flush

### Pattern 3: Shadow DOM Click

**Trace shows:** Click inside shadow root
**Recorder shows:** Nothing

**Cause:** Event listeners don't reach shadow DOM

**Solution:** ⏳ Planned - shadow DOM traversal

### Pattern 4: Cross-Origin Iframe

**Trace shows:** Click in iframe
**Recorder shows:** Nothing

**Cause:** Browser security blocks cross-origin access

**Solution:** ❌ Cannot fix - browser limitation

## 🛠️ Diagnostic Commands

### Check if Recorder is Active

```javascript
// In browser console
window.__pyRecInstalled  // Should be true
```

### Check Queue Status

```javascript
// In browser console
console.log('Pending actions:', window.capQ?.length || 0);
console.log('Pending context:', window.ctxQ?.length || 0);
```

### Force Flush

```javascript
// In browser console
window.pythonRecorderCapture({
    action: 'test',
    pageUrl: location.href,
    timestamp: Date.now(),
    element: { tag: 'test' }
});
```

## 📈 Coverage Benchmarks

| Application Type | Expected Coverage | Notes |
|------------------|-------------------|-------|
| Simple forms | 95-100% | High capture rate |
| SPAs (React/Vue) | 85-95% | Some programmatic changes |
| Complex UIs (Oracle ALTA) | 80-90% | Custom components |
| Shadow DOM apps | 70-85% | Limited shadow access |
| Cross-origin iframes | 60-75% | Security limitations |

## 🎯 Action Items by Coverage

### Coverage > 90% ✅

**Status:** Excellent
**Action:** None needed
**Next:** Generate automation scripts

### Coverage 80-90% ⚠️

**Status:** Good
**Action:** Review missing events
**Check:**
- Are missing events critical?
- Can they be manually added?

### Coverage < 80% ❌

**Status:** Needs investigation
**Action:** Run diagnostics
**Steps:**
1. Check console for CSP errors
2. Check for Shadow DOM usage
3. Check for cross-origin iframes
4. Try `--bypass-csp` flag

## 🔧 Troubleshooting Commands

### Re-record with CSP Bypass

```powershell
python -m app.recorder.run_playwright_recorder_v2 `
    --url "https://example.com" `
    --bypass-csp `
    --timeout 60
```

### Re-record with Slow Motion

```powershell
python -m app.recorder.run_playwright_recorder_v2 `
    --url "https://example.com" `
    --slow-mo 500 `
    --timeout 60
```

### Re-record with Full Artifacts

```powershell
python -m app.recorder.run_playwright_recorder_v2 `
    --url "https://example.com" `
    --capture-dom `
    --capture-screenshots `
    --timeout 60
```

## 📚 Related Commands

### View Trace in Browser

```powershell
playwright show-trace recordings/<session>/trace.zip
```

### Extract Trace Events

```python
from app.recorder.trace_analyzer import TraceAnalyzer
from pathlib import Path

analyzer = TraceAnalyzer(
    trace_path=Path("recordings/<session>/trace.zip"),
    metadata_path=Path("recordings/<session>/metadata.json")
)

comparison = analyzer.compare()
print(f"Missing: {comparison['missing_events_count']}")
```

### Compare Multiple Sessions

```powershell
# PowerShell
Get-ChildItem recordings | ForEach-Object {
    Write-Host "$($_.Name):"
    python -m app.recorder.trace_analyzer $_.FullName
}
```

## 🎓 Best Practices

### 1. Always Record with Trace

✅ **Do:** Use default settings (trace enabled)
❌ **Don't:** Use `--no-trace` unless disk space is critical

### 2. Analyze After Recording

✅ **Do:** Run trace analysis immediately
❌ **Don't:** Wait until test generation fails

### 3. Review Missing Events

✅ **Do:** Check if missing events are critical
❌ **Don't:** Assume all missing events are bugs

### 4. Use Slow Motion for Complex UIs

✅ **Do:** Use `--slow-mo 500` for fast-changing UIs
❌ **Don't:** Use slow motion for simple forms

## 🔗 Quick Links

- [Full Documentation](TRACE_ANALYSIS.md)
- [MCP Integration](MCP_INTEGRATION.md)
- [Runtime Self-Healing](RUNTIME_SELF_HEALING.md)
- [Recorder Troubleshooting](RECORDER_TROUBLESHOOTING.md)

## 💡 Pro Tips

1. **Use Playwright Inspector** to visually see what trace captured
2. **Check synthetic flag** to identify programmatic changes
3. **Compare timestamps** to find timing issues
4. **Review console logs** for CSP/binding errors
5. **Test with --bypass-csp** if coverage is low

## 📞 Getting Help

If coverage is consistently < 80%:

1. Run diagnostics: `python -m app.recorder.trace_analyzer <session>`
2. Check console logs in recordings
3. Try `--bypass-csp` flag
4. Review [TRACE_ANALYSIS.md](TRACE_ANALYSIS.md) for detailed troubleshooting
