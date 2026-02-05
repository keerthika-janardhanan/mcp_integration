import os
import json
import requests
from typing import Optional

CACHE_FILE = "./locator_cache.json"
COPILOT_BRIDGE_URL = os.getenv("COPILOT_BRIDGE_URL", "http://localhost:3030")

def load_locator_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_locator_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

class CopilotClient:
    def __init__(self, temperature: float = 0.2):
        self.temperature = temperature
        self.bridge_url = f"{COPILOT_BRIDGE_URL}/api/copilot/chat"
    
    def invoke(self, prompt: str) -> 'CopilotResponse':
        try:
            print(f"[COPILOT] Sending request to {self.bridge_url}")
            print(f"[COPILOT] Prompt length: {len(prompt)} chars")
            print(f"[COPILOT] Prompt preview: {prompt[:200]}...")
            
            response = requests.post(
                self.bridge_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.temperature
                },
                timeout=120
            )
            response.raise_for_status()
            
            print(f"[COPILOT] ✓ Response received (status: {response.status_code})")
            response_data = response.json()
            content = response_data.get("content", "")
            print(f"[COPILOT] Response length: {len(content)} chars")
            print(f"[COPILOT] Response preview: {content[:200]}...")
            
            return CopilotResponse(content)
        except Exception as e:
            print(f"[COPILOT] ✗ Error: {e}")
            raise RuntimeError(f"Copilot bridge error: {e}")

class CopilotResponse:
    def __init__(self, content: str):
        self.content = content

_llm_instance: Optional[CopilotClient] = None

def _ensure_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = CopilotClient(temperature=0.2)
    return _llm_instance

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

def ask_llm_to_self_heal(failed_script, logs, ui_crawl):
    prompt = f"""
You are debugging a Playwright TypeScript script.

Failing Script:
{failed_script}

Execution Logs:
{logs}

UI Crawl Data:
{ui_crawl or "N/A"}

Task:
- Identify failing locators from logs.
- Replace them using UI crawl or cached mappings.
- If not found, infer correct locators using semantic queries.
- Update the locator cache with old→new mappings.
- Return the full corrected TypeScript script only.
    """
    llm = _ensure_llm()
    resp = llm.invoke(prompt)
    return resp.content.strip()
