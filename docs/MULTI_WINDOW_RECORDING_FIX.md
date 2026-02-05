# Multi-Window Recording Fix

## Current State
`app/run_playwright_recorder_v2.py` already has popup/new-window tracking (lines 1067-1108):
- `page.on("popup", _on_popup)` — tracks popups opened from current page
- `context.on("page", _on_new_page)` — tracks all new pages in the browser context

## Common Issues & Solutions

### Issue 1: Popup Not Detected
**Symptom:** New window opens but recorder doesn't switch to it.

**Cause:** Browser popup blocker or `target="_blank"` links opening in same tab due to browser settings.

**Fix:** Add explicit popup waiting + bring-to-front:

```python
# In run_playwright_recorder_v2.py, after page.on("popup", _on_popup)
try:
    async def _handle_popup_sync():
        popup = await page.wait_for_event("popup", timeout=5000)
        popup.bring_to_front()
        active_page = popup
        # Attach listeners
        _on_popup(popup)
    
    # Run in background
    page.context.on("page", lambda p: p.bring_to_front())
except Exception:
    pass
```

### Issue 2: Active Page Not Switching
**Symptom:** Popup opens but interactions still record on parent page.

**Diagnosis:** Check if `active_page` variable is being updated when popup appears.

**Fix:** Add explicit focus tracking and logging:

```python
def _on_popup(p: Page) -> None:
    nonlocal active_page
    old_url = getattr(active_page, 'url', lambda: 'none')()
    active_page = p
    new_url = getattr(p, 'url', lambda: 'none')()
    
    # Log the switch
    sys.stderr.write(f"[recorder][popup-switch] FROM {old_url} TO {new_url}\n")
    
    # Force focus
    try:
        p.bring_to_front()
    except Exception:
        pass
    
    # Add init script BEFORE any interactions
    try:
        p.add_init_script(PAGE_INJECT_SCRIPT)
    except Exception:
        pass
    
    _wait_bindings_ready(p)
    
    # Attach all event listeners
    try:
        p.on("console", _on_console_with_fallback)
        p.on("pageerror", _on_page_error)
        p.on("framenavigated", lambda f: sys.stderr.write(f"[recorder][popup-framenavigated] {getattr(f, 'url', '')}\n"))
        p.on("frameattached", _on_frame_attached)
    except Exception as e:
        sys.stderr.write(f"[recorder][popup-listener-error] {e}\n")
```

### Issue 3: Modal Dialogs vs True Popups
**Problem:** Some "popups" are actually `<dialog>` elements or overlays, not new windows.

**Detection:**
```javascript
// In PAGE_INJECT_SCRIPT, detect modal dialogs
const observeDialogs = () => {
    const obs = new MutationObserver(() => {
        const dialogs = document.querySelectorAll('dialog[open]');
        dialogs.forEach(d => {
            sendCap({ type: 'dialog-opened', text: d.innerText.slice(0, 200) });
        });
    });
    obs.observe(document.body, { childList: true, subtree: true });
};
observeDialogs();
```

### Issue 4: Cross-Origin Popups
**Problem:** Popup from different domain blocks script injection due to CORS.

**Workaround:** Use CDP (Chrome DevTools Protocol) to inject scripts even in cross-origin contexts:

```python
# Add before context creation
def _inject_via_cdp(page: Page, script: str):
    try:
        client = page.context.new_cdp_session(page)
        client.send("Page.addScriptToEvaluateOnNewDocument", {"source": script})
    except Exception as e:
        sys.stderr.write(f"[recorder][cdp-inject-failed] {e}\n")

# Use in _on_popup
def _on_popup(p: Page) -> None:
    _inject_via_cdp(p, PAGE_INJECT_SCRIPT)
    # ... rest of logic
```

## Testing Multi-Window Recording

### Test Case 1: Simple Popup
```python
# Navigate to a page with:
<button onclick="window.open('https://example.com/popup')">Open Popup</button>

# Expected: Recorder switches to popup, logs interactions, switches back on close
```

### Test Case 2: Target=_blank Links
```python
<a href="/details" target="_blank">View Details</a>

# Expected: New tab opens, recorder tracks it via context.on("page")
```

### Test Case 3: Multiple Popups
```python
# Open 3 popups in sequence
# Expected: Each gets tracked, active_page updates for each

# Verify: Check metadata.json has events from all 3 windows
```

## Debug Commands

### Check if popup listeners are attached:
```powershell
# Add to run_playwright_recorder_v2.py before page.goto
sys.stderr.write(f"[recorder][listeners] popup={page.listeners('popup')}, page={context.listeners('page')}\n")
```

### Monitor active_page switches:
```python
# In _on_popup and _on_new_page:
sys.stderr.write(f"[recorder][active-page] NOW: {getattr(active_page, 'url', lambda: 'unknown')()}\n")
```

### Verify script injection in popup:
```python
# In popup's console listener:
def _on_console_with_fallback(msg: ConsoleMessage):
    if "pythonRecorderCapture" in msg.text:
        sys.stderr.write(f"[recorder][popup-script-active] {msg.text}\n")
```

## Recommended Enhancement

Add a visual indicator in the browser when recorder switches windows:

```javascript
// In PAGE_INJECT_SCRIPT
const showRecorderBadge = () => {
    const badge = document.createElement('div');
    badge.style.cssText = 'position:fixed;top:10px;right:10px;background:red;color:white;padding:8px;z-index:999999;border-radius:4px;font-weight:bold;';
    badge.textContent = '🔴 RECORDING';
    document.body.appendChild(badge);
};
showRecorderBadge();
```

## If Still Failing

1. **Run with verbose logging:**
   ```powershell
   python -m app.run_playwright_recorder_v2 --url "https://..." --headed --timeout 30 2>&1 | Tee-Object recorder_debug.log
   ```

2. **Check trace.zip:** Open in Playwright Inspector to see if popup events were captured:
   ```powershell
   npx playwright show-trace recordings/<session>/trace.zip
   ```

3. **Test with known multi-window site:** Try https://the-internet.herokuapp.com/windows to verify basic popup tracking works.
