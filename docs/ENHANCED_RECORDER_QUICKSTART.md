# Enhanced Recorder Quick Start

## 30-Second Setup

```powershell
# 1. Install dependencies
pip install playwright langchain-openai
python -m playwright install chromium

# 2. Configure Azure OpenAI
$env:AZURE_OPENAI_KEY = "your-key"
$env:AZURE_OPENAI_ENDPOINT = "https://your-endpoint.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-4"

# 3. Check features
python -m app.recorder.enhanced_recorder_cli --check-features

# 4. Start recording
python -m app.recorder.enhanced_recorder_cli --url "https://example.com" --session demo
```

## Common Commands

### Recording

```powershell
# Full-featured recording
python -m app.recorder.enhanced_recorder_cli --url "https://app.com" --session my_flow

# Fast recording (no AI)
python -m app.recorder.enhanced_recorder_cli --url "https://app.com" --no-ai

# Headless mode
python -m app.recorder.enhanced_recorder_cli --url "https://app.com" --headless

# Verbose output
python -m app.recorder.enhanced_recorder_cli --url "https://app.com" --verbose
```

### Verification

```powershell
# Verify existing recording
python -m app.recorder.enhanced_recorder_cli --verify recordings/my_flow

# Check specific session
python -m app.recorder.enhanced_recorder_cli --verify recordings/2024-01-15_demo
```

## Python API

### Basic Usage

```python
from pathlib import Path
from playwright.async_api import async_playwright
from app.recorder.enhanced_recorder_integration import EnhancedRecorderSession

async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        session = EnhancedRecorderSession(
            session_dir=Path("recordings/demo"),
            enable_mcp=True,
            enable_ai_verification=True
        )
        
        await session.start(page, "https://example.com")
        # Perform actions...
        result = await session.stop_and_finalize()
        
        await browser.close()
        return result
```

### Real-time Stats

```python
# During recording
stats = session.get_real_time_stats()
print(f"Events: {stats['events_captured']}")
print(f"Mutations: {stats['mutations_detected']}")
```

### Standalone Verification

```python
from pathlib import Path
from app.recorder.ai_verification_agent import verify_recording_session

result, report = verify_recording_session(Path("recordings/demo"))
print(f"Gaps: {result.has_gaps}")
print(f"Confidence: {result.confidence:.0%}")
```

## Feature Comparison

| Feature | Standard Recorder | Enhanced Recorder |
|---------|------------------|------------------|
| Basic event capture | ✅ | ✅ |
| Fast action handling | ⚠️ May miss | ✅ Zero-loss |
| Priority queuing | ❌ | ✅ |
| IndexedDB persistence | ❌ | ✅ |
| MCP snapshots | ❌ | ✅ |
| DOM mutation tracking | ❌ | ✅ |
| AI gap detection | ❌ | ✅ |
| Verification reports | ❌ | ✅ |
| Deduplication | ❌ | ✅ |
| Emergency flush | Basic | ✅ Advanced (20x) |

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "MCP not available" | Run with `--no-mcp` or configure MCP server |
| "AI verification failed" | Check Azure OpenAI credentials or use `--no-ai` |
| Events still missed | Check verification report, record slower |
| "Playwright not found" | `pip install playwright && python -m playwright install` |
| Out of memory | Reduce `MAX_QUEUE_SIZE` in config |

## Configuration Files

### Minimal Config

```python
# Disable all enhancements (fallback mode)
session = EnhancedRecorderSession(
    session_dir=Path("recordings/basic"),
    enable_mcp=False,
    enable_ai_verification=False
)
```

### Full Config

```python
session = EnhancedRecorderSession(
    session_dir=Path("recordings/full"),
    capture_dom=True,                 # DOM snapshots
    capture_screenshots=True,         # Screenshots
    enable_mcp=True,                  # MCP features
    enable_ai_verification=True,      # AI gap detection
    verbose=True                      # Debug logging
)
```

## Output Files

```
recordings/demo/
├── metadata.json                    # Standard metadata
├── enhanced_capture_report.json     # Detailed capture analysis
├── verification_report.md           # Human-readable report
├── session_summary.json             # Combined summary
├── dom/                             # DOM snapshots (if enabled)
├── screenshots/                     # Screenshots (if enabled)
└── network.har                      # Network log
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, no gaps detected |
| 1 | Warning, potential gaps detected |
| 2 | Error, recording failed |

## Environment Variables

```powershell
# Required for AI verification
$env:AZURE_OPENAI_KEY = "your-key"
$env:AZURE_OPENAI_ENDPOINT = "https://your-endpoint.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "gpt-4"
$env:OPENAI_API_VERSION = "2024-02-15-preview"

# Optional
$env:VECTOR_DB_PATH = "./vector_store"  # If using vector DB
```

## Next Steps

1. ✅ Record your first flow
2. ✅ Check verification report
3. ✅ Review captured events in `metadata.json`
4. ✅ Adjust config based on needs
5. ✅ Integrate into test generation workflow

## Full Documentation

See [ENHANCED_RECORDER.md](./ENHANCED_RECORDER.md) for complete documentation.
