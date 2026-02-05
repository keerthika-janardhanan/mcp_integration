# Free Self-Healing with Playwright Test Healer

This document explains how the platform achieves **extraordinary self-healing** without any paid APIs.

## The Problem with Paid Web Search APIs

Initially, the platform considered using:
- ❌ **Brave Search API**: $5-175/month for 2,000-500,000 queries
- ❌ **Google Custom Search API**: Limited free tier (100 queries/day), then paid
- ❌ **Bing Search API**: Paid service

**These are expensive and unnecessary!**

## Our Free Solution: Playwright Test Healer Methodology

Instead, we use the **playwright-test-healer agent** approach, which is:
- ✅ **100% FREE** - No API keys needed
- ✅ **Systematic** - Proven debugging methodology
- ✅ **Effective** - Uses official docs + UI crawl data
- ✅ **Integrated** - Already part of your system

## How It Works

### 1. Official Microsoft Documentation (FREE)
```python
from app.core.mcp_client import get_microsoft_docs_mcp

docs_mcp = get_microsoft_docs_mcp()

# Get official best practices
locator_docs = docs_mcp.search_docs("Playwright locator strategies")

# Get real code examples
code_samples = docs_mcp.search_code_samples("getByRole", language="typescript")
```

**Benefits:**
- Official Playwright documentation
- Real working code examples
- Always up-to-date
- No API key needed

### 2. UI Crawl Data (FREE)
The recorder already captures:
- Element structure
- Attributes (id, name, class, role, aria-*)
- Visible text
- Parent/sibling context

**This is gold for self-healing!**

### 3. Playwright Test Healer Agent (FREE)

Located at: `.github/agents/playwright-test-healer.agent.md`

The agent uses systematic debugging:
```markdown
1. Initial Execution: Run all tests to identify failures
2. Debug Failed Tests: For each failure, pause and investigate
3. Error Investigation: Use Playwright MCP tools to:
   - Examine error details
   - Capture page snapshot
   - Analyze selectors, timing, assertions
4. Root Cause Analysis: Determine underlying cause
5. Code Remediation: Edit test code to fix issues
6. Verification: Restart test after each fix
7. Iteration: Repeat until test passes
```

## Self-Healing Implementation

### Step 1: Analyze Error
```python
def ask_llm_to_self_heal(failed_script, logs, ui_crawl):
    error_type = "selector error"
    if "TimeoutError" in logs:
        error_type = "timeout error"
    elif "not found" in logs.lower():
        error_type = "element not found"
```

### Step 2: Get Official Documentation
```python
docs_mcp = get_microsoft_docs_mcp()

# Search official docs
locator_docs = docs_mcp.search_docs(
    "Playwright locator best practices resilient selectors"
)

# Get code examples
code_samples = docs_mcp.search_code_samples(
    "Playwright getByRole getByLabel",
    language="typescript"
)
```

### Step 3: Apply Playwright Test Healer Methodology
```python
prompt = f"""
You are debugging using playwright-test-healer methodology.

OFFICIAL PLAYWRIGHT BEST PRACTICES:
{docs_context}

CODE EXAMPLES FROM MICROSOFT DOCS:
{code_context}

Task:
1. Analyze error using official documentation
2. Use systematic debugging (playwright-test-healer approach)
3. Identify failing locators
4. Replace using:
   - UI crawl data (Priority 1)
   - Official Playwright locators: getByRole, getByLabel (Priority 2)
   - CSS/XPath with 2+ attributes (Priority 3)
5. Update locator cache
6. Return corrected script
"""
```

## Comparison: Paid vs Free

### Paid Approach (Brave/Google)
```python
# ❌ Requires API key
# ❌ Monthly costs
# ❌ Rate limits
# ❌ May return irrelevant results

brave_results = brave_search.search("playwright error fix")
# Returns: Blog posts, Stack Overflow (maybe relevant, maybe not)
```

### Free Approach (Playwright Test Healer)
```python
# ✅ No API key
# ✅ No costs
# ✅ No rate limits
# ✅ Official documentation only

docs_results = docs_mcp.search_docs("Playwright error handling")
# Returns: Official Playwright docs (always relevant)

ui_crawl_data = get_ui_crawl_data()
# Returns: Actual element data from your app
```

## Why This Is Better

### 1. Official Sources Only
- Web search returns blog posts, outdated answers, wrong advice
- Microsoft Docs returns official, tested, current documentation

### 2. Your UI Data
- Web search has no knowledge of your application
- UI crawl has exact element attributes from your app

### 3. Systematic Approach
- Web search requires manual interpretation
- Playwright Test Healer uses proven debugging methodology

### 4. Cost-Effective
- Web search APIs: $5-175/month
- Our approach: $0/month

## Example Self-Healing Flow

### Scenario: Button Click Fails

**Error:**
```
TimeoutError: Timeout 30000ms exceeded waiting for locator('#submit-btn')
```

**Step 1: Official Docs**
```typescript
// Microsoft Docs returns:
await page.getByRole('button', { name: 'Submit' }).click();
// Better than CSS selector!
```

**Step 2: UI Crawl Data**
```json
{
  "tag": "button",
  "attributes": {
    "id": "submit-btn",
    "class": "btn btn-primary",
    "role": "button",
    "aria-label": "Submit form"
  },
  "text": "Submit"
}
```

**Step 3: Generate Fixed Locator**
```typescript
// Resilient locator using official pattern + UI data
await page.getByRole('button', { name: 'Submit' })
  .and(page.locator('[aria-label="Submit form"]'))
  .click();
```

**Result:** Test passes! No API key needed!

## Additional Free Resources

### 1. GitHub Code Search (FREE)
```python
github_mcp = get_github_mcp()
code = github_mcp.search_code("playwright locators", repo="microsoft/playwright")
```

### 2. Vector Database (FREE)
```python
vector_db = VectorDBClient()
similar_flows = vector_db.query("login flow", top_k=5)
```

### 3. Playwright MCP Tools (FREE)
- `browser_snapshot` - Capture current page state
- `browser_generate_locator` - Generate best locator
- `browser_evaluate` - Run JS to inspect elements
- `test_debug` - Debug failing tests

## Conclusion

You don't need expensive web search APIs for self-healing!

**Our free approach gives you:**
- ✅ Official Playwright documentation
- ✅ Real code examples from Microsoft
- ✅ Systematic debugging methodology
- ✅ Your actual UI data
- ✅ GitHub code patterns
- ✅ Vector DB context
- ✅ Playwright MCP tools

**All for $0/month!**

The playwright-test-healer agent methodology is proven, systematic, and uses the best sources (official docs + your app's data) rather than random web results.

## References

- [Playwright Test Healer Agent](.github/agents/playwright-test-healer.agent.md)
- [Microsoft Docs MCP](https://github.com/microsoft/mcp-server-docs)
- [Playwright MCP](https://github.com/microsoft/playwright)
- [Official Playwright Docs](https://playwright.dev/)
