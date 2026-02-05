# llm_client.py
import os
import json
import requests
from .mcp_client import get_microsoft_docs_mcp

CACHE_FILE = "./locator_cache.json"
COPILOT_BRIDGE_URL = os.getenv("COPILOT_BRIDGE_URL", "http://localhost:3030")

# -------------------- Locator Cache --------------------
def load_locator_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_locator_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

# -------------------- Copilot Client --------------------
class CopilotResponse:
    def __init__(self, content):
        self.content = content

class CopilotClient:
    def __init__(self, temperature=0.2):
        self.temperature = temperature
        self.bridge_url = f"{COPILOT_BRIDGE_URL}/api/copilot/chat"
    
    def invoke(self, prompt):
        try:
            print(f"[COPILOT] Sending request to {self.bridge_url}")
            response = requests.post(
                self.bridge_url,
                json={"messages": [{"role": "user", "content": prompt}], "temperature": self.temperature},
                timeout=120
            )
            response.raise_for_status()
            print(f"[COPILOT] ✓ Response received (status: {response.status_code})")
            return CopilotResponse(response.json().get("content", ""))
        except Exception as e:
            print(f"[COPILOT] ✗ Error: {e}")
            raise RuntimeError(f"Copilot bridge error: {e}")

_llm_instance = None

def _ensure_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = CopilotClient(temperature=0.2)
    return _llm_instance

# -------------------- Generate Script --------------------
def ask_llm_for_script(structure, existing_script, test_case, enriched_steps, ui_crawl, framework_prompt):
    prompt = f"""
{framework_prompt}

Rules:
- Follow the exact structure of the existing script (imports, hooks, naming, utils).
- Use enriched steps and test cases to create flows.
- If selectors are invalid, self-heal using the UI crawl data.
- Output only valid code.
 - Prefer Playwright getByRole/getByLabel/getByText when locator metadata is provided.
 - If a step provides a union XPath candidate, use it only as a fallback when getBy* is not viable.
 - Do not invent selectors; use provided 'locators' if present in steps. If missing, attempt minimal inference from UI crawl.

Existing structure:
{structure or "N/A"}

Existing Script:
{existing_script or "N/A"}

Test Case:
{test_case or "N/A"}

Enriched Steps (each may include a 'locators' object with 'playwright', 'xpath', 'css', etc.):
{enriched_steps or "N/A"}

UI Crawl Data:
{ui_crawl or "N/A"}
"""
    llm = _ensure_llm()
    resp = llm.invoke(prompt)
    return resp.content.strip()

# -------------------- Self-Healing --------------------
def ask_llm_to_self_heal(failed_script, logs, ui_crawl):
    # Extract error context for targeted search
    error_type = "selector error"
    if "TimeoutError" in logs:
        error_type = "timeout error"
    elif "not found" in logs.lower():
        error_type = "element not found"
    
    # Get MCP clients
    docs_mcp = get_microsoft_docs_mcp()
    
    # Get official Playwright documentation for locator strategies (FREE)
    locator_docs = docs_mcp.search_docs("Playwright locator best practices resilient selectors")
    docs_context = "\n".join([f"- {doc.get('title', '')}: {doc.get('content', '')}" for doc in locator_docs[:2]])
    
    # Search for code examples from Microsoft Docs (FREE)
    code_samples = docs_mcp.search_code_samples("Playwright getByRole getByLabel resilient selectors", language="typescript")
    code_context = "\n".join([f"```typescript\n{sample.get('code', '')}\n```" for sample in code_samples[:2]])
    
    # Note: Using playwright-test-healer agent approach (FREE)
    # The playwright-test-healer agent provides systematic debugging
    # See: .github/agents/playwright-test-healer.agent.md for the agent definition
    
    prompt = f"""
You are debugging a Playwright TypeScript script using official best practices and community knowledge.

Failing Script:
{failed_script}

Execution Logs:
{logs}

UI Crawl Data:
{ui_crawl or "N/A"}

═══════════════════════════════════════════════════════════════════════════════
OFFICIAL PLAYWRIGHT BEST PRACTICES:
═══════════════════════════════════════════════════════════════════════════════
{docs_context}

═══════════════════════════════════════════════════════════════════════════════
CODE EXAMPLES FROM MICROSOFT DOCS:
═══════════════════════════════════════════════════════════════════════════════
{code_context}

Task:
1. Analyze the error using official Playwright documentation patterns
2. Use systematic debugging approach (playwright-test-healer methodology)
3. Identify failing locators from logs
4. Replace them using:
   - UI crawl data (Priority 1)
   - Official Playwright locator strategies: getByRole, getByLabel, getByText (Priority 2)
   - Cached mappings (Priority 3)
   - CSS/XPath only as last resort with multiple attributes
5. Prefer combining 2+ attributes for resilience (e.g., role + text, css + attribute)
6. Update the locator cache with old→new mappings
7. Return the full corrected TypeScript script only (no explanations)
    """
    llm = _ensure_llm()
    resp = llm.invoke(prompt)
    return resp.content.strip()
