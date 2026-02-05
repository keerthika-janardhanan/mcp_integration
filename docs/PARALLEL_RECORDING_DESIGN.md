# Parallel Multi-Window Recording Design

## Current State: Sequential Window Switching
The recorder tracks multiple windows but records them **sequentially**:
- `active_page` variable switches when user focuses different windows
- Events from non-active windows are ignored
- Final `metadata.json` contains a linear sequence of steps

## Why Parallel Recording Is Challenging

### 1. User Interaction Model
- A human user can only interact with **one window at a time**
- Recording should mirror actual user behavior
- Parallel recording would capture events that didn't actually happen in parallel

### 2. Step Ordering Ambiguity
```json
// How to order these?
{
  "step_1": { "window": "main", "action": "Click Submit" },
  "step_2": { "window": "popup", "action": "Click Approve", "timestamp": "..." }
}
// Which happened first if both windows were active?
```

### 3. Data Structure Limitations
Current `metadata.json`:
```json
{
  "events": [
    { "index": 0, "action": "click", "url": "..." },
    { "index": 1, "action": "fill", "url": "..." }
  ]
}
```
No `window_id` or `context_id` to group parallel streams.

## Use Cases That Might Need Parallel Recording

### Case 1: Background Process Monitoring
**Scenario:** User starts a long-running process in Window A, switches to Window B to do other work, then returns to Window A to check progress.

**Current Recorder:** Records switch from A → B → A sequentially ✅ (This works fine)

### Case 2: Multi-User Simulation
**Scenario:** Simulate two users interacting with the system simultaneously.

**Current Recorder:** Cannot record this — recorder only captures one user's actions ❌

**Solution:** This is **not a recorder problem** — use Playwright's multi-context API directly:
```typescript
// In generated test
const user1Context = await browser.newContext();
const user2Context = await browser.newContext();

await Promise.all([
  user1Context.newPage().then(p => p.goto('/dashboard')),
  user2Context.newPage().then(p => p.goto('/admin'))
]);
```

### Case 3: Real-Time Collaboration Testing
**Scenario:** Two browser windows editing the same document; verify live updates.

**Current Recorder:** Cannot record parallel interactions ❌

**Workaround:** Record each user's flow separately, then merge manually:
```powershell
# Record User 1's actions
python -m app.run_playwright_recorder_v2 --url "..." --session-name user1-flow

# Record User 2's actions  
python -m app.run_playwright_recorder_v2 --url "..." --session-name user2-flow

# Manually merge in test code
```

## If You Really Need Parallel Recording

### Design Option A: Multi-Stream Metadata

**Change metadata.json structure:**
```json
{
  "recording_mode": "parallel",
  "streams": {
    "main": {
      "window_id": "page-abc123",
      "events": [
        { "index": 0, "timestamp": "2026-01-05T10:00:00Z", "action": "click", "..." }
      ]
    },
    "popup-1": {
      "window_id": "page-def456",
      "events": [
        { "index": 0, "timestamp": "2026-01-05T10:00:05Z", "action": "fill", "..." }
      ]
    }
  },
  "merged_timeline": [
    { "stream": "main", "event_index": 0 },
    { "stream": "popup-1", "event_index": 0 }
  ]
}
```

**Implementation:**
```python
# In run_playwright_recorder_v2.py
events_by_window = {}  # window_id -> list of events

def _on_console_with_fallback(msg: ConsoleMessage, window_id: str):
    payload = extract_payload(msg)
    if window_id not in events_by_window:
        events_by_window[window_id] = []
    events_by_window[window_id].append(payload)

# Attach listener to each window with unique ID
def _on_new_page(p: Page):
    window_id = f"page-{id(p)}"
    p.on("console", lambda msg: _on_console_with_fallback(msg, window_id))
```

### Design Option B: Timestamp-Based Merging

**Keep sequential events, add window metadata:**
```json
{
  "events": [
    { "index": 0, "window_id": "main", "timestamp": 1704448800.123, "action": "click" },
    { "index": 1, "window_id": "popup", "timestamp": 1704448805.456, "action": "fill" },
    { "index": 2, "window_id": "main", "timestamp": 1704448810.789, "action": "verify" }
  ]
}
```

**Implementation:**
```python
# Add to each event capture
event["window_id"] = getattr(page, "_recorder_window_id", "unknown")
event["timestamp"] = time.time()

# Assign window IDs on page creation
def _on_new_page(p: Page):
    p._recorder_window_id = f"window-{len(all_pages)}"
    all_pages.append(p)
```

### Design Option C: Fork Recording Sessions

**Run multiple recorder instances:**
```powershell
# Terminal 1: Record main window
python -m app.run_playwright_recorder_v2 --url "..." --session-name main-window --port 9001

# Terminal 2: Record popup (connect to same browser via CDP)
python -m app.run_playwright_recorder_v2 --connect-cdp "localhost:9222" --session-name popup-window --port 9002
```

**Merge results:**
```python
# In ingest.py
def merge_parallel_sessions(session_dirs: List[str]):
    all_events = []
    for session_dir in session_dirs:
        meta = json.loads((Path(session_dir) / "metadata.json").read_text())
        for event in meta["events"]:
            event["session"] = session_dir
            all_events.append(event)
    
    # Sort by timestamp
    all_events.sort(key=lambda e: e.get("timestamp", 0))
    return all_events
```

## Recommended Approach for Your Use Case

**Question:** What's your actual scenario?

### If: "Record popup interactions while parent stays open"
✅ **Current implementation works** — recorder switches between windows as user focuses them.

**Example Flow:**
1. User clicks "Open Details" → popup opens
2. Recorder switches to popup, records clicks inside popup
3. User closes popup
4. Recorder switches back to main window, continues recording

**No changes needed.**

### If: "Verify that popup AND main window update simultaneously"
❌ **This is an assertion problem, not a recording problem.**

**Solution:** Generate assertions in both contexts:
```typescript
test('parallel window updates', async ({ page, context }) => {
  const popup = await context.waitForEvent('page');
  
  // Verify both windows in parallel
  await Promise.all([
    expect(page.locator('.status')).toHaveText('Updated'),
    expect(popup.locator('.status')).toHaveText('Updated')
  ]);
});
```

### If: "Record two users working at the same time"
❌ **Use multi-context test setup, not recorder.**

**Solution:** Write a custom test harness:
```typescript
test('multi-user collaboration', async ({ browser }) => {
  const user1 = await browser.newContext();
  const user2 = await browser.newContext();
  
  const page1 = await user1.newPage();
  const page2 = await user2.newPage();
  
  // Execute actions in parallel
  await Promise.all([
    page1.goto('/editor').then(() => page1.fill('.content', 'User 1 text')),
    page2.goto('/editor').then(() => page2.fill('.content', 'User 2 text'))
  ]);
});
```

## Action Items

**Before implementing parallel recording, clarify:**

1. **What's the exact use case?** (Describe the scenario you're trying to record)
2. **Is sequential window-switching insufficient?** (Why?)
3. **Do you need to record or to test parallel behavior?** (Recording vs. assertion)

If you need true parallel recording, I can implement **Design Option B** (timestamp-based sequential log with window IDs) as the least disruptive approach.

Otherwise, the current sequential multi-window support should handle most real-world scenarios where a user interacts with popups/dialogs.
