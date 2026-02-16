# Enhanced Recorder with Zero-Loss Capture

## Overview

The Enhanced Recorder solves the problem of **missing steps during fast user actions** by implementing a multi-layered capture system with MCP integration and AI-powered verification.

## Problem Statement

The standard recorder can miss events when:
- User performs actions faster than ~50ms apart
- Page navigation happens immediately after action
- Form submissions trigger before events are flushed
- JavaScript events fire in rapid succession
- Tab/window switches occur during recording

## Solution Architecture

### 1. **Enhanced JavaScript Capture** (`enhanced_js_injection.py`)

**Features:**
- ✅ Priority-based event queuing (Critical > High > Medium > Low)
- ✅ IndexedDB persistence across page navigations
- ✅ 4 parallel flush threads (2ms, 10ms, 50ms intervals + idle callback)
- ✅ Redundant backup queues
- ✅ Emergency flush on unload/pagehide/visibilitychange
- ✅ 20x retry on critical events (submit, navigation)

**Priority Levels:**
- **Critical (100)**: navigate, submit, form actions
- **High (50)**: click, change, input, fill
- **Medium (20)**: hover, focus, blur, keypress
- **Low (5)**: scroll, mousemove

### 2. **Enhanced Capture Agent** (`enhanced_capture_agent.py`)

**Features:**
- ✅ Real-time event deduplication using element signatures
- ✅ Playwright MCP integration for browser snapshots
- ✅ MutationObserver to detect DOM changes without events
- ✅ Network request capture for context
- ✅ Automatic snapshot comparison to detect gaps

**MCP Tools Used:**
- `mcp_playwright-te_browser_snapshot` - Accessibility tree capture
- `mcp_playwright-te_browser_network_requests` - Network activity
- `mcp_microsoft_pla_browser_console_messages` - Console logs
- `mcp_playwright-te_browser_generate_locator` - Alternative selectors

### 3. **AI Verification Agent** (`ai_verification_agent.py`)

**Features:**
- ✅ Azure OpenAI-powered gap detection
- ✅ Analyzes orphan DOM mutations (changes without events)
- ✅ Detects high-density event periods (potential drops)
- ✅ Identifies navigation jumps without user actions
- ✅ Confidence scoring for each suspected gap
- ✅ Heuristic fallback when LLM unavailable

**Analysis Inputs:**
- Captured events timeline
- DOM mutation records
- Browser snapshots
- Network request log
- Page state changes

### 4. **Integration Module** (`enhanced_recorder_integration.py`)

Drop-in replacement for standard recorder with all enhancements enabled.

## Installation

### Prerequisites

```powershell
# Install Playwright
pip install playwright
python -m playwright install chromium

# Install enhanced recorder dependencies
pip install langchain-openai  # For AI verification

# Configure Azure OpenAI (required for AI features)
$env:AZURE_OPENAI_KEY = "your-key"
$env:AZURE_OPENAI_ENDPOINT = "https://your-endpoint.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-4"
$env:OPENAI_API_VERSION = "2024-02-15-preview"
```

### MCP Configuration

Ensure `.vscode/mcp.json` includes Playwright Test MCP:

```json
{
  "servers": {
    "playwright-test": {
      "command": "node",
      "args": ["path/to/playwright-mcp-server"]
    }
  }
}
```

## Usage

### Method 1: CLI Tool (Recommended)

```powershell
# Basic recording with all features
python -m app.recorder.enhanced_recorder_cli `
    --url "https://example.com" `
    --session demo1

# Recording without AI verification (faster)
python -m app.recorder.enhanced_recorder_cli `
    --url "https://example.com" `
    --session demo2 `
    --no-ai

# Headless mode
python -m app.recorder.enhanced_recorder_cli `
    --url "https://example.com" `
    --headless `
    --verbose

# Verify existing recording
python -m app.recorder.enhanced_recorder_cli `
    --verify recordings/demo1

# Check feature availability
python -m app.recorder.enhanced_recorder_cli --check-features
```

### Method 2: Python API

```python
from pathlib import Path
from playwright.async_api import async_playwright
from app.recorder.enhanced_recorder_integration import EnhancedRecorderSession

async def record_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Create enhanced session
        session = EnhancedRecorderSession(
            session_dir=Path("recordings/my_flow"),
            capture_dom=True,
            capture_screenshots=True,
            enable_mcp=True,              # MCP enhancements
            enable_ai_verification=True,  # AI gap detection
            verbose=True
        )
        
        # Start recording
        await session.start(page, "https://example.com")
        
        # User performs actions...
        await asyncio.sleep(60)  # Or wait for user input
        
        # Stop and finalize
        result = await session.stop_and_finalize()
        
        print(f"Events captured: {result['statistics']['events_captured']}")
        print(f"Verification: {result['verification']['capture_status']}")
        
        if result['verification']['ai_analysis']['has_gaps']:
            print("⚠️ Potential gaps detected!")
            for step in result['verification']['ai_analysis']['missing_steps']:
                print(f"  - {step['likely_action']}")
        
        await browser.close()

# Run
import asyncio
asyncio.run(record_flow())
```

### Method 3: Standalone Verification

```python
from pathlib import Path
from app.recorder.ai_verification_agent import verify_recording_session

# Verify existing recording
result, report_path = verify_recording_session(Path("recordings/demo1"))

print(f"Gaps detected: {result.has_gaps}")
print(f"Confidence: {result.confidence:.0%}")
print(f"Missing steps: {len(result.missing_steps)}")
print(f"Report: {report_path}")
```

## Output Files

Each recording session generates:

### Standard Files
- `metadata.json` - Recording metadata with all events
- `dom/*.html` - DOM snapshots (if enabled)
- `screenshots/*.png` - Screenshots (if enabled)
- `network.har` - Network activity log

### Enhanced Files
- `enhanced_capture_report.json` - Detailed capture analysis
- `verification_report.md` - Human-readable verification report
- `session_summary.json` - Combined summary of all reports

### Enhanced Capture Report Structure

```json
{
  "total_events_captured": 45,
  "unique_events": 42,
  "events_by_priority": {
    "critical": 3,
    "high": 28,
    "medium": 11,
    "low": 3
  },
  "dom_mutations_detected": 67,
  "snapshots_taken": 12,
  "network_requests": 23,
  "potential_missing_actions": [],
  "verification_status": "PASSED",
  "events": [...]
}
```

### Verification Report Example

```markdown
# Recording Verification Report

**Status:** ✅ PASSED
**Confidence:** 85%

## Analysis Summary
Recording appears complete with 45 events captured over 32 seconds.
No significant gaps detected between snapshots.

## Recommendations
- Recording quality is good
- All critical actions were captured
- No re-recording needed
```

## Configuration Options

### EnhancedRecorderSession Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `session_dir` | Required | Path to save recording |
| `capture_dom` | `True` | Capture DOM snapshots |
| `capture_screenshots` | `True` | Capture screenshots |
| `enable_mcp` | `True` | Enable MCP enhancements |
| `enable_ai_verification` | `True` | Enable AI gap detection |
| `verbose` | `True` | Verbose logging |

### JavaScript Capture Config

Edit `CONFIG` in `enhanced_js_injection.py`:

```javascript
const CONFIG = {
    FLUSH_INTERVAL_MS: 2,        // Ultra-fast flush
    FLUSH_BACKUP_MS: 10,         // Backup flush
    FLUSH_SAFETY_MS: 50,         // Safety net
    MAX_QUEUE_SIZE: 1000,        // Max before force flush
    PERSISTENCE_KEY: '__recorder_persistent_events',
    DEBUG: true                  // Enable console logging
};
```

## How It Works

### Event Capture Flow

```
User Action
    ↓
JavaScript Event Listener
    ↓
Priority Queue (with deduplication)
    ↓
Multiple Delivery Attempts
    ├── Immediate delivery (sync)
    ├── 1ms retry
    ├── Queue for flush threads
    └── IndexedDB persistence (critical events)
    ↓
Python Handler (EnhancedCaptureAgent)
    ↓
Enhanced Metadata + MCP Snapshot
    ↓
Stored in metadata.json
```

### Verification Flow

```
Recording Complete
    ↓
Collect All Data
    ├── Captured events
    ├── DOM mutations
    ├── Browser snapshots
    └── Network requests
    ↓
Enhanced Capture Agent Analysis
    ├── Compare snapshots for changes
    ├── Match DOM mutations to events
    └── Identify orphan changes
    ↓
AI Verification Agent
    ├── Build context summary
    ├── Query Azure OpenAI
    ├── Parse gap analysis
    └── Generate recommendations
    ↓
Verification Report
    ├── Gap detection results
    ├── Confidence scores
    └── Recommendations
```

## Performance

### Overhead
- **JavaScript injection**: ~5KB script, <1ms load time
- **Event capture**: <0.1ms per event (priority queue)
- **MCP snapshots**: ~50ms per snapshot (rate-limited to 500ms)
- **AI verification**: 2-5 seconds (runs after recording)

### Scalability
- **Max events**: 10,000 per session (queue overflow protection)
- **Max snapshots**: 1,000 (rate-limited by 500ms interval)
- **Session duration**: No limit (events persisted to IndexedDB)

## Troubleshooting

### Issue: "MCP not available"

**Solution:**
1. Check `.vscode/mcp.json` exists and has `playwright-test` server
2. Verify MCP server is installed: `npm install @playwright/test`
3. Run with `--no-mcp` to disable MCP features

### Issue: "AI verification failed"

**Solution:**
1. Check Azure OpenAI credentials:
   ```powershell
   echo $env:AZURE_OPENAI_KEY
   echo $env:AZURE_OPENAI_ENDPOINT
   ```
2. Verify deployment name matches your Azure setup
3. Run with `--no-ai` to skip AI verification

### Issue: Events still being missed

**Solution:**
1. Check browser console for JavaScript errors
2. Increase `MAX_QUEUE_SIZE` in `enhanced_js_injection.py`
3. Record in slower mode (pause between actions)
4. Check verification report for specific gap patterns
5. Consider recording in multiple sessions (split complex flows)

### Issue: "IndexedDB unavailable"

**Solution:**
- This is non-critical, only affects persistence across navigations
- Ensure browser allows IndexedDB (check privacy settings)
- Events will still be captured via other mechanisms

## Best Practices

1. **Fast Actions**: The enhanced recorder handles fast actions, but for critical flows, consider:
   - Recording at normal human speed
   - Breaking into multiple sessions
   - Using verification to catch any gaps

2. **Complex Workflows**: For multi-page flows:
   - Use MCP snapshots to verify page transitions
   - Check verification report for navigation gaps
   - Re-record specific sections if gaps detected

3. **Authentication Flows**: For sensitive data:
   - Password fields are automatically masked
   - Review `enhanced_capture_report.json` before sharing
   - Consider disabling AI verification for privacy

4. **CI/CD Integration**:
   ```powershell
   # Run in headless with verification
   python -m app.recorder.enhanced_recorder_cli `
       --url "https://staging.example.com" `
       --session "ci_run_${BUILD_ID}" `
       --headless `
       --no-ai  # Skip AI for faster CI
   
   # Check exit code
   if ($LASTEXITCODE -ne 0) {
       Write-Error "Recording verification failed"
       exit 1
   }
   ```

## API Reference

### EnhancedRecorderSession

```python
class EnhancedRecorderSession:
    """Enhanced recorder with zero-loss capture."""
    
    async def start(page: Any, url: str) -> None:
        """Start recording session."""
    
    async def stop_and_finalize() -> Dict[str, Any]:
        """Stop and generate reports."""
    
    def get_real_time_stats() -> Dict[str, Any]:
        """Get current statistics."""
    
    async def pause() -> None:
        """Pause recording."""
    
    async def resume() -> None:
        """Resume recording."""
```

### AIVerificationAgent

```python
class AIVerificationAgent:
    """AI-powered gap detection."""
    
    def analyze_recording_for_gaps(
        events: List[Dict],
        dom_mutations: List[Dict],
        snapshots: List[Dict],
        network_requests: List[Dict]
    ) -> GapDetectionResult:
        """Analyze recording for gaps."""
    
    def generate_verification_report(
        session_dir: Path,
        result: GapDetectionResult
    ) -> Path:
        """Generate human-readable report."""
```

### EnhancedCaptureAgent

```python
class EnhancedCaptureAgent:
    """MCP-powered capture agent."""
    
    async def start_enhanced_capture() -> None:
        """Start enhanced capture."""
    
    async def stop_and_verify() -> Dict[str, Any]:
        """Stop and verify capture."""
    
    def add_event(...) -> bool:
        """Add event with deduplication."""
    
    def get_statistics() -> Dict[str, Any]:
        """Get capture statistics."""
```

## Contributing

To extend the enhanced recorder:

1. **Add new MCP tools**: Edit `enhanced_capture_agent.py`
2. **Customize verification logic**: Edit `ai_verification_agent.py`
3. **Adjust JavaScript capture**: Edit `enhanced_js_injection.py`
4. **Modify integration**: Edit `enhanced_recorder_integration.py`

## License

Same as parent project.

## Support

For issues:
1. Check troubleshooting section above
2. Run with `--verbose` to get detailed logs
3. Review verification report for specific guidance
4. Check `enhanced_capture_report.json` for technical details
