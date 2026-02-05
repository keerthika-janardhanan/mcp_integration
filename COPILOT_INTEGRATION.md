# Copilot Integration Guide

## Architecture

```
Frontend UI (React) 
    ↓ HTTP
FastAPI Backend (Python)
    ↓ HTTP
VS Code Extension Bridge (localhost:3030)
    ↓ VS Code API
GitHub Copilot Chat API
```

## Setup Steps

### 1. Install VS Code Extension

```bash
cd vscode-copilot-bridge
npm install
npm run compile
```

Press F5 in VS Code to launch the extension in debug mode.

### 2. Switch LLM Client

```bash
python switch_llm.py copilot
```

### 3. Update Environment

Add to `.env`:
```
COPILOT_BRIDGE_URL=http://localhost:3030
```

### 4. Install Python Dependencies

```bash
pip install requests
```

### 5. Start Your Application

```bash
# Backend
cd app/api
python main.py

# Frontend
cd frontend
npm run dev
```

## How It Works

1. **VS Code Extension** exposes Copilot via HTTP endpoint at `localhost:3030`
2. **Python Client** (`llm_client_copilot.py`) replaces Azure OpenAI calls with HTTP requests to bridge
3. **No Frontend Changes** - API contract remains identical

## API Compatibility

The Copilot client maintains the same interface:
- `ask_llm_for_script()` - Generate test scripts
- `ask_llm_to_self_heal()` - Fix failing scripts

## Switching Back to Azure

```bash
python switch_llm.py azure
```

## Requirements

- VS Code with GitHub Copilot subscription
- Node.js 18+
- Python 3.8+

## Troubleshooting

**Copilot not available**: Ensure GitHub Copilot extension is installed and authenticated in VS Code

**Connection refused**: Verify VS Code extension is running (check Debug Console)

**Timeout errors**: Increase timeout in `llm_client_copilot.py` (default: 120s)
