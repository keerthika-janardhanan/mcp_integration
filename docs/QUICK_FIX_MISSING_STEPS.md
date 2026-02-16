# Quick Fix: Debounce Input Events

## Problem
- Too many duplicate input events (22 for one email!)
- Missing button clicks after input (fast navigation)

## Solution
Add debouncing to input/change events in PAGE_INJECT_SCRIPT:

```javascript
// Replace current input listener with debounced version
let inputDebounce = {};
document.addEventListener('input', e => { 
    const t=targetOf(e); 
    const el = norm(t);
    const type = (el && el.getAttribute && el.getAttribute('type') || '').toLowerCase();
    
    // Skip input event for checkboxes/radios
    if (type === 'checkbox' || type === 'radio') {
        return;
    }
    
    // Debounce: only send after 500ms of no typing
    const id = el.id || el.name || xp(el);
    clearTimeout(inputDebounce[id]);
    inputDebounce[id] = setTimeout(() => {
        const masked=isSensitive(t); 
        const val=t&&t.value; 
        send('input', t, { value: masked ? '<masked>' : val, valueMasked: !!masked }); 
    }, 500);
}, true);
```

## Better Solution: Use `--slow-mo`

```powershell
python -m app.recorder.run_playwright_recorder_v2 \
    --url "https://onecognizant.cognizant.com/welcome" \
    --slow-mo 1000 \
    --timeout 120
```

This gives recorder time to flush before navigation.

## Best Solution: Parallel Codegen

```powershell
python -m app.recorder.run_with_codegen \
    --url "https://onecognizant.cognizant.com/welcome" \
    --timeout 120
```

Captures everything + auto-merges missing actions.
