# Checkbox Detection Fix

## Problem
Recorder misinterprets checkboxes as textboxes in certain cases.

## Root Cause Analysis

### Why It Happens
1. **Generic `<input>` catch-all** fired before checkbox-specific logic
2. **Custom checkbox implementations** using `<div role="checkbox">` or styled elements
3. **Missing type attribute** on legacy HTML
4. **CSS-only checkboxes** that don't use semantic HTML

## Solution Applied

### Enhanced Role Detection (run_playwright_recorder_v2.py)

**Before:**
```javascript
if (tag === 'input' && type === 'checkbox') return 'checkbox';
if (tag === 'input' || tag === 'textarea') return 'textbox'; // ❌ Too broad
```

**After:**
```javascript
// Multi-layered checkbox detection
if (tag === 'input' && type === 'checkbox') return 'checkbox';
if (r === 'checkbox') return 'checkbox'; // ARIA role
const cls = (el.className || '').toLowerCase();
if (cls.includes('checkbox') || cls.includes('check-box')) return 'checkbox'; // Class-based

// Explicit textbox types only
if (tag === 'input' && ['text','password','email','tel','url','search','number','date','datetime-local','time','week','month'].includes(type)) return 'textbox';
if (tag === 'input' && !type) return 'textbox'; // Default fallback
if (tag === 'textarea') return 'textbox';
```

### Detection Priority
1. Explicit `type="checkbox"` attribute
2. ARIA `role="checkbox"`
3. CSS class contains "checkbox" or "check-box"
4. Only then fall back to textbox for generic `<input>`

## Testing the Fix

### Test Case 1: Standard HTML Checkbox
```html
<input type="checkbox" id="agree" />
```
**Expected:** `role: "checkbox"`

### Test Case 2: ARIA Checkbox
```html
<div role="checkbox" aria-checked="false" class="custom-check"></div>
```
**Expected:** `role: "checkbox"`

### Test Case 3: Class-Based Checkbox
```html
<input class="form-checkbox" />
```
**Expected:** `role: "checkbox"` (via class detection)

### Test Case 4: Oracle Fusion Checkbox
```html
<input id="Pt1:r1:0:AP1:cb1::content" class="af_inputCheckbox" type="checkbox" />
```
**Expected:** `role: "checkbox"`

### Test Case 5: Should NOT Be Checkbox
```html
<input type="text" placeholder="Enter name" />
<input type="email" />
<textarea></textarea>
```
**Expected:** All `role: "textbox"`

## Verification Commands

### 1. Record a flow with checkboxes:
```powershell
python -m app.run_playwright_recorder_v2 --url "https://your-app/form" --capture-dom --session-name checkbox-test
```

### 2. Check metadata.json for correct roles:
```powershell
Get-Content recordings/checkbox-test/metadata.json | Select-String -Pattern '"role":\s*"checkbox"' -Context 2
```

### 3. Verify in vector DB after ingestion:
```powershell
python -m app.vector_db query "checkbox" --top-k 5
```

## Additional Enhancements

### Detect Toggle Switches
Some UIs use toggle switches instead of traditional checkboxes:

```javascript
// Add to roleOf function
if (cls.includes('toggle') || cls.includes('switch')) {
    const ariaChecked = el.getAttribute('aria-checked');
    if (ariaChecked !== null) return 'checkbox'; // Treat as checkbox
}
```

### Detect Tri-State Checkboxes
```javascript
const ariaChecked = el.getAttribute('aria-checked');
if (ariaChecked === 'mixed') {
    // Indeterminate state
    return 'checkbox'; // Still a checkbox, just tri-state
}
```

### Capture Checked State
Enhance the recorder to capture initial state:

```javascript
// In element capture logic
if (roleOf(el) === 'checkbox') {
    payload.checked = el.checked || el.getAttribute('aria-checked') === 'true';
    payload.indeterminate = el.indeterminate || el.getAttribute('aria-checked') === 'mixed';
}
```

## Known Edge Cases

### 1. Icon-Based Checkboxes
Some designs use `<i>` or `<svg>` inside a clickable wrapper:
```html
<span role="checkbox" class="icon-check">
  <i class="fa fa-check"></i>
</span>
```
**Fix:** Ensure parent element's role is captured, not the icon's.

### 2. Hidden Native Checkboxes
```html
<input type="checkbox" style="display:none" id="real" />
<label for="real" class="styled-checkbox"></label>
```
**Detection:** Recorder may capture click on `<label>` instead of `<input>`. Check if label's `for` attribute points to a hidden checkbox.

### 3. React/Vue Custom Components
```html
<Checkbox v-model="agreed" />
<!-- Renders as: -->
<div class="v-checkbox" data-checked="true"></div>
```
**Fix:** Add data-attribute detection:
```javascript
if (el.dataset && (el.dataset.checked !== undefined || el.dataset.checkbox !== undefined)) {
    return 'checkbox';
}
```

## Debugging Misdetections

If a checkbox is still tagged as textbox:

1. **Inspect element in browser:**
   ```javascript
   // In console:
   const el = document.querySelector('#suspect-element');
   console.log({
     tag: el.tagName,
     type: el.type,
     role: el.getAttribute('role'),
     className: el.className,
     computed: roleOf(el) // Use the recorder's function
   });
   ```

2. **Check recorder logs:**
   ```powershell
   # Look for element capture events
   Get-Content pyerr.txt | Select-String -Pattern "checkbox|textbox"
   ```

3. **Add temporary debug logging to PAGE_INJECT_SCRIPT:**
   ```javascript
   const roleOf = el => {
     // ... existing logic ...
     const result = /* ... */;
     if (tag === 'input') {
       console.log('[ROLE-DEBUG]', { tag, type, role: r, className: cls, result });
     }
     return result;
   };
   ```

## Impact on Generated Scripts

With correct role detection, generated scripts will:

- Use `checkbox.check()` instead of `checkbox.fill('on')`
- Produce cleaner Playwright selectors: `getByRole('checkbox', { name: 'Agree' })`
- Avoid false positives in assertions (e.g., checking if a textbox is checked)

## Rollout Plan

1. ✅ Apply the enhanced `roleOf` logic
2. Test with 5-10 existing flows that have checkboxes
3. Re-ingest refined flows if needed
4. Verify generated scripts use `.check()` method
5. Monitor for any regressions in text input detection
