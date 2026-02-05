# MCP Integration Guide

This document describes the Model Context Protocol (MCP) integrations in the test automation platform and how to configure them.

## Overview

The platform now integrates 5 MCP servers to enhance test script generation, self-healing, and repository management:

1. **Playwright Test MCP** - Browser automation and test generation
2. **Microsoft Docs MCP** - Official Playwright documentation and code samples
3. **GitHub MCP** - Repository search and code patterns
4. **Brave Search MCP** - Web search for error solutions and locator patterns
5. **Filesystem MCP** - Safe file operations in framework repositories

## Quick Setup

### 1. Install Required NPM Packages

```powershell
# Install MCP servers globally
npm install -g @microsoft/mcp-server-docs
npm install -g @modelcontextprotocol/server-github
npm install -g @modelcontextprotocol/server-brave-search
npm install -g @modelcontextprotocol/server-filesystem
```

### 2. Configure Environment Variables

Add to your `.env` file:

```env
# GitHub MCP (required for repository operations)
GITHUB_TOKEN=your_github_personal_access_token

# Brave Search MCP (required for self-healing web search)
BRAVE_API_KEY=your_brave_api_key
```

#### Getting API Keys

**GitHub Token:**
1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `read:org`
4. Copy the token to your `.env` file

**Brave API Key:**
1. Go to https://brave.com/search/api/
2. Sign up for API access
3. Copy the API key to your `.env` file

### 3. Verify Configuration

Check that `.vscode/mcp.json` is configured (already done):

```json
{
  "servers": {
    "playwright-test": {
      "type": "stdio",
      "command": "npx",
      "args": ["playwright", "run-test-mcp-server"]
    },
    "microsoft-docs": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@microsoft/mcp-server-docs"]
    },
    "github": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    },
    "brave-search": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"]
    },
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
  }
}
```

## How MCPs Enhance Your Workflow

### 1. Test Script Generation (Microsoft Docs MCP)

**Location:** `app/generators/agentic_script_agent.py`

When generating test scripts, the system now:
- Queries official Playwright documentation for best practices
- Retrieves real code samples from Microsoft Learn
- Ensures generated code follows official standards

**Example:**
```python
# Before: Generic locators
await page.locator('#submit-btn').click()

# After: Official Playwright patterns
await page.getByRole('button', { name: 'Submit' }).click()
```

### 2. Self-Healing (Brave Search + Microsoft Docs MCP)

**Location:** `app/core/llm_client.py`

When tests fail, the self-healing process:
1. Searches web for similar error solutions
2. Consults official Playwright documentation
3. Retrieves proven code patterns
4. Generates resilient locator strategies

**Enhancement:**
```python
# Self-healing now includes:
- Official Playwright locator best practices
- Community-proven solutions from web search
- Real-world code examples
- Multiple fallback strategies
```

### 3. Repository Management (GitHub + Filesystem MCP)

**Location:** `app/api/framework_resolver.py`

When cloning framework repositories:
- Uses GitHub MCP for better cloning
- Filesystem MCP verifies directory structure
- Safer file operations with automatic backups

**Benefits:**
- More reliable repository cloning
- Better error handling
- Automatic structure verification

### 4. Recording Enhancement (Playwright MCP)

**Location:** `app/recorder/mcp_integration.py`

The recorder now can:
- Generate multiple locator strategies per element
- Capture browser snapshots for better context
- Record console messages and network requests
- Evaluate element properties in real-time

**Usage:**
```python
from app.recorder.mcp_integration import enhance_recorder_step

# Enhance recorded step with MCP data
enhanced_step = enhance_recorder_step(step_data, page)
```

## Integration Points

### AgenticScriptAgent

```python
from app.core.mcp_client import get_microsoft_docs_mcp

# In your script generation logic
docs_mcp = get_microsoft_docs_mcp()
best_practices = docs_mcp.search_docs("Playwright locator strategies")
code_samples = docs_mcp.search_code_samples("getByRole", language="typescript")
```

### Self-Healing

```python
from app.core.mcp_client import get_brave_search_mcp, get_microsoft_docs_mcp

# Search for error solutions
brave_search = get_brave_search_mcp()
solutions = brave_search.search(f"Playwright {error_type} solution")

# Get official documentation
docs_mcp = get_microsoft_docs_mcp()
official_docs = docs_mcp.search_docs("Playwright error handling")
```

### Framework Resolver

```python
from app.core.mcp_client import get_github_mcp, get_filesystem_mcp

# Clone with GitHub MCP
github_mcp = get_github_mcp()
success = github_mcp.clone_repository(repo_url, target_path, branch)

# Verify with Filesystem MCP
filesystem_mcp = get_filesystem_mcp()
contents = filesystem_mcp.list_directory(target_path)
```

## Testing MCP Integration

### Test Microsoft Docs MCP

```python
from app.core.mcp_client import get_microsoft_docs_mcp

docs_mcp = get_microsoft_docs_mcp()

# Search documentation
results = docs_mcp.search_docs("Playwright locators")
print(f"Found {len(results)} documentation pages")

# Search code samples
samples = docs_mcp.search_code_samples("getByRole", language="typescript")
print(f"Found {len(samples)} code samples")
```

### Test Brave Search MCP

```python
from app.core.mcp_client import get_brave_search_mcp

brave = get_brave_search_mcp()

# Search for solutions
results = brave.search("Playwright timeout error fix")
print(f"Found {len(results)} web results")
```

### Test GitHub MCP

```python
from app.core.mcp_client import get_github_mcp
from pathlib import Path

github = get_github_mcp()

# Search code
code_results = github.search_code("playwright locators", repo="microsoft/playwright")
print(f"Found {len(code_results)} code snippets")
```

## Troubleshooting

### MCP Server Not Found

```
Error: npx: command not found
```

**Solution:** Ensure Node.js and npm are installed:
```powershell
node --version
npm --version
```

### GitHub Token Issues

```
Error: GitHub API rate limit exceeded
```

**Solution:** Ensure `GITHUB_TOKEN` is set in `.env` file.

### Brave API Issues

```
Error: Brave API key invalid
```

**Solution:** 
1. Verify API key in `.env`
2. Check Brave API dashboard for quota limits

### MCP Server Timeout

```
Error: MCP server connection timeout
```

**Solution:** MCP servers run on-demand. First call may take longer. Subsequent calls are faster.

## Performance Considerations

- **Microsoft Docs MCP**: Fast, cached responses
- **GitHub MCP**: May take 2-5s for first search, then cached
- **Brave Search MCP**: ~1-2s per search (rate limited)
- **Filesystem MCP**: Near-instant for local operations
- **Playwright Test MCP**: Fast, runs locally

## Best Practices

1. **Graceful Degradation**: All MCP integrations have fallbacks
2. **Caching**: Results are cached when possible
3. **Rate Limiting**: Web searches are throttled to avoid limits
4. **Error Handling**: Failed MCP calls don't break the workflow

## Future Enhancements

- [ ] Add SQLite MCP for better database operations
- [ ] Integrate Puppeteer MCP for multi-framework support
- [ ] Add Memory MCP for conversation context
- [ ] Implement sequential chaining for complex workflows

## References

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Playwright Documentation](https://playwright.dev/)
- [MCP Server List](https://github.com/modelcontextprotocol/servers)
